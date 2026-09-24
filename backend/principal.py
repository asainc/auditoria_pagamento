"""Única inicialização FastAPI; não hospeda o frontend da aplicação."""
from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.access import require_access
from backend.config import Settings, load_settings
from backend.container import Services
from backend.errors import ServiceError
from backend.models import Contract
from backend.routers import audit, batches, calculations, documents, extractions, indices
from backend.services.extraction import ExtractionProvider


class Health(Contract):
    """Identifica disponibilidade da API e sua versão de contrato."""
    status: str = "ok"
    versao_api: str = "2.0.0"


class AuditFormatter(logging.Formatter):
    """Logs estruturados contêm apenas metadados técnicos selecionados."""
    def format(self, record: logging.LogRecord) -> str:
        """Seleciona metadados de auditoria sem serializar conteúdo de requisições."""
        payload = {"level": record.levelname, "event": record.getMessage()}
        for key in ("request_id", "status_code", "duration_ms", "error_type", "job_id", "stage", "error_code", "attempt", "pages", "characters", "accepted", "rejected"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, ensure_ascii=False)


def create_app(settings: Settings | None = None, provider: ExtractionProvider | None = None) -> FastAPI:
    """Cria uma instância FastAPI com configuração e dependências explicitamente injetáveis."""
    configuration = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Cria e encerra os serviços pertencentes somente a esta instância."""
        app.state.services = Services(configuration, provider)
        try:
            yield
        finally:
            app.state.services.close()

    app = FastAPI(title="Calculadora de Débitos Judiciais", version="2.0.0", lifespan=lifespan)
    app.state.settings = configuration
    logger = logging.getLogger("judicial")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(AuditFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    app.add_middleware(CORSMiddleware, allow_origins=configuration.cors_origins, allow_credentials=False, allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type", "X-Request-ID"])

    @app.middleware("http")
    async def audit_request(request: Request, call_next):
        """Não registra caminho, processo, payload, cabeçalhos ou dados pessoais."""
        identifier = uuid4().hex
        started = perf_counter()
        try:
            response = await call_next(request)
        except Exception as error:
            logger.error("request_failed", extra={"request_id": identifier, "error_type": type(error).__name__})
            response = JSONResponse(status_code=500, content={"detail": "Falha interna. Informe o identificador da requisição ao suporte."})
        response.headers["X-Request-ID"] = identifier
        response.headers["X-API-Version"] = "1"
        response.headers["Cache-Control"] = "no-store"
        logger.info("request_completed", extra={"request_id": identifier, "status_code": response.status_code, "duration_ms": round((perf_counter() - started) * 1000, 2)})
        return response

    @app.exception_handler(ServiceError)
    async def service_error(request: Request, error: ServiceError):
        """Devolve somente a mensagem de domínio previamente sanitizada."""
        return JSONResponse(status_code=error.status_code, content={"detail": error.message})

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError):
        # A resposta de validação expõe somente localização, mensagem e tipo do erro; o valor recebido não é devolvido.
        """Explica os campos inválidos sem ecoar os valores recebidos."""
        details = [{"campo": ".".join(str(item) for item in problem["loc"]), "tipo": problem["type"], "mensagem": problem["msg"]} for problem in error.errors()]
        return JSONResponse(status_code=422, content={"detail": "Revise os campos informados.", "campos": details})

    api = APIRouter(dependencies=[Depends(require_access)])

    @api.get("/saude", response_model=Health, tags=["Saúde"])
    def health():
        """Informa disponibilidade sem revelar configuração interna."""
        return Health()

    for router in (documents.router, extractions.router, calculations.router, indices.router, batches.router, audit.router):
        api.include_router(router)
    app.include_router(api, prefix="/api")
    app.include_router(api, prefix="/api/v1", include_in_schema=False)
    return app


aplicacao = create_app()
