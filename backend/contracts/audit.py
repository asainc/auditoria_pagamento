"""Contratos da trilha de revisão humana."""
from __future__ import annotations

from pydantic import Field, model_validator

from backend.calculation_policy import CalculationOrigin, parameter_keys
from backend.contracts.base import Contract, ProcessId, Scalar


class ParameterChangeInput(Contract):
    origem_calculo: CalculationOrigin
    numero_processo: ProcessId | None = None
    rascunho_id: str = Field(min_length=8, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    campo: str
    valor_anterior: Scalar = None
    valor_novo: Scalar = None
    extracao_id: str | None = Field(default=None, max_length=80)

    @model_validator(mode="after")
    def validate_change(self) -> "ParameterChangeInput":
        if self.campo not in parameter_keys():
            raise ValueError("campo não pertence ao catálogo de parâmetros.")
        if self.origem_calculo == "manual" and self.numero_processo is not None:
            raise ValueError("Revisão manual não deve informar numero_processo.")
        if self.origem_calculo == "processo" and self.numero_processo is None:
            raise ValueError("numero_processo é obrigatório para revisão de processo.")
        return self


class ParameterChangeRecord(ParameterChangeInput):
    identificador: int
    registrado_em: str
    ator_tecnico: str
    valor_extraido: Scalar = None
    origem_extraida: str | None = None
