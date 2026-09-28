"""Contrato externo tolerante a omissões seguras; limites permanecem no contrato interno."""
from typing import Literal

from pydantic import Field, model_validator

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
    numero_contrato: str | None = Field(default=None, max_length=120, exclude=True)
    verba_tipo: DamageType
    multiplicador: Literal[1, 2] | None = None

    @model_validator(mode="after")
    def include_contract_in_description(self) -> "WireInstallment":
        """Acrescenta o contrato à descrição sem criar novo campo no motor."""
        contract = (self.numero_contrato or "").strip()
        if not contract:
            return self
        marker = f"Contrato: {contract}"
        if marker.casefold() not in self.descricao.casefold():
            self.descricao = f"{marker} — {self.descricao}" if self.descricao else marker
        return self


class WireExtractionFragment(Contract):
    """Estrutura mínima retornada por cada prompt especializado."""

    campos: list[WireEvidence] = []
    parcelas: list[WireInstallment] = []
    alertas: list[str] = []
