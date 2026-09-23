"""Integração mínima com ``gpt_bradesco.py`` para geração de texto.

A calculadora não usa OCR, upload de arquivos ou workflows do módulo corporativo.
Todo PDF é lido localmente com PyMuPDF e somente o texto resultante, combinado com
os prompts versionados do projeto, é enviado à função pública ``text_generator``.

Esta camada não duplica URLs, credenciais ou autenticação do módulo corporativo.
"""
from __future__ import annotations

import importlib
import inspect
import logging
import re
from typing import Any, Sequence

from backend.config import Settings
from backend.errors import ServiceError

logger = logging.getLogger("judicial")


class BradescoBridgeError(ServiceError):
    """Erro sanitizado da integração corporativa, sem conteúdo documental."""

    def __init__(self, code: str, message: str, status_code: int = 502):
        super().__init__(message, status_code)
        self.code = code


class BradescoBridgeClient:
    """Facade restrita ao ``text_generator`` do módulo corporativo.

    Responsabilidade:
        Carregar ``gpt_bradesco.py`` sob demanda, validar a presença da função
        ``text_generator`` e executar prompts com parâmetros centralizados.

    Entradas:
        ``Settings`` com deployment, timeout e parâmetros de geração.

    Saída:
        Texto retornado pelo serviço corporativo.

    Observação:
        O módulo fornecido pelo banco continua responsável por autenticação,
        endpoints e transporte. A calculadora não executa OCR nem File Manager.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self._module: Any | None = None

    @property
    def configured(self) -> bool:
        """A configuração local exige apenas um deployment de geração de texto."""
        return bool(self.settings.bradesco_text_model.strip())

    def _load(self) -> Any:
        """Importa o módulo corporativo somente na primeira chamada de prompt."""
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

        if not callable(getattr(module, "text_generator", None)):
            raise BradescoBridgeError(
                "bradesco_modulo_incompativel",
                "gpt_bradesco.py precisa expor a função text_generator(payload, parameters).",
                500,
            )

        # Algumas versões do módulo disponibilizam configuração explícita. Ela é
        # utilizada somente quando existe e há credenciais configuradas; versões
        # que autenticam internamente continuam funcionando sem adaptação.
        configure = getattr(module, "configure_iagen", None)
        if callable(configure):
            credentials = {
                "ambiente": self.settings.bradesco_environment,
                "identificador": self.settings.bradesco_identificador.get_secret_value(),
                "senha": self.settings.bradesco_senha.get_secret_value(),
                "token": self.settings.bradesco_authorization_token.get_secret_value(),
                "ca_bundle": str(self.settings.bradesco_ca_bundle) if self.settings.bradesco_ca_bundle else "",
            }
            if any(credentials[key] for key in ("identificador", "senha", "token")):
                self._invoke_callable("configuração corporativa", configure, [(credentials,)])

        self._module = module
        return module

    @staticmethod
    def _safe_request_id(value: Any) -> str | None:
        """Aceita somente identificadores técnicos curtos em mensagens de erro."""
        if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.:-]{1,120}", value):
            return value
        return None

    @staticmethod
    def _safe_status_code(exc: Exception) -> int | None:
        """Recupera apenas o código HTTP sem propagar corpo de resposta ou documento.

        Algumas versões legadas de ``gpt_bradesco.py`` levantam ``Exception`` comum
        com texto no formato ``Erro na execução: 400 - ...`` em vez de anexar
        ``status_code`` ao objeto. A calculadora extrai somente os três dígitos para
        produzir diagnóstico acionável, descartando todo o restante da mensagem.
        """
        direct = getattr(exc, "status_code", None)
        if isinstance(direct, int) and 100 <= direct <= 599:
            return direct
        match = re.search(
            r"(?:erro\s+na\s+execu[cç][aã]o|http|status(?:\s+code)?)\s*[:=]?\s*(\d{3})\b",
            str(exc),
            re.IGNORECASE,
        )
        if match:
            value = int(match.group(1))
            return value if 100 <= value <= 599 else None
        return None

    def _classify_error(self, exc: Exception, operation: str) -> BradescoBridgeError:
        """Traduz falhas externas sem ecoar prompt, documento ou credencial."""
        status_code = self._safe_status_code(exc)
        request_id = self._safe_request_id(getattr(exc, "request_id", None))
        suffix = f" Referência técnica: {request_id}." if request_id else ""
        if status_code == 400:
            return BradescoBridgeError(
                "bradesco_requisicao_rejeitada",
                "O serviço corporativo rejeitou os parâmetros da geração de texto (HTTP 400). "
                "A calculadora usa o contrato mínimo compatível com gpt_bradesco.py; valide somente o deployment habilitado no ambiente." + suffix,
            )
        if status_code == 401:
            return BradescoBridgeError(
                "bradesco_credencial_invalida",
                "A autenticação corporativa foi recusada. Revise as credenciais administradas pelo gpt_bradesco.py." + suffix,
            )
        if status_code == 403:
            return BradescoBridgeError(
                "bradesco_acesso_negado",
                "O serviço corporativo recusou a geração de texto. Valide as permissões do deployment configurado." + suffix,
            )
        if status_code == 404:
            return BradescoBridgeError(
                "bradesco_recurso_indisponivel",
                "O deployment corporativo configurado não foi encontrado." + suffix,
            )
        if status_code == 429:
            return BradescoBridgeError(
                "bradesco_limite_requisicoes",
                "O serviço corporativo limitou temporariamente as requisições. Aguarde e repita a extração." + suffix,
            )
        if isinstance(exc, (ValueError, TypeError)):
            return BradescoBridgeError(
                "bradesco_configuracao_invalida",
                f"Configuração inválida na etapa {operation}. Revise os parâmetros de geração de texto.",
                500,
            )
        if "timeout" in type(exc).__name__.lower() or "tempo máximo" in str(exc).lower():
            return BradescoBridgeError(
                "bradesco_tempo_esgotado",
                f"O serviço corporativo excedeu o tempo máximo na etapa {operation}." + suffix,
            )
        return BradescoBridgeError(
            "bradesco_indisponivel",
            f"A etapa corporativa {operation} não foi concluída. Os PDFs locais foram preservados." + suffix,
        )

    @staticmethod
    def _binds(function: Any, args: Sequence[Any]) -> bool:
        """Confere a assinatura antes da chamada para evitar tentativa por exceção."""
        try:
            inspect.signature(function).bind(*args)
            return True
        except (TypeError, ValueError):
            return False

    def _invoke_callable(self, operation: str, function: Any, variants: Sequence[Sequence[Any]]) -> Any:
        """Executa a primeira assinatura conhecida compatível com a função."""
        selected: Sequence[Any] | None = None
        for args in variants:
            if self._binds(function, args):
                selected = args
                break
        if selected is None:
            raise BradescoBridgeError(
                "bradesco_assinatura_incompativel",
                f"A função corporativa usada na etapa {operation} possui assinatura não reconhecida pela calculadora.",
                500,
            )
        try:
            return function(*selected)
        except BradescoBridgeError:
            raise
        except Exception as exc:
            logger.warning(
                "bradesco_bridge_failure",
                extra={"operation": operation, "error_type": type(exc).__name__},
            )
            raise self._classify_error(exc, operation) from None

    def generate_text(self, payload: str, *, max_tokens: int) -> str:
        """Executa qualquer prompt da calculadora exclusivamente por ``text_generator``.

        Args:
            payload: String final contendo prompt especializado + texto extraído do PDF.
            max_tokens: Limite de saída definido para a tarefa atual.

        Returns:
            String produzida pelo deployment corporativo. Para a extração, o chamador
            valida posteriormente que o conteúdo é um JSON aderente ao contrato.
        """
        module = self._load()
        function = getattr(module, "text_generator")
        # Contrato mínimo comum às versões corporativas fornecidas pelo usuário.
        # O formato estruturado é exigido no PROMPT e validado pelo backend; não
        # dependemos de ``response_format=json_object``, que alguns gateways/modelos
        # corporativos rejeitam mesmo quando conseguem produzir JSON em modo texto.
        parameters = {
            "deployment_name": self.settings.bradesco_text_model,
            "temperature": self.settings.bradesco_text_temperature,
            "max_tokens": min(max_tokens, self.settings.bradesco_text_max_tokens),
            "async_mode": False,
            "stream": False,
            "message_format": {"type": "text"},
        }
        response = self._invoke_callable("geração de texto", function, [(payload, parameters)])
        if not isinstance(response, str) or not response.strip():
            raise BradescoBridgeError(
                "bradesco_saida_vazia",
                "O gerador corporativo não retornou texto para a etapa de extração.",
            )
        return response.strip()
