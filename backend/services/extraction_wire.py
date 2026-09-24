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
    """Parcela no transporte; multiplicador só é informado com suporte documental específico."""

    data: str
    valor_singelo: str
    descricao: str = ""
    verba_tipo: DamageType
    multiplicador: Literal[1, 2] | None = None


class WireExtractionFragment(Contract):
    """Estrutura mínima retornada por cada prompt especializado."""

    campos: list[WireEvidence] = []
    parcelas: list[WireInstallment] = []
    alertas: list[str] = []
