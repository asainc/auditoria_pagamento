"""Cálculo, histórico versionado, execuções e exportações compartilham contratos validados."""
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request, Response

from backend.access import technical_actor
from backend.calculation_policy import CalculationOrigin, defaults_for_origin, parameter_catalog, required_parameter_keys
from backend.container import Services, services
from backend.errors import ServiceError
from backend.contracts.calculation import (
    CalculationComparison,
    CalculationDefaults,
    CalculationExecutionsPage,
    CalculationHistoryPage,
    CalculationRequest,
    CalculationState,
    CalculationStateChange,
    CalculationStateResult,
    CalculationVersionDetail,
    CalculationVersionsPage,
    FeePreparation,
    Installment,
    VersionedCalculationResponse,
)
from backend.services.operational_policy import current_competence, fee_installments
from backend.contracts.extraction import CalculationPolicyView, ParameterCatalogItem

router = APIRouter(prefix="/calculos", tags=["Cálculos"])
Dependency = Annotated[Services, Depends(services)]


@router.get("/padroes", response_model=CalculationDefaults)
def defaults(indice: str | None = None):
    """Recomenda competência sem ultrapassar a cobertura do índice selecionado."""
    return current_competence(index_key=indice)


@router.get("/politica/{origem_calculo}", response_model=CalculationPolicyView)
def calculation_policy(origem_calculo: CalculationOrigin):
    """Expõe padrões e metadados oficiais sem duplicá-los no frontend."""
    return CalculationPolicyView(
        origem_calculo=origem_calculo,
        parametros_padrao=defaults_for_origin(origem_calculo),
        campos_obrigatorios=list(required_parameter_keys()),
        catalogo=[ParameterCatalogItem.model_validate(item) for item in parameter_catalog()],
    )


@router.post("/honorarios/preparar", response_model=list[Installment])
def prepare_fees(payload: FeePreparation):
    """Mostra os valores nominais para revisão antes da chamada ao motor."""
    return fee_installments(payload.parcelas, payload.percentual)


@router.get("/historico", response_model=CalculationHistoryPage)
def history(
    service: Dependency,
    pagina: int = Query(default=1, ge=1),
    tamanho_pagina: int = Query(default=20, ge=1, le=100),
    busca: str | None = Query(default=None, max_length=120),
    origem: CalculationOrigin | None = None,
    estado: CalculationState | None = None,
    indice: str | None = Query(default=None, max_length=120),
    criado_por: str | None = Query(default=None, max_length=120),
    atualizado_de: date | None = None,
    atualizado_ate: date | None = None,
    ordenacao: Literal["processo", "atualizado_desc", "atualizado_asc", "criado_desc", "criado_asc"] = "processo",
):
    """Lista cálculos paginados; as versões são carregadas somente após expansão."""
    if atualizado_de and atualizado_ate and atualizado_de > atualizado_ate:
        raise ServiceError("A data inicial do filtro não pode ser posterior à data final.", 422)
    return service.calculation_repository.history(
        page=pagina,
        page_size=tamanho_pagina,
        search=busca,
        origin=origem,
        state=estado,
        index_name=indice,
        created_by=criado_por,
        updated_from=atualizado_de,
        updated_to=atualizado_ate,
        sort=ordenacao,
    )


@router.get("/{calculo_id}/versoes", response_model=CalculationVersionsPage)
def versions(
    calculo_id: str,
    service: Dependency,
    pagina: int = Query(default=1, ge=1),
    tamanho_pagina: int = Query(default=50, ge=1, le=100),
):
    """Lazy loading das versões de um cálculo já localizado no histórico."""
    result = service.calculation_repository.versions(calculo_id, page=pagina, page_size=tamanho_pagina)
    if result is None:
        raise ServiceError("Cálculo não encontrado.", 404, code="CALCULATION_NOT_FOUND")
    return result


@router.get("/{calculo_id}/comparar", response_model=CalculationComparison)
def compare_versions(
    calculo_id: str,
    service: Dependency,
    versao_origem: int = Query(ge=1),
    versao_destino: int = Query(ge=1),
):
    """Compara parâmetros, parcelas e impacto no total entre duas versões."""
    comparison = service.calculation_repository.compare(calculo_id, versao_origem, versao_destino)
    if comparison is None:
        raise ServiceError("Uma das versões selecionadas não existe neste cálculo.", 404, code="CALCULATION_VERSION_NOT_FOUND")
    return comparison


@router.post("/{calculo_id}/estado", response_model=CalculationStateResult)
def change_state(calculo_id: str, payload: CalculationStateChange, request: Request, service: Dependency):
    """Arquiva, cancela ou reativa o cálculo sem excluir histórico."""
    result = service.calculation_repository.change_state(calculo_id, payload.estado, actor=technical_actor(request))
    if result is None:
        raise ServiceError("Cálculo não encontrado.", 404, code="CALCULATION_NOT_FOUND")
    return result


@router.get("/{calculo_id}/versoes/{versao}/execucoes", response_model=CalculationExecutionsPage)
def executions(
    calculo_id: str,
    versao: int,
    service: Dependency,
    pagina: int = Query(default=1, ge=1),
    tamanho_pagina: int = Query(default=20, ge=1, le=100),
):
    """Pagina execuções técnicas sem carregar indefinidamente uma versão muito reexecutada."""
    result = service.calculation_repository.executions(calculo_id, versao, page=pagina, page_size=tamanho_pagina)
    if result is None:
        raise ServiceError("Versão de cálculo não encontrada.", 404, code="CALCULATION_VERSION_NOT_FOUND")
    return result


@router.get("/{calculo_id}/versoes/{versao}", response_model=CalculationVersionDetail)
def version_detail(calculo_id: str, versao: int, service: Dependency):
    """Reabre o snapshot exato de uma versão sem executar o motor novamente."""
    detail = service.calculation_repository.version(calculo_id, versao)
    if detail is None:
        raise ServiceError("Versão de cálculo não encontrada.", 404, code="CALCULATION_VERSION_NOT_FOUND")
    return detail


@router.get("/{calculo_id}/versoes/{versao}/memoria-pdf", response_class=Response)
def version_pdf(calculo_id: str, versao: int, service: Dependency, auditavel: bool = False):
    """Baixa a memória congelada quando aquela versão de negócio foi criada."""
    content = service.calculation_repository.version_pdf(calculo_id, versao, audit=auditavel)
    if content is None:
        raise ServiceError("Memória da versão não encontrada.", 404)
    filename = f"memoria_calculo_v{versao}{'_auditavel' if auditavel else ''}.pdf"
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}", "Cache-Control": "no-store"},
    )


@router.get("/{calculo_id}/execucoes/{execucao_id}/memoria-pdf", response_class=Response)
def execution_pdf(calculo_id: str, execucao_id: str, service: Dependency, auditavel: bool = False):
    """Baixa a memória da execução atual, mesmo quando a versão foi reutilizada."""
    content = service.calculation_repository.execution_pdf(calculo_id, execucao_id, audit=auditavel)
    if content is None:
        raise ServiceError("Memória da execução não encontrada.", 404)
    filename = f"memoria_execucao_{execucao_id[-8:]}{'_auditavel' if auditavel else ''}.pdf"
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}", "Cache-Control": "no-store"},
    )


@router.post("", response_model=VersionedCalculationResponse)
def calculate(
    payload: CalculationRequest,
    request: Request,
    service: Dependency,
    calculo_id: str | None = Query(default=None),
    versao_base: int | None = Query(default=None, ge=1),
    versao_atual_esperada: int | None = Query(default=None, ge=1),
):
    """Calcula e versiona com controle otimista, inclusive a partir de versões históricas."""
    return service.calculations.execute(
        payload,
        calculation_id=calculo_id,
        base_version=versao_base,
        expected_current_version=versao_atual_esperada,
        actor=technical_actor(request),
    )


@router.post("/memoria-pdf", response_class=Response)
def memory_pdf(payload: CalculationRequest, service: Dependency, indices_sha256: str | None = None):
    """Exportação legada do request atual; não cria versão nem execução persistida."""
    content = service.calculations.execute(
        payload,
        pdf=True,
        expected_indices_hash=indices_sha256,
        persist_version=False,
    )
    return Response(content=content, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=memoria_calculo.pdf", "Cache-Control": "no-store"})
