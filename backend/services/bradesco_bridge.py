"""Integração adaptativa com ``gpt_bradesco.py``.

A aplicação usa somente as funções públicas já expostas pelo módulo corporativo.
Nenhuma URL interna, credencial, token ou implementação de autenticação é duplicada
nesta camada. O adaptador tolera as assinaturas encontradas nas versões antigas e
novas do módulo para evitar acoplamento desnecessário.
"""
from __future__ import annotations

import base64
import hashlib
import importlib
import inspect
import json
import logging
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

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
    """Texto OCR de uma página, sem persistir conteúdo em log técnico."""

    numero: int
    texto: str


@dataclass(frozen=True)
class OcrDocument:
    """Documento OCR normalizado para consumo pelos prompts especializados."""

    nome: str
    paginas: tuple[OcrPage, ...]
    alertas: tuple[str, ...] = ()

    def texto_prompt(self) -> str:
        """Expõe nome e página explicitamente para manter rastreabilidade."""
        blocos = [f"## DOCUMENTO: {self.nome}"]
        for pagina in self.paginas:
            blocos.append(f"### PAGINA {pagina.numero}\n{pagina.texto}")
        return "\n\n".join(blocos)


@dataclass(frozen=True)
class RemoteFile:
    """Referências técnicas retornadas pelo gerenciador de arquivos corporativo."""

    nome: str
    identificador: str | None = None
    caminho: str | None = None


class BradescoBridgeClient:
    """Facade de baixo acoplamento sobre o módulo corporativo.

    Funções mínimas exigidas:
    - ``text_generator``;
    - alguma função de OCR: ``ocr_hibrido``, ``ocr``, ``ocr_generator`` ou
      ``get_text_ocr``;
    - alguma função de upload: ``file_manager_upload`` ou
      ``file_manager_upload_base64``.

    ``configure_iagen``, listagem, exclusão e espera de workflow são opcionais.
    Quando existem, são aproveitadas; quando não existem, a extração continua por
    uma estratégia compatível com as funções legadas.
    """

    _TEXT_KEYS = (
        "output_text",
        "ocr_text",
        "full_text",
        "markdown",
        "text",
        "content",
        "texto",
        "conteudo",
    )
    _PAGE_KEYS = ("page_number", "page_num", "page", "pagina", "page_index", "pageIndex")
    _ID_KEYS = ("file_id", "fileId", "arquivo_id", "document_id", "documentId", "id")
    _PATH_KEYS = ("file_path", "filePath", "path", "full_path", "fullPath", "caminho", "name", "file_name", "fileName")
    _WORKFLOW_KEYS = ("workflow_execution_id", "workflowExecutionId", "execution_id")
    _OCR_FUNCTIONS = ("ocr_hibrido", "ocr", "ocr_generator", "get_text_ocr")
    _UPLOAD_FUNCTIONS = ("file_manager_upload_base64", "file_manager_upload")

    def __init__(self, settings: Settings):
        self.settings = settings
        self._module: Any | None = None

    @property
    def configured(self) -> bool:
        """Valida apenas parâmetros da calculadora, sem importar o módulo.

        A autenticação pode ser integralmente administrada pelo próprio
        ``gpt_bradesco.py`` corporativo; por isso não é obrigatório duplicar
        usuário/senha/token nas variáveis da calculadora.
        """
        return bool(self.settings.bradesco_text_model and self.settings.bradesco_ocr_container)

    def _load(self) -> Any:
        """Importa o módulo no primeiro uso e configura somente se houver suporte."""
        if self._module is not None:
            return self._module
        try:
            module = importlib.import_module("gpt_bradesco")
        except Exception as exc:  # pragma: no cover - depende do host corporativo
            raise BradescoBridgeError(
                "bradesco_modulo_indisponivel",
                "Não foi possível carregar gpt_bradesco.py. Confirme que o arquivo corporativo está na raiz do projeto e que suas dependências aprovadas estão instaladas.",
                500,
            ) from exc

        missing: list[str] = []
        if not callable(getattr(module, "text_generator", None)):
            missing.append("text_generator")
        if not any(callable(getattr(module, name, None)) for name in self._OCR_FUNCTIONS):
            missing.append("ocr_hibrido/ocr/ocr_generator/get_text_ocr")
        if not any(callable(getattr(module, name, None)) for name in self._UPLOAD_FUNCTIONS):
            missing.append("file_manager_upload/file_manager_upload_base64")
        if missing:
            raise BradescoBridgeError(
                "bradesco_modulo_incompativel",
                "gpt_bradesco.py não possui as funções mínimas exigidas pela calculadora: " + ", ".join(missing) + ".",
                500,
            )

        # Algumas versões novas expõem configuração explícita; as versões legadas
        # já se autenticam no próprio import. A aplicação aceita ambos os contratos.
        configure = getattr(module, "configure_iagen", None)
        if callable(configure):
            credentials = {
                "ambiente": self.settings.bradesco_environment,
                "identificador": self.settings.bradesco_identificador.get_secret_value(),
                "senha": self.settings.bradesco_senha.get_secret_value(),
                "token": self.settings.bradesco_authorization_token.get_secret_value(),
                "ca_bundle": str(self.settings.bradesco_ca_bundle) if self.settings.bradesco_ca_bundle else "",
            }
            # Não substitui autenticação já configurada por valores vazios.
            if any(credentials[key] for key in ("identificador", "senha", "token")):
                self._invoke_callable("configuração corporativa", configure, [(credentials,)])

        self._module = module
        return module

    @staticmethod
    def _safe_request_id(value: Any) -> str | None:
        """Aceita somente IDs técnicos curtos antes de incluí-los em mensagem."""
        if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.:-]{1,120}", value):
            return value
        return None

    def _classify_error(self, exc: Exception, operation: str) -> BradescoBridgeError:
        """Traduz falhas externas sem ecoar corpo, documento, prompt ou segredo."""
        status_code = getattr(exc, "status_code", None)
        request_id = self._safe_request_id(getattr(exc, "request_id", None))
        suffix = f" Referência técnica: {request_id}." if request_id else ""
        if status_code == 401:
            return BradescoBridgeError("bradesco_credencial_invalida", "A autenticação corporativa foi recusada. Revise as credenciais do módulo gpt_bradesco.py." + suffix)
        if status_code == 403:
            return BradescoBridgeError("bradesco_acesso_negado", "O serviço corporativo recusou o acesso à operação solicitada. Valide as permissões do identificador e do ambiente." + suffix)
        if status_code == 404:
            return BradescoBridgeError("bradesco_recurso_indisponivel", "Um recurso configurado para a extração corporativa não foi encontrado. Revise deployment, container e workflow." + suffix)
        if status_code == 429:
            return BradescoBridgeError("bradesco_limite_requisicoes", "O serviço corporativo limitou temporariamente as requisições. Aguarde e repita a extração." + suffix)
        if isinstance(exc, (ValueError, TypeError, FileNotFoundError)):
            return BradescoBridgeError("bradesco_configuracao_invalida", f"Configuração inválida na etapa {operation}. Revise os parâmetros corporativos antes de repetir.", 500)
        if "timeout" in type(exc).__name__.lower() or "tempo máximo" in str(exc).lower():
            return BradescoBridgeError("bradesco_tempo_esgotado", f"O serviço corporativo excedeu o tempo máximo na etapa {operation}." + suffix)
        return BradescoBridgeError("bradesco_indisponivel", f"A etapa corporativa {operation} não foi concluída. Os documentos locais foram preservados." + suffix)

    @staticmethod
    def _binds(function: Any, args: Sequence[Any]) -> bool:
        """Confere a assinatura antes da chamada para não usar TypeError como fluxo."""
        try:
            inspect.signature(function).bind(*args)
            return True
        except (TypeError, ValueError):
            return False

    def _invoke_callable(self, operation: str, function: Any, variants: Sequence[Sequence[Any]]) -> Any:
        """Executa a primeira assinatura compatível conhecida de uma função."""
        selected: Sequence[Any] | None = None
        for args in variants:
            if self._binds(function, args):
                selected = args
                break
        if selected is None:
            raise BradescoBridgeError(
                "bradesco_assinatura_incompativel",
                f"A função corporativa usada na etapa {operation} possui uma assinatura não reconhecida pela calculadora.",
                500,
            )
        try:
            return function(*selected)
        except BradescoBridgeError:
            raise
        except Exception as exc:
            logger.warning("bradesco_bridge_failure", extra={"operation": operation, "error_type": type(exc).__name__})
            raise self._classify_error(exc, operation) from None

    def _call_variants(self, operation: str, function_name: str, variants: Sequence[Sequence[Any]]) -> Any:
        """Carrega uma função pública pelo nome e aplica assinaturas compatíveis."""
        module = self._load()
        function = getattr(module, function_name, None)
        if not callable(function):
            raise BradescoBridgeError(
                "bradesco_funcao_indisponivel",
                f"A função corporativa necessária para {operation} não está disponível.",
                500,
            )
        return self._invoke_callable(operation, function, variants)

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
        """Extrai valor textual respeitando a prioridade declarada em ``keys``."""
        walked = list(self._walk(payload))
        for expected in keys:
            normalized = expected.casefold()
            for key, value in walked:
                if key and key.casefold() == normalized and isinstance(value, str) and value.strip():
                    return value.strip()
        return None

    @staticmethod
    def _same_remote_name(mapping: Mapping[str, Any], remote_name: str) -> bool:
        """Compara nome/caminho remoto sem aceitar correspondência parcial ambígua."""
        for key in BradescoBridgeClient._PATH_KEYS:
            value = mapping.get(key)
            if isinstance(value, str) and Path(value.replace("\\", "/")).name == remote_name:
                return True
        return False

    def _list_remote_file(self, remote_name: str) -> RemoteFile:
        """Consulta listagem apenas quando a versão do módulo oferece esse recurso."""
        module = self._load()
        listing: Any | None = None
        if callable(getattr(module, "file_manager_list_files", None)):
            listing = self._call_variants(
                "listar arquivo enviado",
                "file_manager_list_files",
                [(self.settings.bradesco_ocr_container,), (self.settings.bradesco_ocr_container, 0, 50000)],
            )
        elif callable(getattr(module, "file_manager_list", None)):
            payload = {"container_name": self.settings.bradesco_ocr_container, "page": 0, "page_size": 50000}
            parameters = {"ambiente": self.settings.bradesco_environment, "timeout": self.settings.bradesco_timeout_seconds}
            listing = self._call_variants("listar arquivo enviado", "file_manager_list", [(payload, parameters), (payload,)])
        if listing is None:
            return RemoteFile(nome=remote_name, caminho=remote_name)

        matches: list[Mapping[str, Any]] = []
        for _, item in self._walk(listing):
            if isinstance(item, Mapping) and self._same_remote_name(item, remote_name):
                matches.append(item)
        if not matches:
            return RemoteFile(nome=remote_name, caminho=remote_name)
        item = matches[-1]
        return RemoteFile(
            nome=remote_name,
            identificador=self._extract_identifier(item, self._ID_KEYS),
            caminho=self._extract_identifier(item, self._PATH_KEYS) or remote_name,
        )

    def _upload_pdf(self, name: str, content: bytes) -> RemoteFile:
        """Envia PDF usando a função disponível sem depender de aliases adicionais."""
        module = self._load()
        digest = hashlib.sha256(content).hexdigest()[:12]
        safe_name = Path(name).name.replace(" ", "_")
        remote_name = f"{digest}_{safe_name}"
        parameters = {"ambiente": self.settings.bradesco_environment, "timeout": self.settings.bradesco_timeout_seconds}

        result: Any
        if callable(getattr(module, "file_manager_upload_base64", None)):
            payload = {
                "base64": base64.b64encode(content).decode("ascii"),
                "file_name": remote_name,
                "container_name": self.settings.bradesco_ocr_container,
                "create_container": self.settings.bradesco_ocr_create_container,
                "overwrite": False,
            }
            result = self._call_variants(
                "upload para OCR",
                "file_manager_upload_base64",
                [(payload, parameters), (payload,)],
            )
        elif callable(getattr(module, "file_manager_upload", None)):
            # A API legada recebe caminho local; o arquivo temporário dura somente
            # o tempo do upload e é removido pelo TemporaryDirectory.
            with tempfile.TemporaryDirectory(prefix="judicial_ocr_") as temporary_directory:
                local_path = Path(temporary_directory) / safe_name
                local_path.write_bytes(content)
                result = self._call_variants(
                    "upload para OCR",
                    "file_manager_upload",
                    [
                        (
                            str(local_path),
                            remote_name,
                            self.settings.bradesco_ocr_container,
                            str(self.settings.bradesco_ocr_create_container).lower(),
                            "false",
                        ),
                        (str(local_path), remote_name, self.settings.bradesco_ocr_container),
                    ],
                )
        else:  # protegido também em _load; mantido para diagnóstico explícito
            raise BradescoBridgeError(
                "bradesco_upload_indisponivel",
                "gpt_bradesco.py não expõe função de upload compatível com o OCR.",
                500,
            )

        identifier = self._extract_identifier(result, self._ID_KEYS)
        path = self._extract_identifier(result, self._PATH_KEYS)
        if identifier or path:
            return RemoteFile(nome=remote_name, identificador=identifier, caminho=path or remote_name)
        listed = self._list_remote_file(remote_name)
        return RemoteFile(
            nome=remote_name,
            identificador=listed.identificador,
            caminho=listed.caminho or remote_name,
        )

    def _hybrid_payload(self, remote: RemoteFile, async_mode: bool) -> dict[str, Any]:
        """Monta o payload híbrido no formato demonstrado pelo módulo corporativo."""
        payload: dict[str, Any] = {
            "detailed_output": "true",
            "async_mode": "true" if async_mode else "false",
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
            "warning_settings": {"enabled": "true"},
        }
        if remote.identificador:
            payload["files_id"] = [remote.identificador]
        else:
            payload["files_path"] = [remote.caminho or remote.nome]
            payload["container"] = self.settings.bradesco_ocr_container
        return payload

    @staticmethod
    def _ocr_instruction() -> str:
        """Orienta OCR a preservar conteúdo útil aos parâmetros do cálculo."""
        return (
            "Extraia integralmente o texto do PDF em português, preservando números, datas, "
            "percentuais, índices, tabelas, títulos e separação de páginas. Não resuma, não "
            "interprete juridicamente e não descarte trechos."
        )

    def _wait_if_available(self, result: Any) -> Any:
        """Aguarda workflow somente quando o módulo expõe essa operação."""
        workflow_id = self._extract_identifier(result, self._WORKFLOW_KEYS)
        if not workflow_id:
            return result
        module = self._load()
        wait = getattr(module, "wait_for_workflow", None)
        if not callable(wait):
            return result
        parameters = {
            "ambiente": self.settings.bradesco_environment,
            "timeout": self.settings.bradesco_timeout_seconds,
            "poll_interval": self.settings.bradesco_ocr_poll_interval_seconds,
            "max_wait_seconds": self.settings.bradesco_ocr_max_wait_seconds,
        }
        return self._invoke_callable("aguardar OCR", wait, [(workflow_id, parameters), (workflow_id,)])

    def _run_ocr(self, remote: RemoteFile) -> Any:
        """Escolhe automaticamente a melhor função de OCR disponível."""
        module = self._load()
        parameters = {"ambiente": self.settings.bradesco_environment, "timeout": self.settings.bradesco_timeout_seconds}

        # OCR híbrido é priorizado quando disponível, conforme o fluxo informado.
        hybrid = getattr(module, "ocr_hibrido", None)
        if callable(hybrid):
            # Sem helper de espera, solicita modo síncrono para obter texto na mesma chamada.
            async_mode = callable(getattr(module, "wait_for_workflow", None))
            payload = self._hybrid_payload(remote, async_mode=async_mode)
            result = self._invoke_callable("OCR híbrido", hybrid, [(payload, parameters), (payload,)])
            return self._wait_if_available(result)

        # Algumas versões expõem o OCR genérico como função ``ocr``.
        generic = getattr(module, "ocr", None)
        if callable(generic):
            payload = {
                "files_path": [remote.caminho or remote.nome],
                "container": self.settings.bradesco_ocr_container,
                "input_text": self._ocr_instruction(),
            }
            return self._invoke_callable("OCR", generic, [(payload, parameters), (payload,)])

        generator = getattr(module, "ocr_generator", None)
        if callable(generator):
            payload = {
                "files_path": [remote.caminho or remote.nome],
                "container": self.settings.bradesco_ocr_container,
                "input_text": self._ocr_instruction(),
                "async_mode": False,
            }
            return self._invoke_callable("OCR", generator, [(payload, parameters), (payload,)])

        legacy = getattr(module, "get_text_ocr", None)
        if callable(legacy):
            return self._invoke_callable(
                "OCR",
                legacy,
                [([remote.caminho or remote.nome], self.settings.bradesco_ocr_container, self._ocr_instruction())],
            )

        raise BradescoBridgeError(
            "bradesco_ocr_indisponivel",
            "gpt_bradesco.py não expõe função de OCR compatível.",
            500,
        )

    @staticmethod
    def _page_number(mapping: Mapping[str, Any], page_keys: tuple[str, ...]) -> int | None:
        """Converte identificadores de página sem aceitar booleanos ou negativos."""
        normalized = {key.casefold() for key in page_keys}
        for key, value in mapping.items():
            if str(key).casefold() not in normalized or isinstance(value, bool):
                continue
            try:
                number = int(value)
            except (TypeError, ValueError):
                continue
            if number >= 0:
                return number + 1 if str(key).casefold() in {"page_index", "pageindex"} else max(1, number)
        return None

    def _pages_from_payload(self, payload: Any) -> list[OcrPage]:
        """Normaliza diferentes envelopes de OCR preservando página quando possível."""
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
                pages[number] = pages[number] + "\n" + text if number in pages and text not in pages[number] else text
        if pages:
            return [OcrPage(numero=number, texto=pages[number]) for number in sorted(pages)]

        text = self._find_first_text(payload, self._TEXT_KEYS)
        if not text and isinstance(payload, str):
            text = payload.strip()
        if not text:
            return []
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
                page_text = text[start:end].strip()
                if page_text:
                    result.append(OcrPage(numero=int(match.group(1)), texto=page_text))
            if result:
                return result
        return [OcrPage(numero=1, texto=text)]

    def _cleanup_remote(self, remote: RemoteFile) -> None:
        """Remove o objeto remoto somente se a função estiver disponível; falha não invalida OCR."""
        if not remote.identificador:
            return
        module = self._load()
        try:
            if callable(getattr(module, "file_manager_delete", None)):
                self._call_variants("limpeza do arquivo remoto", "file_manager_delete", [(remote.identificador,)])
            elif callable(getattr(module, "file_manager_delete_file", None)):
                payload = {"file_id": remote.identificador}
                parameters = {"ambiente": self.settings.bradesco_environment, "timeout": self.settings.bradesco_timeout_seconds}
                self._call_variants("limpeza do arquivo remoto", "file_manager_delete_file", [(payload, parameters), (payload,)])
        except BradescoBridgeError:
            logger.warning("bradesco_remote_cleanup_failed", extra={"error_type": "cleanup_failed"})

    def ocr_pdf(self, name: str, content: bytes, expected_pages: int) -> OcrDocument:
        """Executa upload + OCR automaticamente assim que o PDF entra na extração."""
        if not content.startswith(b"%PDF-"):
            raise BradescoBridgeError("bradesco_pdf_invalido", "O OCR recebeu conteúdo que não é PDF.", 400)
        remote: RemoteFile | None = None
        warnings: list[str] = []
        try:
            remote = self._upload_pdf(name, content)
            result = self._run_ocr(remote)
            pages = self._pages_from_payload(result)
            if not pages:
                workflow_id = self._extract_identifier(result, self._WORKFLOW_KEYS)
                if workflow_id:
                    raise BradescoBridgeError(
                        "bradesco_ocr_assincrono_sem_retorno",
                        "O OCR foi iniciado, mas esta versão de gpt_bradesco.py não devolveu o texto concluído nem disponibilizou uma função de espera compatível.",
                    )
                raise BradescoBridgeError("bradesco_ocr_sem_texto", "O OCR corporativo foi concluído, mas não retornou texto utilizável.")
            if len(pages) == 1 and expected_pages > 1:
                warnings.append(
                    f"OCR de {name}: o serviço retornou texto sem separação confiável das {expected_pages} páginas; confira visualmente as evidências."
                )
            return OcrDocument(nome=name, paginas=tuple(pages), alertas=tuple(warnings))
        finally:
            if remote is not None:
                self._cleanup_remote(remote)

    def generate_text(self, payload: str, *, max_tokens: int) -> str:
        """Executa qualquer prompt da calculadora exclusivamente por ``text_generator``."""
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
        }
        response = self._call_variants("geração de texto", "text_generator", [(payload, parameters)])
        if not isinstance(response, str) or not response.strip():
            raise BradescoBridgeError("bradesco_saida_vazia", "O gerador corporativo não retornou texto para a etapa de extração.")
        return response.strip()
