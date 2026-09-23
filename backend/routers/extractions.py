"""Consulta e repetição da extração não dependem de estado do navegador."""
from typing import Annotated

from fastapi import APIRouter, Depends

from backend.container import Services, services
from backend.errors import ServiceError
from backend.models import ExtractionConfiguration, ExtractionRequest, ExtractionResult, ExtractionStatus

router = APIRouter(prefix="/extracoes", tags=["Extrações"])
Dependency = Annotated[Services, Depends(services)]


@router.get("/configuracao", response_model=ExtractionConfiguration)
def configuration(service: Dependency):
    """Expõe somente disponibilidade operacional da integração corporativa."""
    provider = service.extractions.provider
    configured = provider.configured
    return ExtractionConfiguration(
        configurada=configured,
        modelo=provider.settings.bradesco_text_model,
        mensagem=(
            "Extração corporativa configurada. OCR e geração de texto serão validados na primeira execução."
            if configured
            else "Configure BRADESCO_OCR_CONTAINER e BRADESCO_TEXT_MODEL e mantenha gpt_bradesco.py funcional no backend."
        ),
        ocr_workflow=provider.settings.bradesco_ocr_workflow_configuration_code,
        tokens_disponiveis=False,
        custo_disponivel=False,
    )


@router.post("", response_model=ExtractionStatus, status_code=202)
def start(payload: ExtractionRequest, service: Dependency):
    """Retentativa manual é útil após configurar o provedor ou reiniciar o serviço."""
    return service.extractions.start(payload.numero_processo)


@router.get("/{numero_processo}/status", response_model=ExtractionStatus)
def status(numero_processo: str, service: Dependency):
    """Ausência de trabalho é 404; falha do provedor é estado explícito."""
    result = service.repository.status(numero_processo)
    if result is None:
        raise ServiceError("Nenhuma extração registrada para o processo.", 404)
    return result


@router.get("/{numero_processo}/resultado", response_model=ExtractionResult)
def result(numero_processo: str, service: Dependency):
    """Somente extração consolidada é devolvida para revisão humana."""
    result = service.repository.result(numero_processo)
    if result is None:
        raise ServiceError("A extração ainda não possui resultado revisável.", 409)
    return result
