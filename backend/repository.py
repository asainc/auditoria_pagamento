"""Fachada de compatibilidade sobre repositórios especializados.

O código novo deve injetar o repositório do domínio necessário. Esta fachada
permanece para integrações antigas e testes que ainda importam ``Repository``.
"""
from __future__ import annotations

from pathlib import Path

from backend.persistence.schema import migrate, timestamp
from backend.persistence.sqlite import SQLiteDatabase
from backend.repositories.audit_repository import AuditRepository
from backend.repositories.calculation_repository import CalculationRepository
from backend.repositories.document_repository import DocumentRepository
from backend.repositories.extraction_repository import ExtractionRepository
from backend.repositories.index_repository import IndexRepository


class Repository:
    """Composição retrocompatível; não contém SQL nem regra de persistência."""

    def __init__(self, data_dir: Path):
        self.database = SQLiteDatabase(data_dir)
        migrate(self.database)
        self.document_store = DocumentRepository(self.database)
        self.extraction_store = ExtractionRepository(self.database, self.document_store)
        self.audit_store = AuditRepository(self.database)
        self.calculation_store = CalculationRepository(self.database)
        self.index_store = IndexRepository(self.database)
        self.data_dir = data_dir
        self.path = self.database.path

    def connection(self):
        return self.database.connection()

    # Documentos
    def add_document(self, document): return self.document_store.add(document)
    def documents(self, process): return self.document_store.list_for_process(process)
    def document(self, identifier): return self.document_store.get(identifier)
    def classify_document(self, identifier, classification): return self.document_store.classify(identifier, classification)
    def processes(self): return self.document_store.processes()

    # Extração
    def start_job(self, status, *, max_attempts=3): return self.extraction_store.start_job(status, max_attempts=max_attempts)
    def claim_extraction_job(self, lease_seconds): return self.extraction_store.claim_job(lease_seconds)
    def retry_extraction_job(self, job, delay_seconds): return self.extraction_store.retry_job(job, delay_seconds)
    def finish_extraction_job(self, job, *, success): return self.extraction_store.finish_job(job, success=success)
    def update_job(self, status, result=None): return self.extraction_store.update_job(status, result)
    def status(self, process): return self.extraction_store.status(process)
    def result(self, process): return self.extraction_store.result(process)
    def recover_jobs(self): return self.extraction_store.recover_jobs()

    # Auditoria
    def add_parameter_change(self, change, *, actor, extracted_value=None, extracted_source=None):
        return self.audit_store.add_parameter_change(change, actor=actor, extracted_value=extracted_value, extracted_source=extracted_source)
    def parameter_changes(self, *, process=None, draft=None): return self.audit_store.parameter_changes(process=process, draft=draft)
    def audit(self, event, payload): return self.audit_store.append(event, payload)

    # Cálculos
    def append_calculation_version(self, **kwargs): return self.calculation_store.append_version(**kwargs)
    def calculation_history(self, **kwargs): return self.calculation_store.history(**kwargs)
    def calculation_versions(self, calculation_id, *, page=1, page_size=50): return self.calculation_store.versions(calculation_id, page=page, page_size=page_size)
    def calculation_version(self, calculation_id, version): return self.calculation_store.version(calculation_id, version)
    def calculation_comparison(self, calculation_id, version_from, version_to): return self.calculation_store.compare(calculation_id, version_from, version_to)
    def change_calculation_state(self, calculation_id, state, *, actor): return self.calculation_store.change_state(calculation_id, state, actor=actor)
    def calculation_executions(self, calculation_id, version, *, page=1, page_size=20): return self.calculation_store.executions(calculation_id, version, page=page, page_size=page_size)
    def calculation_pdf(self, calculation_id, version, *, audit): return self.calculation_store.version_pdf(calculation_id, version, audit=audit)
    def execution_pdf(self, calculation_id, execution_id, *, audit): return self.calculation_store.execution_pdf(calculation_id, execution_id, audit=audit)
