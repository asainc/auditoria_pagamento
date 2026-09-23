"""Integração única com os serviços corporativos de IA e OCR.

Este módulo isola o restante da aplicação de detalhes de autenticação, upload,
OCR e geração de texto. Nenhum conteúdo de PDF, prompt, token ou credencial é
registrado em log.
"""
from __future__ import annotations

import base64
import hashlib
import importlib
import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from backend.config import Settings
from backend.errors import ServiceError

logger = logging.getLogger("judicial")


class BradescoBridgeError(ServiceError):
    """Erro sanitizado da integração corporativa, com código operacional estável."""

    def __init__(self, code: str, message: str, status_code: int = 502):
        super().__init__(message, status_code)
        self.code = code


@dataclass(frozen=True)
class OcrPage:
    """Texto OCR de uma página, sem persistência adicional no serviço remoto."""

    numero: int
    texto: str


@dataclass(frozen=True)
class OcrDocument:
    """Documento OCR normalizado para consumo pelos prompts especializados."""

    nome: str
    paginas: tuple[OcrPage, ...]
    alertas: tuple[str, ...] = ()

    def texto_prompt(self) -> str:
        """Expõe nome e página de forma explícita para manter evidência rastreável."""
        blocos = [f'## DOCUMENTO: {self.nome}']
        for pagina in self.paginas:
            blocos.append(f'### PAGINA {pagina.numero}\n{pagina.texto}')
        return "\n\n".join(blocos)


class BradescoBridgeClient:
    """Facade de baixo acoplamento sobre ``gpt_bradesco.py``.

    O import é tardio para que testes, geração de contratos e inicialização do
    FastAPI não executem autenticação ou rede. O próprio módulo corporativo é o
    único responsável por chamadas aos serviços de geração de texto e OCR.
    """

    _TEXT_KEYS = ("output_text", "ocr_text", "full_text", "markdown", "text", "content")
    _PAGE_KEYS = ("page_number", "page_num", "page", "pagina", "page_index", "pageIndex")
    _ID_KEYS = ("file_id", "fileId", "arquivo_id", "document_id", "documentId")
    _WORKFLOW_KEYS = ("workflow_execution_id", "workflowExecutionId", "execution_id")

    def __init__(self, settings: Settings):
        self.settings = settings
        self._module: Any | None = None

    @property
    def configured(self) -> bool:
        """Valida somente presença de configuração; não faz chamada de rede."""
        auth = bool(
            self.settings.bradesco_authorization_token.get_secret_value()
            or (
                self.settings.bradesco_identificador.get_secret_value()
                and self.settings.bradesco_senha.get_secret_value()
            )
        )
        return bool(auth and self.settings.bradesco_text_model and self.settings.bradesco_ocr_container)

    def _load(self) -> Any:
        """Importa e configura o módulo corporativo no primeiro uso."""
        if self._module is not None:
            return self._module
        try:
            module = importlib.import_module("gpt_bradesco")
        except Exception as exc:  # pragma: no cover - diagnóstico depende do host corporativo
            raise BradescoBridgeError(
                "bradesco_modulo_indisponivel",
                "Não foi possível carregar gpt_bradesco.py. Confirme que o arquivo está na raiz do projeto e que suas dependências aprovadas estão instaladas.",
                500,
            ) from exc

        required = (
            "configure_iagen",
            "text_generator",
            "file_manager_upload_base64",
            "file_manager_list",
            "file_manager_delete_file",
            "wait_for_workflow",
        )
        missing = [name for name in required if not callable(getattr(module, name, None))]
        ocr_candidates = ("ocr_hibrido", "ocr_generator", "ocr")
        if not any(callable(getattr(module, name, None)) for name in ocr_candidates):
            missing.append("ocr_hibrido/ocr_generator/ocr")
        if missing:
            raise BradescoBridgeError(
                "bradesco_modulo_incompativel",
                "gpt_bradesco.py não possui todas as funções exigidas pela calculadora: " + ", ".join(missing) + ".",
                500,
            )
        module.configure_iagen(
            {
                "ambiente": self.settings.bradesco_environment,
                "identificador": self.settings.bradesco_identificador.get_secret_value(),
                "senha": self.settings.bradesco_senha.get_secret_value(),
                "token": self.settings.bradesco_authorization_token.get_secret_value(),
                "ca_bundle": str(self.settings.bradesco_ca_bundle) if self.settings.bradesco_ca_bundle else "",
            }
        )
        self._module = module
        return module

    @staticmethod
    def _safe_request_id(value: Any) -> str | None:
        """Aceita somente IDs técnicos curtos antes de incluí-los em mensagem."""
        if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.:-]{1,120}", value):
            return value
        return None

    def _classify_error(self, exc: Exception, operation: str) -> BradescoBridgeError:
        """Traduz falhas externas sem ecoar corpo, documento ou segredo."""
        status_code = getattr(exc, "status_code", None)
        request_id = self._safe_request_id(getattr(exc, "request_id", None))
        suffix = f" Referência técnica: {request_id}." if request_id else ""
        if status_code == 401:
            return BradescoBridgeError("bradesco_credencial_invalida", "A autenticação corporativa foi recusada. Revise token ou credenciais do serviço." + suffix)
        if status_code == 403:
            return BradescoBridgeError("bradesco_acesso_negado", "O serviço corporativo recusou o acesso a esta operação. Valide as permissões do identificador e do ambiente." + suffix)
        if status_code == 404:
            return BradescoBridgeError("bradesco_recurso_indisponivel", "Um recurso configurado para a extração corporativa não foi encontrado. Revise deployment, container e workflow." + suffix)
        if status_code == 429:
            return BradescoBridgeError("bradesco_limite_requisicoes", "O serviço corporativo limitou temporariamente as requisições. Aguarde e repita a extração." + suffix)
        if isinstance(exc, (ValueError, TypeError, FileNotFoundError)):
            return BradescoBridgeError("bradesco_configuracao_invalida", f"Configuração inválida na etapa {operation}. Revise os parâmetros corporativos antes de repetir.", 500)
        if "timeout" in type(exc).__name__.lower() or "tempo máximo" in str(exc).lower():
            return BradescoBridgeError("bradesco_tempo_esgotado", f"O serviço corporativo excedeu o tempo máximo na etapa {operation}." + suffix)
        return BradescoBridgeError("bradesco_indisponivel", f"A etapa corporativa {operation} não foi concluída. Os documentos locais foram preservados." + suffix)

    def _call(self, operation: str, function_name: str, *args: Any, **kwargs: Any) -> Any:
        """Executa uma função corporativa e centraliza tratamento de erro."""
        module = self._load()
        try:
            return getattr(module, function_name)(*args, **kwargs)
        except BradescoBridgeError:
            raise
        except Exception as exc:
            logger.warning("bradesco_bridge_failure", extra={"operation": operation, "error_type": type(exc).__name__})
            raise self._classify_error(exc, operation) from None

    @staticmethod
    def _walk(value: Any) -> Iterable[tuple[str | None, Any]]:
        """Percorre respostas JSON sem pressupor um único envelope do gateway."""
        if isinstance(value, Mapping):
            for key, item in value.items():
                yield str(key), item
                yield from BradescoBridgeClient._walk(item)
        elif isinstance(value, list):
            for item in value:
                yield None, item
                yield from BradescoBridgeClient._walk(item)

    def _find_first_text(self, payload: Any, keys: tuple[str, ...]) -> str | None:
        candidates: list[str] = []
        normalized = {key.casefold() for key in keys}
        for key, value in self._walk(payload):
            if key and key.casefold() in normalized and isinstance(value, str) and value.strip():
                candidates.append(value.strip())
        return max(candidates, key=len) if candidates else None

    def _extract_identifier(self, payload: Any, keys: tuple[str, ...]) -> str | None:
        normalized = {key.casefold() for key in keys}
        for key, value in self._walk(payload):
            if key and key.casefold() in normalized and isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _resolve_file_id(self, upload_result: Any, remote_name: str) -> str:
        """Obtém o ID do upload; consulta a listagem somente se a resposta não o trouxer."""
        identifier = self._extract_identifier(upload_result, self._ID_KEYS)
        if identifier:
            return identifier
        listing = self._call(
            "listar arquivo enviado",
            "file_manager_list",
            {"container_name": self.settings.bradesco_ocr_container, "page": 0, "page_size": 50000},
            {"ambiente": self.settings.bradesco_environment, "timeout": self.settings.bradesco_timeout_seconds},
        )
        matches: list[Mapping[str, Any]] = []
        for _, item in self._walk(listing):
            if isinstance(item, Mapping):
                name = item.get("file_name") or item.get("fileName") or item.get("name")
                if name == remote_name:
                    matches.append(item)
        for item in reversed(matches):
            identifier = self._extract_identifier(item, self._ID_KEYS + ("id",))
            if identifier:
                return identifier
        raise BradescoBridgeError(
            "bradesco_upload_sem_id",
            "O arquivo foi enviado ao gerenciador corporativo, mas o identificador necessário para o OCR não foi localizado.",
        )

    def _upload_pdf(self, name: str, content: bytes) -> str:
        """Envia PDF em base64 apenas durante a chamada e retorna o ID remoto."""
        digest = hashlib.sha256(content).hexdigest()[:12]
        remote_name = f"{digest}_{name}"
        result = self._call(
            "upload para OCR",
            "file_manager_upload_base64",
            {
                "base64": base64.b64encode(content).decode("ascii"),
                "file_name": remote_name,
                "container_name": self.settings.bradesco_ocr_container,
                "create_container": self.settings.bradesco_ocr_create_container,
                "overwrite": False,
            },
            {"ambiente": self.settings.bradesco_environment, "timeout": self.settings.bradesco_timeout_seconds},
        )
        return self._resolve_file_id(result, remote_name)

    def _ocr_payload(self, file_id: str) -> dict[str, Any]:
        """Monta o OCR híbrido seguindo o contrato exemplificado para a plataforma."""
        return {
            "files_id": [file_id],
            "detailed_output": True,
            "async_mode": True,
            "workflow_configuration_code": self.settings.bradesco_ocr_workflow_configuration_code,
            "figure_settings": {
                "vision_model": self.settings.bradesco_ocr_vision_model,
                "max_image_size": self.settings.bradesco_ocr_max_image_size,
                "image_format": self.settings.bradesco_ocr_image_format,
            },
            "table_settings": {
                "table_format": self.settings.bradesco_ocr_table_format,
                "language_model": self.settings.bradesco_ocr_language_model,
            },
            "document_settings": {"locale": self.settings.bradesco_ocr_locale},
            "warning_settings": {"enabled": True},
        }

    def _wait_if_needed(self, result: Any) -> Any:
        """Aguarda workflow assíncrono somente quando a resposta fornece seu ID."""
        workflow_id = self._extract_identifier(result, self._WORKFLOW_KEYS)
        status = self._find_first_text(result, ("status",))
        if workflow_id and status != "WF_COMPLETED_SUCCESS":
            return self._call(
                "aguardar OCR",
                "wait_for_workflow",
                workflow_id,
                {
                    "ambiente": self.settings.bradesco_environment,
                    "timeout": self.settings.bradesco_timeout_seconds,
                    "poll_interval": self.settings.bradesco_ocr_poll_interval_seconds,
                    "max_wait_seconds": self.settings.bradesco_ocr_max_wait_seconds,
                },
            )
        return result

    @staticmethod
    def _page_number(mapping: Mapping[str, Any], page_keys: tuple[str, ...]) -> int | None:
        """Converte identificadores de página sem aceitar booleanos ou negativos."""
        normalized = {key.casefold() for key in page_keys}
        for key, value in mapping.items():
            if str(key).casefold() not in normalized:
                continue
            if isinstance(value, bool):
                continue
            try:
                number = int(value)
            except (TypeError, ValueError):
                continue
            if number >= 0:
                return number + 1 if str(key).casefold() in {"page_index", "pageindex"} else max(1, number)
        return None

    def _pages_from_payload(self, payload: Any) -> list[OcrPage]:
        """Normaliza diferentes envelopes detalhados de OCR preservando a página."""
        pages: dict[int, str] = {}
        for _, item in self._walk(payload):
            if not isinstance(item, Mapping):
                continue
            number = self._page_number(item, self._PAGE_KEYS)
            if number is None:
                continue
            text = None
            for key in self._TEXT_KEYS:
                value = item.get(key)
                if isinstance(value, str) and value.strip():
                    text = value.strip()
                    break
            if text:
                if number in pages and text not in pages[number]:
                    pages[number] += "\n" + text
                else:
                    pages[number] = text
        if pages:
            return [OcrPage(numero=number, texto=pages[number]) for number in sorted(pages)]

        text = self._find_first_text(payload, self._TEXT_KEYS)
        if not text and isinstance(payload, str):
            text = payload.strip()
        if not text:
            return []
        # Alguns workflows devolvem o detalhamento serializado em JSON dentro de output_text.
        try:
            decoded = json.loads(text)
        except (ValueError, TypeError):
            decoded = None
        if decoded is not None and decoded is not payload:
            nested = self._pages_from_payload(decoded)
            if nested:
                return nested
        form_feed = [part.strip() for part in text.split("\f") if part.strip()]
        if len(form_feed) > 1:
            return [OcrPage(numero=index, texto=part) for index, part in enumerate(form_feed, start=1)]
        marker = re.compile(r"(?im)^\s*(?:#{1,6}\s*)?(?:p[aá]gina|page)\s*[:#-]?\s*(\d+)\s*$")
        matches = list(marker.finditer(text))
        if matches:
            result: list[OcrPage] = []
            for index, match in enumerate(matches):
                start = match.end()
                end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
                content = text[start:end].strip()
                if content:
                    result.append(OcrPage(numero=int(match.group(1)), texto=content))
            if result:
                return result
        return [OcrPage(numero=1, texto=text)]

    def ocr_pdf(self, name: str, content: bytes, expected_pages: int) -> OcrDocument:
        """Envia um PDF ao OCR e remove o objeto remoto após obter o texto."""
        if not content.startswith(b"%PDF-"):
            raise BradescoBridgeError("bradesco_pdf_invalido", "O OCR recebeu conteúdo que não é PDF.", 400)
        file_id: str | None = None
        warnings: list[str] = []
        try:
            file_id = self._upload_pdf(name, content)
            module = self._load()
            ocr_function = next(
                name
                for name in ("ocr_hibrido", "ocr_generator", "ocr")
                if callable(getattr(module, name, None))
            )
            result = self._call(
                "OCR",
                ocr_function,
                self._ocr_payload(file_id),
                {"ambiente": self.settings.bradesco_environment, "timeout": self.settings.bradesco_timeout_seconds},
            )
            result = self._wait_if_needed(result)
            pages = self._pages_from_payload(result)
            if not pages:
                raise BradescoBridgeError("bradesco_ocr_sem_texto", "O OCR corporativo foi concluído, mas não retornou texto utilizável.")
            if len(pages) == 1 and expected_pages > 1:
                warnings.append(
                    f"OCR de {name}: o serviço retornou texto sem separação confiável das {expected_pages} páginas; confira visualmente as evidências."
                )
            return OcrDocument(nome=name, paginas=tuple(pages), alertas=tuple(warnings))
        finally:
            if file_id:
                try:
                    self._call(
                        "limpeza do arquivo remoto",
                        "file_manager_delete_file",
                        {"file_id": file_id},
                        {"ambiente": self.settings.bradesco_environment, "timeout": self.settings.bradesco_timeout_seconds},
                    )
                except BradescoBridgeError:
                    # Falha de limpeza não invalida o resultado; apenas gera alerta técnico.
                    logger.warning("bradesco_remote_cleanup_failed", extra={"error_type": "cleanup_failed"})

    def generate_text(self, payload: str, *, max_tokens: int) -> str:
        """Executa qualquer prompt exclusivamente por ``text_generator``."""
        parameters = {
            "deployment_name": self.settings.bradesco_text_model,
            "reasoning_effort": self.settings.bradesco_text_reasoning_effort,
            "verbosity": self.settings.bradesco_text_verbosity,
            "modalities": self.settings.bradesco_text_modalities,
            "temperature": self.settings.bradesco_text_temperature,
            "max_tokens": min(max_tokens, self.settings.bradesco_text_max_tokens),
            "async_mode": False,
            "stream": False,
            "message_format": {"type": "json_object"},
            "ambiente": self.settings.bradesco_environment,
            "timeout": self.settings.bradesco_timeout_seconds,
        }
        response = self._call("geração de texto", "text_generator", payload, parameters)
        if not isinstance(response, str) or not response.strip():
            raise BradescoBridgeError("bradesco_saida_vazia", "O gerador corporativo não retornou texto para a etapa de extração.")
        return response.strip()
