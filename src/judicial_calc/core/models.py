"""Modelos Pydantic versionados para entrada/auditoria do cálculo judicial.

Os modelos complementam a API pública principal ``calcular_debitos(parcelas,
**params)``. Eles servem como contrato interno para validação, serialização e
trilha auditável: valores extraídos por IA devem carregar fonte, evidência,
escopo e confiança antes de virarem parâmetros finais.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SCHEMA_VERSION = "2026-05-26.v1-auditavel"

TipoVerba = Literal["dano_material", "dano_moral", "honorarios", "custas"]
TipoEscopo = Literal["caso_concreto", "jurisprudencia_citada", "indeterminado"]
StatusEvidencia = Literal[
    "extraido",
    "padrao_aplicado",
    "padrao_confirmado",
    "conflito_resolvido",
    "revisar",
    "jurisprudencia_ignorada",
    "revisado_manual",
]
class StrictBaseModel(BaseModel):
    """Base comum que aceita campos extras para compatibilidade evolutiva."""

    model_config = ConfigDict(extra="allow", populate_by_name=True, str_strip_whitespace=True)


class EvidenceSource(StrictBaseModel):
    """Fonte/evidência usada para justificar um campo extraído."""

    field_path: str
    extracted_value: str = ""
    source_file: str = ""
    source_page: int | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: str = ""
    status: StatusEvidencia = "revisar"
    process_scope: TipoEscopo = "indeterminado"
    source_section: str | None = None
    document_type: str | None = None

    def is_usable_for_calculation(self) -> bool:
        """Indica se a evidência pode alimentar o cálculo final."""
        return self.process_scope == "caso_concreto" and self.status != "jurisprudencia_ignorada"


class ParcelaInput(StrictBaseModel):
    """Parcela individual calculável."""

    item: int
    descricao: str = ""
    data: date
    valor_singelo: Decimal = Field(ge=Decimal("0"))
    verba_tipo: TipoVerba = "dano_material"
    source_file: str | None = None
    source_page: int | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class VerbaJudicial(StrictBaseModel):
    """Verba consolidada por natureza jurídica."""

    tipo: TipoVerba
    descricao: str = ""
    valor_base: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    data_base: date | None = None
    source_file: str | None = None
    source_page: int | None = None
    evidence: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class PrescricaoParams(StrictBaseModel):
    """Agrupa os parâmetros estruturados de prescrição usados no contrato interno."""
    flag: int = Field(default=0, ge=0, le=1)
    anos: int | None = None
    data_referencia_tipo: Literal["data_ajuizamento", "data_decisao", "data_ultima_parcela"] | None = None
    data_referencia: date | None = None


class CompensacaoParams(StrictBaseModel):
    """Agrupa os parâmetros estruturados de compensação usados no contrato interno."""
    flag: int = Field(default=0, ge=0, le=1)
    tipo_calculo: Literal["percentual", "fixo"] = "fixo"
    valor: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))


class DuploIndiceParams(StrictBaseModel):
    """Agrupa os parâmetros das duas faixas de correção do modo de duplo índice."""
    flag: int = Field(default=0, ge=0, le=1)
    primeiro_indice: str = ""
    primeiro_data_inicio: date | None = None
    primeiro_data_fim: date | None = None
    primeiro_valor_parcela: Decimal | None = None
    segundo_indice: str = ""
    segundo_data_inicio: date | None = None
    segundo_data_fim: date | None = None
    segundo_valor_parcela: Decimal | None = None


class CalculoJudicialInput(StrictBaseModel):
    """Payload versionado completo para cálculo judicial auditável."""

    schema_version: str = SCHEMA_VERSION
    processo_id: str | None = None
    parcelas: list[ParcelaInput] = Field(default_factory=list)
    params: dict[str, Any] = Field(default_factory=dict)
    verbas: list[VerbaJudicial] = Field(default_factory=list)
    evidence_map: dict[str, list[EvidenceSource]] = Field(default_factory=dict)
    raw_extractions: list[dict[str, Any]] = Field(default_factory=list)
    validation_issues: list[dict[str, Any]] = Field(default_factory=list)
    human_review_checklist: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("params")
    @classmethod
    def params_must_be_dict(cls, value: dict[str, Any]) -> dict[str, Any]:
        """Garante que o bloco de parâmetros seja recebido como dicionário antes das demais validações."""
        return dict(value or {})

    def calculation_params(self) -> dict[str, Any]:
        """Retorna uma cópia isolada dos parâmetros destinados ao motor."""
        return dict(self.params)
