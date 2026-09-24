"""Cálculo e exportações compartilham o mesmo contrato validado."""
from typing import Annotated
from fastapi import APIRouter, Depends, Response
from backend.container import Services, services
from backend.models import CalculationDefaults, CalculationPolicyView, CalculationRequest, CalculationResponse, FeePreparation, Installment, ParameterCatalogItem
from backend.services.operational_policy import current_competence, fee_installments
from backend.calculation_policy import CalculationOrigin, defaults_for_origin, parameter_catalog, required_parameter_keys

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


@router.post("", response_model=CalculationResponse)
def calculate(payload: CalculationRequest, service: Dependency):
    """Calcula somente após a confirmação humana enviada no contrato."""
    return service.calculations.execute(payload)


@router.post("/memoria-pdf", response_class=Response)
def memory_pdf(payload: CalculationRequest, service: Dependency, auditavel: bool = False, indices_sha256: str | None = None):
    """Retorna bytes do PDF, sem template de interface nem arquivo temporário remanescente."""
    content = service.calculations.execute(payload, pdf=True, audit=auditavel, expected_indices_hash=indices_sha256)
    return Response(content=content, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=memoria_calculo.pdf", "Cache-Control": "no-store"})
