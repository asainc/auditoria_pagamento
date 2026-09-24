"""Persistência exclusiva de documentos e processos."""
from __future__ import annotations

from backend.calculation_identity import display_process_number, normalize_process_number
from backend.contracts.document import DocumentMetadata, ProcessSummary
from backend.persistence.sqlite import SQLiteDatabase


def _process_sort_key(value: str) -> tuple[int, str, str]:
    normalized = "".join(character for character in value if character.isalnum())
    return len(normalized), normalized, value


class DocumentRepository:
    """CRUD documental sem conhecer extração, cálculo ou auditoria."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def add(self, document: DocumentMetadata) -> DocumentMetadata:
        with self.database.connection() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO documents(id,process,hash,payload) VALUES(?,?,?,?)",
                (document.identificador, document.numero_processo, document.sha256, document.model_dump_json()),
            )
            row = connection.execute(
                "SELECT payload FROM documents WHERE process=? AND hash=?",
                (document.numero_processo, document.sha256),
            ).fetchone()
        return DocumentMetadata.model_validate_json(row["payload"])

    def list_for_process(self, process: str) -> list[DocumentMetadata]:
        normalized = normalize_process_number(process)
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT payload FROM documents WHERE REPLACE(REPLACE(process,'.',''),'-','')=? ORDER BY rowid",
                (normalized,),
            ).fetchall()
        return [DocumentMetadata.model_validate_json(row["payload"]) for row in rows]

    def get(self, identifier: str) -> DocumentMetadata | None:
        with self.database.connection() as connection:
            row = connection.execute("SELECT payload FROM documents WHERE id=?", (identifier,)).fetchone()
        return DocumentMetadata.model_validate_json(row["payload"]) if row else None

    def classify(self, identifier: str, classification: str) -> None:
        document = self.get(identifier)
        if document is None:
            return
        document.classificacao = classification
        with self.database.connection() as connection:
            connection.execute("UPDATE documents SET payload=? WHERE id=?", (document.model_dump_json(), identifier))

    def processes(self) -> list[ProcessSummary]:
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT REPLACE(REPLACE(process,'.',''),'-','') AS normalized, COUNT(*) AS count FROM documents GROUP BY normalized"
            ).fetchall()
        summaries = [
            ProcessSummary(numero_processo=display_process_number(str(row["normalized"])), quantidade_documentos=int(row["count"]))
            for row in rows
        ]
        return sorted(summaries, key=lambda item: _process_sort_key(item.numero_processo))
