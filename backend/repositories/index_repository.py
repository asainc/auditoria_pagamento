"""Persistência mínima do estado do atualizador de índices."""
from __future__ import annotations

from backend.contracts.index import IndexStatus
from backend.persistence.sqlite import SQLiteDatabase


class IndexRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def status(self) -> IndexStatus | None:
        with self.database.connection() as connection:
            row = connection.execute("SELECT payload FROM index_state WHERE id=1").fetchone()
        return IndexStatus.model_validate_json(row["payload"]) if row else None

    def save(self, status: IndexStatus) -> None:
        with self.database.connection() as connection:
            connection.execute("INSERT OR REPLACE INTO index_state(id,payload) VALUES(1,?)", (status.model_dump_json(),))

    def start_if_idle(self, status: IndexStatus) -> IndexStatus:
        with self.database.immediate() as connection:
            row = connection.execute("SELECT payload FROM index_state WHERE id=1").fetchone()
            if row:
                current = IndexStatus.model_validate_json(row["payload"])
                if current.estado == "executando":
                    return current
            connection.execute("INSERT OR REPLACE INTO index_state(id,payload) VALUES(1,?)", (status.model_dump_json(),))
        return status
