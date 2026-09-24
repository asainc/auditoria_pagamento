"""Modelo de domínio dos parâmetros jurídico-financeiros.

O contrato HTTP permanece plano para não quebrar clientes existentes. Antes de
entrar na orquestração, os campos são convertidos para objetos coesos e tipados,
separando atualização, juros, valores percentuais/fixos, prescrição e duplo índice.
O motor legado continua recebendo o contrato plano por meio de ``contrato_flat``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

from backend.contracts.calculation_parameters import CalculationParameters


@dataclass(frozen=True)
class AmountRule:
    """Valor percentual ou monetário com semântica explícita e mutuamente exclusiva."""

    tipo: Literal["percentual", "fixo"]
    percentual: Decimal | None = None
    valor_fixo: Decimal | None = None

    @classmethod
    def build(cls, tipo: str | None, valor: Decimal | None) -> "AmountRule | None":
        """Converte o par legado tipo/valor sem misturar taxa e dinheiro no domínio."""
        if tipo is None or valor is None:
            return None
        decimal_value = Decimal(str(valor))
        if tipo == "percentual":
            return cls(tipo="percentual", percentual=decimal_value)
        if tipo == "fixo":
            return cls(tipo="fixo", valor_fixo=decimal_value)
        raise ValueError(f"Modalidade de valor não suportada: {tipo}")


@dataclass(frozen=True)
class MonetaryUpdateRule:
    """Critério e competência de atualização monetária."""

    mes: str
    ano: int
    indice: str
    deflacionar: bool | None
    competencia_final_taxa_legal: str | None


@dataclass(frozen=True)
class InterestRule:
    """Regra de juros com todos os atributos que pertencem ao mesmo conceito."""

    tipo: str
    taxa: Decimal | None
    periodicidade: str | None
    pro_rata: bool | None
    data_inicio: date | None
    sobre_compensatorios: bool | None = None


@dataclass(frozen=True)
class PrescriptionRule:
    """Configuração da prescrição; campos inativos permanecem nulos."""

    ativa: bool
    anos: int | None
    referencia_tipo: str | None
    referencia: date | None


@dataclass(frozen=True)
class DualIndexSegment:
    """Um intervalo fechado de uma regra de duplo índice."""

    indice: str | None
    inicio: date | None
    fim: date | None
    valor_parcela: Decimal | None


@dataclass(frozen=True)
class DualIndexRule:
    """Regra completa de dois índices com dois segmentos explícitos."""

    ativo: bool
    primeiro: DualIndexSegment
    segundo: DualIndexSegment


@dataclass(frozen=True)
class NormalizedCalculationParameters:
    """Visão interna orientada ao domínio; não é serializada diretamente na API."""

    atualizacao: MonetaryUpdateRule
    juros_compensatorios: InterestRule
    juros_moratorios: InterestRule
    multa: AmountRule | None
    honorarios: AmountRule | None
    compensacao: AmountRule | None
    prescricao: PrescriptionRule
    duplo_indice: DualIndexRule
    art_523: str | None
    valor_dobrado: bool
    contrato_flat: dict[str, object]


def _decimal(value: object | None) -> Decimal | None:
    """Normaliza numerais Pydantic para Decimal sem introduzir float."""
    return Decimal(str(value)) if value is not None else None


def normalize_parameters(parameters: CalculationParameters) -> NormalizedCalculationParameters:
    """Converte o contrato plano em grupos coesos sem alterar a entrada do motor."""
    flat = parameters.model_dump(mode="json")
    return NormalizedCalculationParameters(
        atualizacao=MonetaryUpdateRule(
            mes=parameters.mes_atualizacao,
            ano=parameters.ano_atualizacao,
            indice=parameters.indice,
            deflacionar=parameters.deflacionar_valor_nominal,
            competencia_final_taxa_legal=parameters.competencia_final_taxa_legal,
        ),
        juros_compensatorios=InterestRule(
            tipo=parameters.juros_compensatorios_tipo,
            taxa=_decimal(parameters.juros_compensatorios_taxa),
            periodicidade=parameters.juros_compensatorios_periodicidade,
            pro_rata=parameters.juros_compensatorios_pro_rata,
            data_inicio=parameters.juros_compensatorios_data_inicio,
        ),
        juros_moratorios=InterestRule(
            tipo=parameters.juros_moratorios_tipo,
            taxa=_decimal(parameters.juros_moratorios_taxa),
            periodicidade=parameters.juros_moratorios_periodicidade,
            pro_rata=parameters.juros_moratorios_pro_rata,
            data_inicio=parameters.juros_moratorios_data_inicio,
            sobre_compensatorios=parameters.juros_moratorios_sobre_compensatorios,
        ),
        multa=AmountRule.build(parameters.multa_tipo, parameters.multa_valor),
        honorarios=AmountRule.build(parameters.honorarios_tipo, parameters.honorarios),
        compensacao=(
            AmountRule.build(parameters.compensacao_tipo_calculo, parameters.compensacao_valor)
            if parameters.compensacao_flag
            else None
        ),
        prescricao=PrescriptionRule(
            ativa=bool(parameters.prescricao_flag),
            anos=parameters.prescricao_anos,
            referencia_tipo=parameters.prescricao_data_referencia_tipo,
            referencia=parameters.prescricao_data_referencia,
        ),
        duplo_indice=DualIndexRule(
            ativo=bool(parameters.duplo_indice_flag),
            primeiro=DualIndexSegment(
                indice=parameters.duplo_indice_primeiro_indice,
                inicio=parameters.duplo_indice_primeiro_data_inicio,
                fim=parameters.duplo_indice_primeiro_data_fim,
                valor_parcela=_decimal(parameters.duplo_indice_primeiro_valor_parcela),
            ),
            segundo=DualIndexSegment(
                indice=parameters.duplo_indice_segundo_indice,
                inicio=parameters.duplo_indice_segundo_data_inicio,
                fim=parameters.duplo_indice_segundo_data_fim,
                valor_parcela=_decimal(parameters.duplo_indice_segundo_valor_parcela),
            ),
        ),
        art_523=parameters.art_523,
        valor_dobrado=bool(parameters.valor_dobrado_flag),
        contrato_flat=flat,
    )
