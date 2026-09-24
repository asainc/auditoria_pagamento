"""Contratos de entrada de cálculo e preparação de parcelas."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import Field, model_validator

from backend.calculation_identity import display_process_number
from backend.calculation_policy import CalculationOrigin, apply_missing_defaults
from backend.contracts.base import CalculationIdentifier, Contract, DamageType, Money, ProcessId, Rate
from backend.contracts.calculation_parameters import CalculationParameters


class Installment(Contract):
    """Parcela revisada e congelada dentro de uma versão."""

    data: date
    valor_singelo: Money
    descricao: str = Field(default="", max_length=500)
    verba_tipo: DamageType
    multiplicador: Literal[1, 2] | None = None
    origem: Literal["informada", "honorarios_dano_moral"] = "informada"


class CalculationDraft(Contract):
    """Entrada completa antes da confirmação humana definitiva."""

    origem_calculo: CalculationOrigin
    numero_processo: ProcessId | None = None
    identificador_calculo: CalculationIdentifier | None = None
    parcelas: list[Installment] = Field(min_length=1, max_length=10000)
    parametros: CalculationParameters
    revisao_humana_confirmada: bool = False
    honorarios_sobre_danos_morais: bool = False
    competencia_automatica: bool = False

    @model_validator(mode="before")
    @classmethod
    def apply_origin_defaults(cls, raw: object) -> object:
        """Normaliza identidade e aplica padrões oficiais antes da validação."""
        if not isinstance(raw, dict):
            return raw
        prepared = dict(raw)
        origin = str(prepared.get("origem_calculo") or "")
        if origin not in {"manual", "processo"}:
            return prepared
        if origin == "processo" and prepared.get("numero_processo"):
            canonical_process = display_process_number(str(prepared.get("numero_processo")))
            prepared["numero_processo"] = canonical_process
            prepared["identificador_calculo"] = canonical_process
        prepared["parametros"] = apply_missing_defaults(dict(prepared.get("parametros") or {}), origin)  # type: ignore[arg-type]
        return prepared

    @model_validator(mode="after")
    def validate_origin_identity(self) -> "CalculationDraft":
        """Garante uma única identidade de negócio por origem."""
        if self.origem_calculo == "manual":
            if self.numero_processo is not None:
                raise ValueError("Cálculo manual não deve informar numero_processo.")
            if self.identificador_calculo is None:
                raise ValueError("identificador_calculo é obrigatório para cálculos manuais.")
        if self.origem_calculo == "processo":
            if self.numero_processo is None:
                raise ValueError("numero_processo é obrigatório para cálculos de processo.")
            if self.identificador_calculo != self.numero_processo:
                raise ValueError("Em cálculo de processo, identificador_calculo deve corresponder ao numero_processo.")
        return self


class CalculationRequest(CalculationDraft):
    revisao_humana_confirmada: Literal[True]


class FeePreparation(Contract):
    parcelas: list[Installment] = Field(max_length=10000)
    percentual: Rate
