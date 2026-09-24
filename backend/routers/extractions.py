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
    """Expõe somente disponibilidade operacional da leitura local + geração corporativa."""
    provider = service.extractions.provider
    configured = provider.configured
    return ExtractionConfiguration(
        configurada=configured,
        modelo=provider.settings.bradesco_text_model,
        mensagem=(
            "Extração automática configurada: PDFs são lidos localmente com PyMuPDF e os prompts usam text_generator."
            if configured
            else "Configure BRADESCO_TEXT_MODEL e mantenha gpt_bradesco.py com text_generator funcional no backend."
        ),
        # Campo mantido no contrato da API para compatibilidade com o frontend atual.
        leitura_documental="pymupdf_local_text",
        tokens_disponiveis=False,
        custo_disponivel=False,
    )


@router.post("", response_model=ExtractionStatus, status_code=202)
def start(payload: ExtractionRequest, service: Dependency):
    """Retentativa manual é útil após configurar o deployment ou reiniciar o serviço."""
    return service.extractions.start(payload.numero_processo)


@router.get("/{numero_processo}/status", response_model=ExtractionStatus)
def status(numero_processo: str, service: Dependency):
    """Ausência de trabalho é 404; falha do provedor é estado explícito."""
    result = service.extraction_repository.status(numero_processo)
    if result is None:
        raise ServiceError("Nenhuma extração registrada para o processo.", 404)
    return result


@router.get("/{numero_processo}/resultado", response_model=ExtractionResult)
def result(numero_processo: str, service: Dependency):
    """Somente extração consolidada é devolvida para revisão humana."""
    result = service.extraction_repository.result(numero_processo)
    if result is None:
        raise ServiceError("A extração ainda não possui resultado revisável.", 409)
    return result
