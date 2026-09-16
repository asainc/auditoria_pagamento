"""Lotes reutilizam o mesmo serviço de cálculo e a confirmação humana."""
from typing import Annotated
from fastapi import APIRouter, Depends, File, UploadFile
from backend.container import Services, services
from backend.errors import ServiceError
from backend.models import BatchImport, BatchRequest, BatchResponse

router = APIRouter(prefix="/lotes", tags=["Lotes"])
Dependency = Annotated[Services, Depends(services)]


@router.post("/importar", response_model=BatchImport)
async def import_batch(service: Dependency, file: UploadFile = File(...)):
    """Importar apenas prepara a prévia; não executa nem confirma o lote."""
    limit = service.documents.settings.max_upload_bytes
    content = await file.read(limit + 1)
    if len(content) > limit:
        raise ServiceError("Arquivo excede o tamanho máximo.", 413)
    return service.imports.batch(content, file.filename or "")


@router.post("/executar", response_model=BatchResponse)
def run(payload: BatchRequest, service: Dependency):
    """Falhas são explícitas por processo; sucessos não são descartados."""
    return service.batches.execute(payload)
