"""Contratos de saída do motor e recomendações operacionais."""
from __future__ import annotations

from pydantic import Field

from backend.calculation_policy import CalculationOrigin
from backend.contracts.base import Contract, Month, Scalar
from backend.contracts.calculation_parameters import CalculationParameters


class DataTable(Contract):
    colunas: list[str]
    linhas: list[list[Scalar]]


class SummaryEntry(Contract):
    campo: str
    valor: str


class CalculationMetadata(Contract):
    entrada_sha256: str
    politica_sha256: str
    motor_sha256: str
    indices_sha256: str
    duracao_ms: float
    revisao_humana_confirmada: bool


class CalculationResponse(Contract):
    origem_calculo: CalculationOrigin
    numero_processo: str | None
    identificador_calculo: str
    memoria: DataTable
    resumo: list[SummaryEntry]
    parametros: CalculationParameters
    metadata: CalculationMetadata


class CalculationDefaults(Contract):
    mes: Month
    ano: int
    competencia_recomendada: str | None = Field(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    ajustada_por_disponibilidade: bool = False
    mensagem: str | None = None
