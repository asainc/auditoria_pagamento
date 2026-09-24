"""Regressões de compatibilidade com bases SQLite persistidas por versões antigas."""
from __future__ import annotations

import json
import sqlite3

from backend.models import ParameterChangeInput
from backend.repository import Repository


def test_legacy_parameter_changes_schema_is_migrated_without_blocking_manual_audit(tmp_path):
    """Uma base antiga não pode impedir revisão/auditoria de cálculo manual."""
    db = tmp_path / "business.sqlite3"
    connection = sqlite3.connect(db)
    connection.executescript("""
        CREATE TABLE parameter_changes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            moment TEXT NOT NULL,
            process TEXT,
            field TEXT NOT NULL,
            payload TEXT NOT NULL
        );
    """)
    legacy_payload = {
        "numero_processo": "12345",
        "campo": "indice",
        "valor_anterior": None,
        "valor_novo": "sem_correcao",
    }
    connection.execute(
        "INSERT INTO parameter_changes(moment,process,field,payload) VALUES(?,?,?,?)",
        ("2026-01-01T00:00:00+00:00", "12345", "indice", json.dumps(legacy_payload)),
    )
    connection.commit()
    connection.close()

    repository = Repository(tmp_path)
    with repository.connection() as current:
        columns = {row[1] for row in current.execute("PRAGMA table_info(parameter_changes)").fetchall()}
        legacy_tables = {row[0] for row in current.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert {"draft", "process", "origin", "field", "payload"}.issubset(columns)
    assert "parameter_changes_legacy_v1" in legacy_tables

    change = ParameterChangeInput(
        origem_calculo="manual",
        numero_processo=None,
        rascunho_id="manualdraft001",
        campo="indice",
        valor_anterior=None,
        valor_novo="sem_correcao",
        extracao_id=None,
    )
    record = repository.add_parameter_change(change, actor="local")
    assert record.origem_calculo == "manual"
    assert repository.parameter_changes(draft="manualdraft001")[0].campo == "indice"
