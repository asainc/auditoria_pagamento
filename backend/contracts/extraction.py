"""Contratos de extração, evidência e política de parâmetros."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import Field

from backend.calculation_policy import CalculationOrigin
from backend.contracts.base import Contract, DamageType, EvidenceEffect, EvidenceNature, ProcessId, Scalar
from backend.contracts.calculation import Installment
from backend.contracts.document import DocumentMetadata


class AiUsage(Contract):
    etapa: str
    modelo: str
    # Contadores reais, somente quando o gateway os fornece explicitamente.
    tokens_entrada: int | None = Field(default=None, ge=0)
    tokens_entrada_cache: int | None = Field(default=None, ge=0)
    tokens_saida: int | None = Field(default=None, ge=0)
    tokens_total: int | None = Field(default=None, ge=0)
    # Estimativas locais são separadas dos contadores reais e nunca tratadas como cobrança.
    tokens_estimados_entrada: int | None = Field(default=None, ge=0)
    tokens_estimados_saida: int | None = Field(default=None, ge=0)
    origem_tokens: Literal["gateway", "estimativa_local", "cache", "indisponivel"] = "indisponivel"
    custo_estimado_usd: Decimal | None = Field(default=None, ge=0, decimal_places=6)
    duracao_ms: float = Field(ge=0)
    paginas_contexto: int | None = Field(default=None, ge=0)
    caracteres_entrada: int | None = Field(default=None, ge=0)
    caracteres_saida: int | None = Field(default=None, ge=0)
    cache_hit: bool = False
    request_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    correcao_estrutural: bool = False


class AiUsageSummary(Contract):
    chamadas: int = Field(ge=0)
    chamadas_api: int = Field(default=0, ge=0)
    acertos_cache: int = Field(default=0, ge=0)
    tokens_entrada: int | None = Field(default=None, ge=0)
    tokens_entrada_cache: int | None = Field(default=None, ge=0)
    tokens_saida: int | None = Field(default=None, ge=0)
    tokens_total: int | None = Field(default=None, ge=0)
    tokens_estimados_total: int | None = Field(default=None, ge=0)
    custo_estimado_usd: Decimal | None = Field(default=None, ge=0, decimal_places=6)
    duracao_total_ms: float = Field(default=0, ge=0)
    detalhamento: list[AiUsage] = Field(default_factory=list)


class ExtractionRequest(Contract):
    numero_processo: ProcessId


class ExtractionStatus(Contract):
    numero_processo: str
    identificador: str
    estado: Literal["aguardando", "executando", "pronto", "falha", "bloqueada", "interrompida"]
    etapa: str
    mensagem: str
    atualizado_em: str
    codigo_erro: str | None = None
    uso_ia: AiUsageSummary | None = None


class ExtractionConfiguration(Contract):
    provedor: Literal["bradesco_iagen"] = "bradesco_iagen"
    configurada: bool
    modelo: str
    mensagem: str
    leitura_documental: str
    tokens_disponiveis: bool = False
    custo_disponivel: bool = False


class UploadResponse(Contract):
    documentos: list[DocumentMetadata]
    extracoes: list[ExtractionStatus]


class FieldEvidence(Contract):
    campo: str
    valor: Scalar
    documento: str
    pagina: int = Field(ge=1)
    trecho: str
    escopo: Literal["caso_concreto", "jurisprudencia_citada", "indeterminado"]
    natureza: EvidenceNature = "indeterminado"
    efeito: EvidenceEffect = "informa"


class OperationalAdjustment(Contract):
    campo: str
    valor: Scalar
    motivo: str


class ChronologyDecision(Contract):
    campo: str
    valor: Scalar
    documento: str
    pagina: int
    sequencia: int
    natureza: EvidenceNature
    efeito: EvidenceEffect
    motivo: str


class ExtractionResult(Contract):
    numero_processo: str
    campos: list[FieldEvidence]
    parcelas: list[Installment]
    alertas: list[str]
    versao_prompts: str
    parametros_consolidados: dict[str, Scalar] = Field(default_factory=dict)
    decisoes_cronologicas: list[ChronologyDecision] = Field(default_factory=list)
    ajustes_operacionais: list[OperationalAdjustment] = Field(default_factory=list)
    honorarios_sobre_danos_morais: bool = False
    competencia_automatica: bool = False
    uso_ia: AiUsageSummary | None = None


class ParameterOption(Contract):
    value: Scalar
    label: str
    hidden: bool = False


class ParameterCatalogItem(Contract):
    key: str
    label: str
    type: Literal["text", "number", "date", "select", "checkbox"]
    section: str
    options: list[ParameterOption] | None = None
    help: str | None = None
    damageTypes: list[DamageType] | None = None


class CalculationPolicyView(Contract):
    origem_calculo: CalculationOrigin
    parametros_padrao: dict[str, Scalar]
    campos_obrigatorios: list[str]
    catalogo: list[ParameterCatalogItem]
