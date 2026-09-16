"""Composição dos serviços por instância FastAPI, sem estado global de sessão."""
from __future__ import annotations

from fastapi import Request
from backend.config import Settings
from backend.repository import Repository
from backend.services.calculation import CalculationService
from backend.services.batches import BatchService
from backend.services.documents import DocumentService
from backend.services.engine import EngineFacade
from backend.services.extraction import ExtractionProvider, ExtractionService
from backend.services.imports import ImportService
from backend.services.indices import IndexService
from backend.services.revision_audit import RevisionAuditService


class Services:
    """Proprietário das conexões curtas e executores da aplicação."""
    def __init__(self, settings: Settings, provider: ExtractionProvider | None = None):
        """Cria os serviços da aplicação a partir de uma configuração validada e dependências opcionais."""
        self.repository = Repository(settings.data_dir)
        self.repository.recover_jobs()
        self.documents = DocumentService(settings, self.repository)
        self.engine = EngineFacade(settings)
        self.calculations = CalculationService(self.repository, self.engine)
        self.batches = BatchService(self.calculations)
        self.extractions = ExtractionService(settings, self.repository, self.documents, provider or ExtractionProvider(settings))
        self.indices = IndexService(settings, self.repository, self.engine)
        self.imports = ImportService()
        self.revision_audit = RevisionAuditService(self.repository)

    def close(self) -> None:
        """Finaliza os recursos pertencentes a esta instância."""
        self.extractions.close()
        self.indices.close()


def services(request: Request) -> Services:
    """Injeção explicita facilita TestClient e evita dependências entre rotas."""
    return request.app.state.services
