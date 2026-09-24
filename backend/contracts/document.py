"""Contratos do domínio documental."""
from backend.contracts.base import Contract


class DocumentMetadata(Contract):
    identificador: str
    numero_processo: str
    nome: str
    sha256: str
    tamanho_bytes: int
    paginas: int
    classificacao: str


class ProcessSummary(Contract):
    numero_processo: str
    quantidade_documentos: int
