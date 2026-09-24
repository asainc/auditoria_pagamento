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


def test_legacy_calculation_records_gain_origin_and_identifier_without_losing_process(tmp_path):
    """Cadastros por processo criados antes do cálculo manual continuam legíveis."""
    db = tmp_path / "business.sqlite3"
    connection = sqlite3.connect(db)
    connection.executescript("""
        CREATE TABLE calculation_records(
            id TEXT PRIMARY KEY,
            process TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        INSERT INTO calculation_records(id,process,created_at,created_by,updated_at)
        VALUES('calc_0123456789abcdef0123456789abcdef','1001','2026-01-01','legacy','2026-01-01');
    """)
    connection.commit()
    connection.close()

    repository = Repository(tmp_path)
    with repository.connection() as current:
        row = current.execute(
            "SELECT process,origin,identifier FROM calculation_records WHERE id=?",
            ("calc_0123456789abcdef0123456789abcdef",),
        ).fetchone()

    assert row[0] == "1001"
    assert row[1] == "processo"
    assert row[2] == "1001"


def test_legacy_calculation_schema_gains_normalized_identity_state_hash_diff_and_execution(tmp_path):
    """A migração avançada é aditiva e não recalcula uma versão histórica."""
    db = tmp_path / "business.sqlite3"
    connection = sqlite3.connect(db)
    connection.executescript("""
        PRAGMA foreign_keys=ON;
        CREATE TABLE calculation_records(
            id TEXT PRIMARY KEY,
            process TEXT NOT NULL UNIQUE,
            origin TEXT NOT NULL DEFAULT 'processo',
            identifier TEXT,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE calculation_versions(
            calculation_id TEXT NOT NULL,
            version INTEGER NOT NULL,
            base_version INTEGER,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            request TEXT NOT NULL,
            response TEXT NOT NULL,
            pdf BLOB NOT NULL,
            audit_pdf BLOB NOT NULL,
            total TEXT,
            index_name TEXT NOT NULL,
            update_competence TEXT NOT NULL,
            input_hash TEXT NOT NULL,
            policy_hash TEXT NOT NULL,
            engine_hash TEXT NOT NULL,
            indices_hash TEXT NOT NULL,
            changed_fields TEXT NOT NULL,
            PRIMARY KEY(calculation_id, version),
            FOREIGN KEY(calculation_id) REFERENCES calculation_records(id) ON DELETE RESTRICT
        );
    """)
    calculation_id = "calc_0123456789abcdef0123456789abcdef"
    request = {
        "origem_calculo": "processo",
        "numero_processo": "1234567-89.2026.8.26.0001",
        "identificador_calculo": "1234567-89.2026.8.26.0001",
        "parametros": {"indice": "sem_correcao"},
        "parcelas": [],
        "honorarios_sobre_danos_morais": False,
    }
    response = {"metadata": {"duracao_ms": 12.5}}
    connection.execute(
        "INSERT INTO calculation_records(id,process,origin,identifier,created_at,created_by,updated_at) VALUES(?,?,?,?,?,?,?)",
        (calculation_id, "1234567-89.2026.8.26.0001", "processo", "1234567-89.2026.8.26.0001", "2026-01-01", "legacy", "2026-01-01"),
    )
    connection.execute(
        """
        INSERT INTO calculation_versions(
            calculation_id,version,base_version,created_at,created_by,request,response,pdf,audit_pdf,
            total,index_name,update_competence,input_hash,policy_hash,engine_hash,indices_hash,changed_fields
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            calculation_id, 1, None, "2026-01-01", "legacy", json.dumps(request), json.dumps(response),
            sqlite3.Binary(b"%PDF-legacy"), sqlite3.Binary(b"%PDF-audit"), "100.00", "sem_correcao", "janeiro/2026",
            "a" * 64, "b" * 64, "c" * 64, "d" * 64, "[]",
        ),
    )
    connection.commit()
    connection.close()

    repository = Repository(tmp_path)
    with repository.connection() as current:
        record = current.execute(
            "SELECT normalized_identifier,state FROM calculation_records WHERE id=?", (calculation_id,)
        ).fetchone()
        version = current.execute(
            "SELECT business_hash,diff_json FROM calculation_versions WHERE calculation_id=? AND version=1", (calculation_id,)
        ).fetchone()
        executions = current.execute(
            "SELECT COUNT(*) FROM calculation_executions WHERE calculation_id=? AND version=1", (calculation_id,)
        ).fetchone()[0]

    assert record["normalized_identifier"] == "12345678920268260001"
    assert record["state"] == "ativo"
    assert len(version["business_hash"]) == 64
    assert json.loads(version["diff_json"]) == {"campos": [], "parcelas": []}
    assert executions == 1
