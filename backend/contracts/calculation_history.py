"""Contratos de versionamento, execução, artefatos e histórico."""
from __future__ import annotations

from typing import Literal

from pydantic import Field

from backend.calculation_policy import CalculationOrigin
from backend.contracts.base import Contract, Scalar
from backend.contracts.calculation_input import CalculationRequest, Installment
from backend.contracts.calculation_output import CalculationResponse


class CalculationVersionRef(Contract):
    calculo_id: str = Field(pattern=r"^calc_[0-9a-f]{32}$")
    versao: int = Field(ge=1)
    versao_base: int | None = Field(default=None, ge=1)
    criado_em: str
    criada: bool = True


class CalculationExecutionRef(Contract):
    execucao_id: str = Field(pattern=r"^exec_[0-9a-f]{32}$")
    calculo_id: str = Field(pattern=r"^calc_[0-9a-f]{32}$")
    versao: int = Field(ge=1)
    executada_em: str
    nova_versao: bool = False


class VersionedCalculationResponse(CalculationResponse):
    registro: CalculationVersionRef | None = None
    execucao: CalculationExecutionRef | None = None


CalculationState = Literal["ativo", "arquivado", "cancelado"]


class CalculationFieldDiff(Contract):
    caminho: str
    valor_anterior: Scalar = None
    valor_novo: Scalar = None


class InstallmentDiff(Contract):
    posicao: int = Field(ge=1)
    acao: Literal["adicionada", "removida", "alterada"]
    campos_alterados: list[str] = Field(default_factory=list)
    antes: Installment | None = None
    depois: Installment | None = None


class CalculationDiff(Contract):
    campos: list[CalculationFieldDiff] = Field(default_factory=list)
    parcelas: list[InstallmentDiff] = Field(default_factory=list)


class CalculationExecutionSummary(Contract):
    execucao_id: str = Field(pattern=r"^exec_[0-9a-f]{32}$")
    versao: int = Field(ge=1)
    executada_em: str
    executada_por: str
    entrada_sha256: str
    politica_sha256: str
    motor_sha256: str
    indices_sha256: str
    duracao_ms: float


class CalculationExecutionsPage(Contract):
    calculo_id: str = Field(pattern=r"^calc_[0-9a-f]{32}$")
    versao: int = Field(ge=1)
    itens: list[CalculationExecutionSummary]
    pagina: int = Field(ge=1)
    tamanho_pagina: int = Field(ge=1, le=100)
    total_itens: int = Field(ge=0)
    total_paginas: int = Field(ge=0)


class CalculationVersionSummary(Contract):
    versao: int = Field(ge=1)
    versao_base: int | None = Field(default=None, ge=1)
    criado_em: str
    criado_por: str
    total_geral: str | None = None
    indice: str
    competencia_atualizacao: str
    entrada_sha256: str
    indices_sha256: str
    campos_alterados: list[str] = Field(default_factory=list)
    diff: CalculationDiff = Field(default_factory=CalculationDiff)
    quantidade_execucoes: int = Field(default=1, ge=1)
    ultima_execucao_em: str | None = None


class CalculationHistoryItem(Contract):
    calculo_id: str = Field(pattern=r"^calc_[0-9a-f]{32}$")
    origem_calculo: CalculationOrigin
    identificador_calculo: str
    numero_processo: str | None = None
    numero_processo_normalizado: str | None = None
    estado: CalculationState
    criado_em: str
    criado_por: str
    atualizado_em: str
    quantidade_versoes: int = Field(ge=1)
    quantidade_execucoes: int = Field(ge=1)
    versao_atual: int = Field(ge=1)
    total_atual: str | None = None
    indice_atual: str
    competencia_atualizacao_atual: str


class CalculationHistoryPage(Contract):
    itens: list[CalculationHistoryItem]
    pagina: int = Field(ge=1)
    tamanho_pagina: int = Field(ge=1, le=100)
    total_itens: int = Field(ge=0)
    total_paginas: int = Field(ge=0)


class CalculationVersionsPage(Contract):
    calculo_id: str = Field(pattern=r"^calc_[0-9a-f]{32}$")
    itens: list[CalculationVersionSummary]
    pagina: int = Field(ge=1)
    tamanho_pagina: int = Field(ge=1, le=100)
    total_itens: int = Field(ge=0)
    total_paginas: int = Field(ge=0)


class CalculationVersionDetail(Contract):
    calculo_id: str = Field(pattern=r"^calc_[0-9a-f]{32}$")
    origem_calculo: CalculationOrigin
    identificador_calculo: str
    numero_processo: str | None = None
    estado_calculo: CalculationState = "ativo"
    versao: int = Field(ge=1)
    versao_atual: int = Field(ge=1)
    versao_base: int | None = Field(default=None, ge=1)
    criado_em: str
    criado_por: str
    campos_alterados: list[str] = Field(default_factory=list)
    diff: CalculationDiff = Field(default_factory=CalculationDiff)
    quantidade_execucoes: int = Field(default=1, ge=1)
    requisicao: CalculationRequest
    resultado: CalculationResponse


class CalculationComparison(Contract):
    calculo_id: str = Field(pattern=r"^calc_[0-9a-f]{32}$")
    versao_origem: int = Field(ge=1)
    versao_destino: int = Field(ge=1)
    total_origem: str | None = None
    total_destino: str | None = None
    diferenca_total: str | None = None
    diff: CalculationDiff


class CalculationStateChange(Contract):
    estado: CalculationState


class CalculationStateResult(Contract):
    calculo_id: str = Field(pattern=r"^calc_[0-9a-f]{32}$")
    estado: CalculationState
    atualizado_em: str
