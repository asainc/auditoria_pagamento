"""Contratos de execução e importação em lote."""
from pydantic import Field

from backend.contracts.base import Contract
from backend.contracts.calculation import CalculationDraft, CalculationRequest, VersionedCalculationResponse


class BatchRequest(Contract):
    processos: list[CalculationRequest] = Field(min_length=1, max_length=100)


class BatchItem(Contract):
    numero_processo: str | None
    resultado: VersionedCalculationResponse | None = None
    erro: str | None = None


class BatchResponse(Contract):
    resultados: list[BatchItem]


class BatchImport(Contract):
    processos: list[CalculationDraft]
    erros: list[str]
