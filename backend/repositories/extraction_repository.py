"""Persistência exclusiva do fluxo e fila de extração."""
from __future__ import annotations

import sqlite3
import time

from backend.contracts.extraction import ExtractionResult, ExtractionStatus
from backend.persistence.schema import timestamp
from backend.persistence.sqlite import SQLiteDatabase
from backend.repositories.document_repository import DocumentRepository


class ExtractionRepository:
    """Estado da extração e lease da fila durável."""

    def __init__(self, database: SQLiteDatabase, documents: DocumentRepository) -> None:
        self.database = database
        self.documents_repository = documents

    def start_job(self, status: ExtractionStatus, *, max_attempts: int = 3) -> None:
        now = time.time()
        with self.database.connection() as connection:
            connection.execute(
                "INSERT INTO extractions(process,job,payload,result) VALUES(?,?,?,NULL) "
                "ON CONFLICT(process) DO UPDATE SET job=excluded.job,payload=excluded.payload,result=NULL",
                (status.numero_processo, status.identificador, status.model_dump_json()),
            )
            connection.execute(
                "UPDATE extraction_queue SET state='cancelled' WHERE process=? AND state IN ('queued','leased') AND job<>?",
                (status.numero_processo, status.identificador),
            )
            connection.execute(
                "INSERT INTO extraction_queue(job,process,state,attempts,max_attempts,available_at,lease_until,created_at) "
                "VALUES(?,?, 'queued',0,?,?,NULL,?) "
                "ON CONFLICT(job) DO UPDATE SET state='queued',available_at=excluded.available_at,lease_until=NULL",
                (status.identificador, status.numero_processo, max_attempts, now, now),
            )

    def claim_job(self, lease_seconds: int) -> tuple[str, str, int, int] | None:
        now = time.time()
        with self.database.immediate() as connection:
            connection.execute(
                "UPDATE extraction_queue SET state='queued',lease_until=NULL WHERE state='leased' AND lease_until IS NOT NULL AND lease_until<?",
                (now,),
            )
            row = connection.execute(
                "SELECT job,process,attempts,max_attempts FROM extraction_queue WHERE state='queued' AND available_at<=? ORDER BY created_at LIMIT 1",
                (now,),
            ).fetchone()
            if row is None:
                return None
            attempt = int(row["attempts"]) + 1
            connection.execute(
                "UPDATE extraction_queue SET state='leased',attempts=?,lease_until=? WHERE job=?",
                (attempt, now + lease_seconds, row["job"]),
            )
            return str(row["job"]), str(row["process"]), attempt, int(row["max_attempts"])

    def retry_job(self, job: str, delay_seconds: float) -> None:
        with self.database.connection() as connection:
            connection.execute(
                "UPDATE extraction_queue SET state='queued',available_at=?,lease_until=NULL WHERE job=?",
                (time.time() + max(0.0, delay_seconds), job),
            )

    def finish_job(self, job: str, *, success: bool) -> None:
        with self.database.connection() as connection:
            connection.execute(
                "UPDATE extraction_queue SET state=?,lease_until=NULL WHERE job=?",
                ("done" if success else "failed", job),
            )

    def update_job(self, status: ExtractionStatus, result: ExtractionResult | None = None) -> None:
        with self.database.connection() as connection:
            connection.execute(
                "UPDATE extractions SET payload=?,result=? WHERE process=? AND job=?",
                (status.model_dump_json(), result.model_dump_json() if result else None, status.numero_processo, status.identificador),
            )

    def status(self, process: str) -> ExtractionStatus | None:
        with self.database.connection() as connection:
            row = connection.execute("SELECT payload FROM extractions WHERE process=?", (process,)).fetchone()
        return ExtractionStatus.model_validate_json(row["payload"]) if row else None

    def result(self, process: str) -> ExtractionResult | None:
        with self.database.connection() as connection:
            row = connection.execute("SELECT result FROM extractions WHERE process=?", (process,)).fetchone()
        return ExtractionResult.model_validate_json(row["result"]) if row and row["result"] else None

    def recover_jobs(self) -> None:
        now = time.time()
        with self.database.connection() as connection:
            connection.execute(
                "UPDATE extraction_queue SET state='queued',available_at=?,lease_until=NULL WHERE state IN ('queued','leased')",
                (now,),
            )
        for process in self.documents_repository.processes():
            status = self.status(process.numero_processo)
            if status and status.estado in {"aguardando", "executando", "interrompida"}:
                status.estado = "aguardando"
                status.etapa = "Recuperando trabalho"
                status.mensagem = "Extração recuperada após reinício e devolvida à fila durável."
                status.atualizado_em = timestamp()
                self.update_job(status)
