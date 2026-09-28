"""Contratos de aprendizado supervisionado e qualidade da extração."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import Field

from backend.calculation_policy import CalculationOrigin
from backend.contracts.base import Contract, ProcessId, Scalar
from backend.contracts.calculation import Installment

FeedbackAction = Literal["confirmed", "corrected", "removed", "added", "not_found", "ambiguous"]
FeedbackReasonCode = Literal[
    "confirmado_sem_alteracao",
    "decisao_posterior_prevalece",
    "documento_incorreto",
    "pagina_incorreta",
    "valor_interpretado_incorretamente",
    "data_interpretada_incorretamente",
    "regra_nao_se_aplica",
    "campo_ausente_no_documento",
    "contrato_incorreto",
    "parcela_associada_ao_contrato_errado",
    "classificacao_documento_incorreta",
    "ambiguidade_documental",
    "adicao_manual",
    "nao_informado",
    "outro",
]
CurationStatus = Literal["pending", "approved", "rejected"]


class ReviewSnapshotInput(Contract):
    """Snapshot do estado revisado usado para comparar IA × humano no servidor."""

    origem_calculo: CalculationOrigin
    numero_processo: ProcessId | None = None
    rascunho_id: str = Field(min_length=8, max_length=80)
    extracao_id: str | None = Field(default=None, max_length=80)
    parametros: dict[str, Scalar] = Field(default_factory=dict)
    parametros_por_dano: dict[str, dict[str, Scalar]] = Field(default_factory=dict)
    parcelas: list[Installment] = Field(default_factory=list)


class FeedbackEventRecord(Contract):
    identificador: str
    numero_processo: str | None = None
    rascunho_id: str
    extracao_id: str | None = None
    campo: str
    acao: FeedbackAction
    motivo_codigo: FeedbackReasonCode
    comentario: str | None = None
    valor_modelo: Scalar = None
    valor_humano: Scalar = None
    documento: str | None = None
    pagina: int | None = Field(default=None, ge=1)
    evidencia_modelo: str | None = None
    tipo_documento: str | None = None
    versao_prompts: str | None = None
    modelo: str | None = None
    pipeline_version: str
    revisor_pseudonimo: str
    criado_em: str
    status_curadoria: CurationStatus


class ReviewCaptureResult(Contract):
    eventos_criados: int = Field(ge=0)
    confirmados: int = Field(ge=0)
    corrigidos: int = Field(ge=0)
    pendentes_curadoria: int = Field(ge=0)


class FeedbackCurationInput(Contract):
    status: Literal["approved", "rejected"]
    motivo_codigo: FeedbackReasonCode | None = None
    comentario: str | None = Field(default=None, max_length=1000)


class FeedbackFieldMetric(Contract):
    campo: str
    total: int = Field(ge=0)
    confirmados: int = Field(ge=0)
    corrigidos: int = Field(ge=0)
    removidos: int = Field(ge=0)
    adicionados: int = Field(ge=0)
    taxa_intervencao: Decimal = Field(ge=0, le=1, decimal_places=6)


class FeedbackReasonMetric(Contract):
    motivo_codigo: str
    quantidade: int = Field(ge=0)


class QualitySummary(Contract):
    total_eventos: int = Field(ge=0)
    confirmados: int = Field(ge=0)
    corrigidos: int = Field(ge=0)
    removidos: int = Field(ge=0)
    adicionados: int = Field(ge=0)
    pendentes_curadoria: int = Field(ge=0)
    taxa_intervencao: Decimal = Field(ge=0, le=1, decimal_places=6)
    por_campo: list[FeedbackFieldMetric] = Field(default_factory=list)
    motivos: list[FeedbackReasonMetric] = Field(default_factory=list)


class FeedbackPage(Contract):
    itens: list[FeedbackEventRecord]
    pagina: int = Field(ge=1)
    tamanho_pagina: int = Field(ge=1)
    total_itens: int = Field(ge=0)
    total_paginas: int = Field(ge=0)


class DatasetSnapshot(Contract):
    identificador: str
    criado_em: str
    criado_por: str
    sha256: str
    quantidade_exemplos: int = Field(ge=0)


class LearningExample(Contract):
    campo: str
    tarefa: str
    evidencia: str | None = None
    valor_modelo: Scalar = None
    valor_esperado: Scalar = None
    motivo_codigo: str


class FinOpsStageMetric(Contract):
    etapa: str
    chamadas_api: int = Field(ge=0)
    falhas_api: int = Field(default=0, ge=0)
    acertos_cache: int = Field(ge=0)
    caracteres_entrada: int = Field(ge=0)
    caracteres_saida: int = Field(ge=0)
    tokens_reais: int | None = Field(default=None, ge=0)
    tokens_estimados: int = Field(ge=0)
    custo_estimado_usd: Decimal | None = Field(default=None, ge=0, decimal_places=6)


class FinOpsSummary(Contract):
    periodo_dias: int = Field(ge=1)
    chamadas_api: int = Field(ge=0)
    falhas_api: int = Field(default=0, ge=0)
    acertos_cache: int = Field(ge=0)
    taxa_cache: Decimal = Field(ge=0, le=1, decimal_places=6)
    caracteres_entrada: int = Field(ge=0)
    caracteres_saida: int = Field(ge=0)
    tokens_reais: int | None = Field(default=None, ge=0)
    tokens_estimados: int = Field(ge=0)
    custo_estimado_usd: Decimal | None = Field(default=None, ge=0, decimal_places=6)
    origem_tokens: Literal["gateway", "estimativa_local", "mista", "cache", "indisponivel"]
    economia_chamadas_cache: int = Field(ge=0)
    orcamento_mensal_usd: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    consumo_mes_estimado_usd: Decimal | None = Field(default=None, ge=0, decimal_places=6)
    percentual_orcamento: Decimal | None = Field(default=None, ge=0, decimal_places=6)
    status_orcamento: Literal["not_configured", "unavailable", "ok", "warning", "exceeded"] = "not_configured"
    por_etapa: list[FinOpsStageMetric] = Field(default_factory=list)
