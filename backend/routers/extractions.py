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
    """Permite orientar a operação sem expor ou testar a credencial da OpenAI."""
    provider = service.extractions.provider
    pricing = provider.usage_meter.catalog
    return ExtractionConfiguration(
        configurada=provider.configured,
        modelo=provider.settings.openai_model,
        mensagem=("Extração automática configurada. O acesso à OpenAI será verificado ao extrair."
                  if provider.configured else "Configure API_TOKEN no .env do backend e reinicie a aplicação para habilitar a extração automática."),
        moeda_custo=pricing.currency,
        precos_verificados_em=pricing.verified_at,
        fonte_precos=pricing.source,
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
