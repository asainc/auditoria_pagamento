"""Publicação protegida por gateway autenticado; local usa apenas loopback."""
import hashlib
import secrets
from fastapi import Request
from backend.errors import ServiceError


def require_access(request: Request) -> None:
    """Cabeçalho é inserido pelo gateway, nunca enviado ao navegador como segredo."""
    settings = request.app.state.settings
    if settings.environment == "local":
        return
    supplied = request.headers.get("X-Gateway-Token", "")
    if not secrets.compare_digest(supplied, settings.gateway_token.get_secret_value()):
        raise ServiceError("Acesso permitido somente pelo gateway autenticado.", 403)


def technical_actor(request: Request) -> str:
    """Deriva identificador técnico estável sem persistir a identidade pessoal em claro."""
    settings = request.app.state.settings
    if settings.environment == "local":
        return "local"
    subject = request.headers.get("X-Authenticated-Subject", "")
    if not subject:
        return "gateway"
    return "usr_" + hashlib.sha256(subject.encode("utf-8")).hexdigest()[:16]
