"""Endpoints de auditoria da revisão humana de parâmetros."""
from __future__ import annotations

import hashlib
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from backend.container import Services, services
from backend.models import ParameterChangeInput, ParameterChangeRecord

router = APIRouter(prefix="/auditoria", tags=["Auditoria"])
Dependency = Annotated[Services, Depends(services)]


def _technical_actor(request: Request) -> str:
    """Deriva identificador técnico sem persistir identidade pessoal em claro."""
    settings = request.app.state.settings
    if settings.environment == "local":
        return "local"
    subject = request.headers.get("X-Authenticated-Subject", "")
    if not subject:
        return "gateway"
    return "usr_" + hashlib.sha256(subject.encode("utf-8")).hexdigest()[:16]


@router.post("/parametros", response_model=ParameterChangeRecord)
def record_parameter_change(payload: ParameterChangeInput, request: Request, service: Dependency):
    """Registra uma alteração de parâmetro como evento imutável."""
    return service.revision_audit.record(payload, _technical_actor(request))


@router.get("/parametros", response_model=list[ParameterChangeRecord])
def list_parameter_changes(
    service: Dependency,
    numero_processo: str | None = Query(default=None),
    rascunho_id: str | None = Query(default=None),
):
    """Consulta por processo real ou por rascunho manual; exige exatamente um filtro."""
    if bool(numero_processo) == bool(rascunho_id):
        from backend.errors import ServiceError
        raise ServiceError("Informe numero_processo ou rascunho_id, mas não ambos.", 422)
    if numero_processo:
        return service.revision_audit.list_for_process(numero_processo)
    return service.revision_audit.list_for_draft(rascunho_id or "")
