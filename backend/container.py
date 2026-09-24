"""Composição explícita dos serviços e repositórios por domínio."""
from __future__ import annotations

from fastapi import Request

from backend.config import Settings
from backend.persistence.schema import migrate
from backend.persistence.sqlite import SQLiteDatabase
from backend.repositories.audit_repository import AuditRepository
from backend.repositories.calculation_repository import CalculationRepository
from backend.repositories.document_repository import DocumentRepository
from backend.repositories.extraction_repository import ExtractionRepository
from backend.repositories.index_repository import IndexRepository
from backend.services.batches import BatchService
from backend.services.calculation import CalculationService
from backend.services.documents import DocumentService
from backend.services.engine import EngineFacade
from backend.services.extraction import ExtractionProvider, ExtractionService
from backend.services.imports import ImportService
from backend.services.indices import IndexService
from backend.services.revision_audit import RevisionAuditService


class Services:
    """Composition root: cada serviço recebe somente persistência do seu domínio."""

    def __init__(self, settings: Settings, provider: ExtractionProvider | None = None):
        self.database = SQLiteDatabase(settings.data_dir)
        migrate(self.database)
        self.document_repository = DocumentRepository(self.database)
        self.extraction_repository = ExtractionRepository(self.database, self.document_repository)
        self.audit_repository = AuditRepository(self.database)
        self.calculation_repository = CalculationRepository(self.database)
        self.index_repository = IndexRepository(self.database)
        # Alias temporário apenas para clientes legados de extração; código novo usa repositórios nomeados.
        self.repository = self.extraction_repository

        self.extraction_repository.recover_jobs()
        self.documents = DocumentService(settings, self.document_repository, self.audit_repository)
        self.engine = EngineFacade(settings)
        self.calculations = CalculationService(self.calculation_repository, self.audit_repository, self.engine)
        self.batches = BatchService(self.calculations)
        self.extractions = ExtractionService(
            settings,
            self.extraction_repository,
            self.document_repository,
            self.audit_repository,
            self.documents,
            provider or ExtractionProvider(settings),
        )
        self.indices = IndexService(settings, self.index_repository, self.audit_repository, self.engine)
        self.imports = ImportService()
        self.revision_audit = RevisionAuditService(self.audit_repository, self.extraction_repository)

    def close(self) -> None:
        self.extractions.close()
        self.indices.close()


def services(request: Request) -> Services:
    return request.app.state.services
