"""Contratos do catálogo e atualização de índices."""
from typing import Literal

from pydantic import Field

from backend.contracts.base import Contract


class IndexOption(Contract):
    chave: str
    nome: str
    nome_base: str
    disponivel: bool = True
    modo: Literal["rate_decimal", "value_index", "sem_correcao", "indisponivel"]
    competencia_inicial: str | None = Field(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    competencia_final: str | None = Field(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    competencia_maxima_atualizacao: str | None = Field(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")


class IndexStatus(Contract):
    estado: Literal["nao_verificado", "atualizado", "sem_novidade", "falha", "executando"]
    mensagem: str
    atualizado_em: str | None = None
    arquivos_sha256: dict[str, str]
