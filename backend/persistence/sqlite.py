"""Infraestrutura SQLite compartilhada pelos repositórios especializados."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class SQLiteDatabase:
    """Cria conexões curtas; nenhuma conexão é compartilhada entre threads."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        data_dir.mkdir(parents=True, exist_ok=True)
        self.path = data_dir / "business.sqlite3"

    def connect(self, *, isolation_level: str | None = "DEFERRED", foreign_keys: bool = True) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30, isolation_level=isolation_level)
        connection.row_factory = sqlite3.Row
        connection.execute(f"PRAGMA foreign_keys={'ON' if foreign_keys else 'OFF'}")
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Commit ou rollback integral da operação corrente."""
        connection = self.connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @contextmanager
    def immediate(self) -> Iterator[sqlite3.Connection]:
        """Serializa decisões concorrentes que dependem do estado mais recente."""
        connection = self.connect(isolation_level=None)
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.execute("COMMIT")
        except Exception:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.OperationalError:
                pass
            raise
        finally:
            connection.close()
