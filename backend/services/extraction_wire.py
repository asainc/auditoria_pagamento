"""Contrato externo tolerante a omissões seguras; limites permanecem no contrato interno."""
from typing import Literal

from backend.models import (
    Contract,
    DamageType,
    EvidenceEffect,
    EvidenceNature,
    FieldEvidence,
)


class WireEvidence(FieldEvidence):
    """Evidência recebida do gerador com defaults somente para metadados de classificação.

    ``natureza`` e ``efeito`` não alteram o valor factual extraído. Quando o
    gerador os omite, o backend assume explicitamente os estados conservadores
    ``indeterminado`` e ``informa`` e mantém a evidência sujeita à revisão humana.
    """

    pagina: int
    natureza: EvidenceNature = "indeterminado"
    efeito: EvidenceEffect = "informa"


class WireInstallment(Contract):
    """Parcela no transporte; descrição é opcional e não participa do cálculo."""

    data: str
    valor_singelo: str
    descricao: str = ""
    verba_tipo: DamageType


class WireFinancialEvent(Contract):
    """Evento financeiro com defaults equivalentes ao contrato interno.

    A validação interna continua exigindo data quando o critério escolhido torna
    o evento calculável. Portanto, estes defaults não relaxam regras do motor.
    """

    tipo: Literal["deposito_judicial", "pagamento_parcial", "compensacao", "levantamento"]
    data: str | None = None
    valor: str
    criterio: Literal["abater_na_data_do_pagamento", "descontar_no_final", "informativo"]
    indice_atualizacao: str | None = None
    aplicar_juros_apos_evento: bool = False


class WireExtractionFragment(Contract):
    """Estrutura mínima retornada por cada prompt especializado."""

    campos: list[WireEvidence] = []
    parcelas: list[WireInstallment] = []
    eventos_financeiros: list[WireFinancialEvent] = []
    alertas: list[str] = []
