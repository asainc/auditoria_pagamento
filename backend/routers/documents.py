"""Documentos chegam por multipart e são obtidos por identificador opaco."""
from typing import Annotated
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from backend.container import Services, services
from backend.errors import ServiceError
from backend.contracts.base import DamageType
from backend.contracts.calculation import Installment
from backend.contracts.document import DocumentMetadata, ProcessSummary
from backend.contracts.extraction import UploadResponse

router = APIRouter(prefix="/documentos", tags=["Documentos"])
Dependency = Annotated[Services, Depends(services)]


@router.post("/upload", response_model=UploadResponse, status_code=202)
async def upload(service: Dependency, files: list[UploadFile] = File(...)):
    """A extração é iniciada no servidor imediatamente após a persistência."""
    documents = await service.documents.receive(files)
    statuses = [service.extractions.start(process, new_upload=True) for process in sorted({row.numero_processo for row in documents})]
    return UploadResponse(documentos=documents, extracoes=statuses)


@router.get("/processos", response_model=list[ProcessSummary])
def processes(service: Dependency):
    """Lista processos armazenados sem selecionar automaticamente nenhum na UI."""
    return service.document_repository.processes()


@router.get("/processos/{numero_processo}", response_model=list[DocumentMetadata])
def process_documents(numero_processo: str, service: Dependency):
    """A seleção filtra no backend e evita misturar documentos de processos."""
    return service.document_repository.list_for_process(numero_processo)


@router.get("/{identificador_documento}/arquivo")
def file(identificador_documento: str, service: Dependency):
    """A autorização global da API também protege o conteúdo PDF."""
    path, document = service.documents.path(identificador_documento)
    return FileResponse(path, media_type="application/pdf", filename=document.nome, content_disposition_type="inline", headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@router.post("/parcelas/importar", response_model=list[Installment])
async def import_installments(service: Dependency, verba_tipo: DamageType, file: UploadFile = File(...)):
    """O limite também se aplica a planilhas antes de sua leitura pelo importador."""
    limit = service.documents.settings.max_upload_bytes
    content = await file.read(limit + 1)
    if len(content) > limit:
        raise ServiceError("Planilha excede o tamanho máximo.", 413)
    return service.imports.installments(content, file.filename or "", verba_tipo)
