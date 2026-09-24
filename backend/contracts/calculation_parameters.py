"""Contratos dos parâmetros de cálculo, separados do transporte HTTP.

A API pública permanece retrocompatível e plana. A composição em classes menores
faz cada grupo de regras ter uma única responsabilidade e permite conversão para
o modelo de domínio normalizado sem contaminar os endpoints.
"""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import AliasChoices, Field, model_validator

from backend.contracts.base import Contract, FlexibleAmount, InterestType, Money, Month, Periodicity, Rate


class MonetaryUpdateParameters(Contract):
    """Atualização monetária e competência de cálculo."""

    mes_atualizacao: Month
    ano_atualizacao: int = Field(ge=1900, le=2200)
    indice: str = Field(min_length=1, max_length=120)
    deflacionar_valor_nominal: bool | None = None
    competencia_final_taxa_legal: str | None = Field(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$")


class CompensatoryInterestParameters(Contract):
    """Juros compensatórios."""

    juros_compensatorios_tipo: InterestType
    juros_compensatorios_taxa: Rate | None = None
    juros_compensatorios_periodicidade: Periodicity | None = None
    juros_compensatorios_pro_rata: bool | None = None
    juros_compensatorios_data_inicio: date | None = None


class MoratoryInterestParameters(Contract):
    """Juros moratórios."""

    juros_moratorios_tipo: InterestType
    juros_moratorios_taxa: Rate | None = None
    juros_moratorios_periodicidade: Periodicity | None = None
    juros_moratorios_pro_rata: bool | None = None
    juros_moratorios_data_inicio: date | None = None
    juros_moratorios_sobre_compensatorios: bool | None = None


class PenaltyAndFeeParameters(Contract):
    """Multa, honorários e art. 523 com modalidade explicitamente tipada."""

    incidir_multa_sobre_juros_compensatorios: bool | None = None
    incidir_multa_sobre_juros_moratorios: bool | None = None
    incidir_multa_sobre_parcelas_a_vencer: bool | None = None
    incidir_honorarios_sobre_multa: bool | None = None
    multa_valor: FlexibleAmount | None = Field(default=None, validation_alias=AliasChoices("multa_valor", "multa_percentual"))
    multa_tipo: Literal["percentual", "fixo"] | None = None
    honorarios: FlexibleAmount | None = None
    honorarios_tipo: Literal["percentual", "fixo"] | None = None
    art_523: Literal["nao_aplicar", "aplicar_multa", "aplicar_multa_honorarios"] | None = None


class PrescriptionParameters(Contract):
    """Prescrição e referência temporal."""

    prescricao_flag: bool | None = None
    prescricao_anos: int | None = Field(default=None, ge=0, le=100)
    prescricao_data_referencia_tipo: Literal["data_ajuizamento", "data_decisao", "data_ultima_parcela"] | None = None
    prescricao_data_referencia: date | None = None


class CompensationParameters(Contract):
    """Compensação percentual ou fixa."""

    compensacao_flag: bool | None = None
    compensacao_tipo_calculo: Literal["percentual", "fixo"] | None = None
    compensacao_valor: FlexibleAmount | None = None


class DualIndexParameters(Contract):
    """Dois intervalos de correção monetária."""

    duplo_indice_flag: bool | None = None
    duplo_indice_primeiro_indice: str | None = None
    duplo_indice_primeiro_data_inicio: date | None = None
    duplo_indice_primeiro_data_fim: date | None = None
    duplo_indice_primeiro_valor_parcela: Money | None = None
    duplo_indice_segundo_indice: str | None = None
    duplo_indice_segundo_data_inicio: date | None = None
    duplo_indice_segundo_data_fim: date | None = None
    duplo_indice_segundo_valor_parcela: Money | None = None


class CalculationParameters(
    MonetaryUpdateParameters,
    CompensatoryInterestParameters,
    MoratoryInterestParameters,
    PenaltyAndFeeParameters,
    PrescriptionParameters,
    CompensationParameters,
    DualIndexParameters,
):
    """Contrato externo composto; o domínio interno usa uma representação aninhada."""

    valor_dobrado_flag: bool | None = None

    @model_validator(mode="after")
    def require_active_fields(self) -> "CalculationParameters":
        """Valida apenas dependências estruturais dos grupos habilitados."""
        for prefix in ("juros_compensatorios", "juros_moratorios"):
            if getattr(self, prefix + "_tipo") in {"capitalizacao_simples", "capitalizacao_composta"}:
                if getattr(self, prefix + "_taxa") is None or getattr(self, prefix + "_periodicidade") is None:
                    raise ValueError(f"Informe taxa e periodicidade para {prefix}.")
        required: list[str] = []
        if self.prescricao_flag:
            required += ["prescricao_anos", "prescricao_data_referencia_tipo"]
            if self.prescricao_data_referencia_tipo != "data_ultima_parcela":
                required += ["prescricao_data_referencia"]
        if self.compensacao_flag:
            required += ["compensacao_tipo_calculo", "compensacao_valor"]
        if self.duplo_indice_flag:
            required += [f"duplo_indice_{part}_{field}" for part in ("primeiro", "segundo") for field in ("indice", "data_inicio", "data_fim")]
        missing = [field for field in required if getattr(self, field) is None or getattr(self, field) == ""]
        if missing:
            raise ValueError("Complete os parâmetros habilitados: " + ", ".join(missing))
        return self
