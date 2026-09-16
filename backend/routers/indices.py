"""Catálogo e atualização de índices passam exclusivamente pela API."""
from typing import Annotated
from fastapi import APIRouter, Depends
from backend.container import Services, services
from backend.models import IndexOption, IndexStatus

router = APIRouter(prefix="/indices", tags=["Índices"])
Dependency = Annotated[Services, Depends(services)]


@router.get("", response_model=list[IndexOption])
def options(service: Dependency):
    """Devolve somente chaves registradas no motor."""
    return service.indices.options()


@router.get("/status", response_model=IndexStatus)
def status(service: Dependency):
    """Informa estado real, sem afirmar atualização não verificada."""
    return service.indices.status()


@router.post("/atualizar", response_model=IndexStatus, status_code=202)
def update(service: Dependency):
    """Atualização segue assíncrona e pode ser acompanhada por polling."""
    return service.indices.start()
