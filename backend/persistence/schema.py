"""Schema e migrações idempotentes do banco de negócio."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from backend.calculation_identity import normalize_manual_identifier, normalize_process_number
from backend.contracts.calculation import CalculationDiff, CalculationFieldDiff, Installment, InstallmentDiff
from backend.persistence.sqlite import SQLiteDatabase

SCHEMA_VERSION = 6


def timestamp() -> str:
    """UTC torna eventos comparáveis entre instalações."""
    return datetime.now(timezone.utc).isoformat()


def _business_state(payload: dict) -> dict:
    return {
        "parametros": payload.get("parametros") or {},
        "parcelas": payload.get("parcelas") or [],
        "honorarios_sobre_danos_morais": bool(payload.get("honorarios_sobre_danos_morais", False)),
    }


def business_hash(payload: dict) -> str:
    """Hash canônico exclusivo do estado funcional do cálculo."""
    canonical = json.dumps(_business_state(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def full_diff(previous: dict | None, current: dict) -> CalculationDiff:
    """Diff completo entre parâmetros e parcelas de duas versões."""
    if previous is None:
        return CalculationDiff()
    fields: list[CalculationFieldDiff] = []
    previous_parameters = previous.get("parametros") if isinstance(previous.get("parametros"), dict) else {}
    current_parameters = current.get("parametros") if isinstance(current.get("parametros"), dict) else {}
    for key in sorted(set(previous_parameters) | set(current_parameters)):
        before = previous_parameters.get(key)
        after = current_parameters.get(key)
        if before != after:
            fields.append(CalculationFieldDiff(caminho=f"parametros.{key}", valor_anterior=before, valor_novo=after))
    before_fee = bool(previous.get("honorarios_sobre_danos_morais", False))
    after_fee = bool(current.get("honorarios_sobre_danos_morais", False))
    if before_fee != after_fee:
        fields.append(CalculationFieldDiff(caminho="honorarios_sobre_danos_morais", valor_anterior=before_fee, valor_novo=after_fee))

    installments: list[InstallmentDiff] = []
    before_rows = previous.get("parcelas") if isinstance(previous.get("parcelas"), list) else []
    after_rows = current.get("parcelas") if isinstance(current.get("parcelas"), list) else []
    for index in range(max(len(before_rows), len(after_rows))):
        before = before_rows[index] if index < len(before_rows) else None
        after = after_rows[index] if index < len(after_rows) else None
        if before == after:
            continue
        if before is None:
            installments.append(InstallmentDiff(posicao=index + 1, acao="adicionada", depois=Installment.model_validate(after)))
            continue
        if after is None:
            installments.append(InstallmentDiff(posicao=index + 1, acao="removida", antes=Installment.model_validate(before)))
            continue
        changed_fields = [key for key in sorted(set(before) | set(after)) if before.get(key) != after.get(key)]
        installments.append(InstallmentDiff(posicao=index + 1, acao="alterada", campos_alterados=changed_fields, antes=Installment.model_validate(before), depois=Installment.model_validate(after)))
    return CalculationDiff(campos=fields, parcelas=installments)


def _changed_fields(diff: CalculationDiff) -> list[str]:
    changed = [item.caminho for item in diff.campos]
    if diff.parcelas:
        changed.append("parcelas")
    return changed


def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
    return connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    if not _table_exists(connection, table):
        return set()
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}


def _base_schema(connection: sqlite3.Connection) -> None:
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS schema_migrations(
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS documents(
            id TEXT PRIMARY KEY,
            process TEXT NOT NULL,
            hash TEXT NOT NULL,
            payload TEXT NOT NULL,
            UNIQUE(process, hash)
        );
        CREATE TABLE IF NOT EXISTS extractions(
            process TEXT PRIMARY KEY,
            job TEXT NOT NULL,
            payload TEXT NOT NULL,
            result TEXT
        );
        CREATE TABLE IF NOT EXISTS extraction_queue(
            job TEXT PRIMARY KEY,
            process TEXT NOT NULL,
            state TEXT NOT NULL CHECK(state IN ('queued','leased','done','failed','cancelled')),
            attempts INTEGER NOT NULL DEFAULT 0 CHECK(attempts >= 0),
            max_attempts INTEGER NOT NULL DEFAULT 3 CHECK(max_attempts >= 1),
            available_at REAL NOT NULL,
            lease_until REAL,
            created_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit(
            id INTEGER PRIMARY KEY,
            moment TEXT NOT NULL,
            event TEXT NOT NULL,
            payload TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS index_state(
            id INTEGER PRIMARY KEY CHECK(id=1),
            payload TEXT NOT NULL
        );
    """)


def _parameter_changes_ddl(table: str = "parameter_changes") -> str:
    return f"""
        CREATE TABLE {table}(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            moment TEXT NOT NULL,
            draft TEXT NOT NULL,
            process TEXT,
            origin TEXT NOT NULL CHECK(origin IN ('manual','processo')),
            field TEXT NOT NULL,
            payload TEXT NOT NULL
        )
    """


def _ensure_parameter_changes(connection: sqlite3.Connection) -> None:
    if not _table_exists(connection, "parameter_changes"):
        connection.execute(_parameter_changes_ddl())
        return
    columns = _columns(connection, "parameter_changes")
    expected = {"id", "moment", "draft", "process", "origin", "field", "payload"}
    if expected.issubset(columns):
        return
    suffix = 1
    legacy = "parameter_changes_legacy_v1"
    while _table_exists(connection, legacy):
        suffix += 1
        legacy = f"parameter_changes_legacy_v{suffix}"
    connection.execute(f'ALTER TABLE parameter_changes RENAME TO "{legacy}"')
    connection.execute(_parameter_changes_ddl())
    for row in connection.execute(f'SELECT * FROM "{legacy}"').fetchall():
        raw = dict(row)
        try:
            payload = json.loads(raw.get("payload") or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        field = str(raw.get("field") or payload.get("campo") or "").strip()
        if not field:
            continue
        process = raw.get("process") or payload.get("numero_processo")
        origin = str(raw.get("origin") or payload.get("origem_calculo") or ("processo" if process else "manual"))
        if origin not in {"manual", "processo"}:
            origin = "processo" if process else "manual"
        draft = str(raw.get("draft") or payload.get("rascunho_id") or f"legacy_{raw.get('id', '0')}")
        moment = str(raw.get("moment") or payload.get("registrado_em") or timestamp())
        payload.setdefault("origem_calculo", origin)
        payload.setdefault("numero_processo", process)
        payload.setdefault("rascunho_id", draft)
        payload.setdefault("campo", field)
        payload.setdefault("valor_anterior", None)
        payload.setdefault("valor_novo", None)
        payload.setdefault("extracao_id", None)
        connection.execute(
            "INSERT INTO parameter_changes(moment,draft,process,origin,field,payload) VALUES(?,?,?,?,?,?)",
            (moment, draft, process, origin, field, json.dumps(payload, ensure_ascii=False)),
        )


def _ensure_calculation_records(connection: sqlite3.Connection) -> None:
    connection.execute("""
        CREATE TABLE IF NOT EXISTS calculation_records(
            id TEXT PRIMARY KEY CHECK(id GLOB 'calc_[0-9a-f]*'),
            process TEXT NOT NULL UNIQUE,
            origin TEXT NOT NULL DEFAULT 'processo' CHECK(origin IN ('manual','processo')),
            identifier TEXT,
            normalized_identifier TEXT,
            state TEXT NOT NULL DEFAULT 'ativo' CHECK(state IN ('ativo','arquivado','cancelado')),
            state_changed_at TEXT,
            state_changed_by TEXT,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    columns = _columns(connection, "calculation_records")
    additions = {
        "origin": "TEXT NOT NULL DEFAULT 'processo'",
        "identifier": "TEXT",
        "normalized_identifier": "TEXT",
        "state": "TEXT NOT NULL DEFAULT 'ativo'",
        "state_changed_at": "TEXT",
        "state_changed_by": "TEXT",
    }
    for name, ddl in additions.items():
        if name not in columns:
            connection.execute(f"ALTER TABLE calculation_records ADD COLUMN {name} {ddl}")
    connection.execute("UPDATE calculation_records SET origin='processo' WHERE origin IS NULL OR origin='' OR origin NOT IN ('manual','processo')")
    connection.execute("UPDATE calculation_records SET identifier=process WHERE identifier IS NULL OR identifier='' ")
    connection.execute("UPDATE calculation_records SET state='ativo' WHERE state IS NULL OR state='' OR state NOT IN ('ativo','arquivado','cancelado')")
    for row in connection.execute("SELECT id,process,origin,identifier,normalized_identifier FROM calculation_records").fetchall():
        if row["normalized_identifier"]:
            continue
        origin = str(row["origin"] or "processo")
        identifier = str(row["identifier"] or row["process"] or "")
        try:
            normalized = normalize_process_number(identifier) if origin == "processo" else normalize_manual_identifier(identifier)
        except ValueError:
            normalized = identifier.upper()
        connection.execute("UPDATE calculation_records SET normalized_identifier=? WHERE id=?", (normalized, row["id"]))
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_calculation_records_identity ON calculation_records(origin, normalized_identifier)")
    connection.executescript("""
        CREATE TRIGGER IF NOT EXISTS trg_calculation_records_origin_insert
        BEFORE INSERT ON calculation_records WHEN NEW.origin NOT IN ('manual','processo')
        BEGIN SELECT RAISE(ABORT, 'invalid calculation origin'); END;
        CREATE TRIGGER IF NOT EXISTS trg_calculation_records_state_insert
        BEFORE INSERT ON calculation_records WHEN NEW.state NOT IN ('ativo','arquivado','cancelado')
        BEGIN SELECT RAISE(ABORT, 'invalid calculation state'); END;
        CREATE TRIGGER IF NOT EXISTS trg_calculation_records_state_update
        BEFORE UPDATE OF state ON calculation_records WHEN NEW.state NOT IN ('ativo','arquivado','cancelado')
        BEGIN SELECT RAISE(ABORT, 'invalid calculation state'); END;
    """)


def _create_normalized_calculation_tables(connection: sqlite3.Connection) -> None:
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS calculation_versions(
            calculation_id TEXT NOT NULL,
            version INTEGER NOT NULL CHECK(version >= 1),
            base_version INTEGER CHECK(base_version IS NULL OR base_version >= 1),
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL,
            request TEXT NOT NULL,
            total TEXT,
            index_name TEXT NOT NULL,
            update_competence TEXT NOT NULL,
            business_hash TEXT NOT NULL,
            changed_fields TEXT NOT NULL,
            diff_json TEXT NOT NULL,
            PRIMARY KEY(calculation_id, version),
            UNIQUE(calculation_id, business_hash),
            FOREIGN KEY(calculation_id) REFERENCES calculation_records(id) ON DELETE RESTRICT
        );
        CREATE TABLE IF NOT EXISTS calculation_executions(
            id TEXT PRIMARY KEY CHECK(id GLOB 'exec_[0-9a-f]*'),
            calculation_id TEXT NOT NULL,
            version INTEGER NOT NULL CHECK(version >= 1),
            executed_at TEXT NOT NULL,
            executed_by TEXT NOT NULL,
            response TEXT NOT NULL,
            input_hash TEXT NOT NULL,
            policy_hash TEXT NOT NULL,
            engine_hash TEXT NOT NULL,
            indices_hash TEXT NOT NULL,
            duration_ms REAL NOT NULL CHECK(duration_ms >= 0),
            FOREIGN KEY(calculation_id, version) REFERENCES calculation_versions(calculation_id, version) ON DELETE RESTRICT
        );
        CREATE TABLE IF NOT EXISTS calculation_artifacts(
            id TEXT PRIMARY KEY CHECK(id GLOB 'art_[0-9a-f]*'),
            execution_id TEXT NOT NULL,
            kind TEXT NOT NULL CHECK(kind = 'memoria'),
            sha256 TEXT NOT NULL,
            size_bytes INTEGER NOT NULL CHECK(size_bytes >= 0),
            mime_type TEXT NOT NULL DEFAULT 'application/pdf',
            content BLOB NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(execution_id, kind),
            FOREIGN KEY(execution_id) REFERENCES calculation_executions(id) ON DELETE RESTRICT
        );
    """)


def _insert_artifact(connection: sqlite3.Connection, execution_id: str, kind: str, content: bytes, created_at: str) -> None:
    connection.execute(
        "INSERT INTO calculation_artifacts(id,execution_id,kind,sha256,size_bytes,mime_type,content,created_at) VALUES(?,?,?,?,?,?,?,?)",
        (f"art_{uuid4().hex}", execution_id, kind, hashlib.sha256(content).hexdigest(), len(content), "application/pdf", sqlite3.Binary(content), created_at),
    )


def _normalize_calculation_storage(connection: sqlite3.Connection) -> None:
    """Migra versões/execuções com BLOBs duplicados para execução + artefato."""
    version_columns = _columns(connection, "calculation_versions")
    execution_columns = _columns(connection, "calculation_executions")
    normalized = bool(version_columns) and "response" not in version_columns and "pdf" not in version_columns and bool(execution_columns) and "request" not in execution_columns and "pdf" not in execution_columns
    if normalized:
        _create_normalized_calculation_tables(connection)
        return

    legacy_versions = [dict(row) for row in connection.execute("SELECT * FROM calculation_versions ORDER BY calculation_id,version").fetchall()] if version_columns else []
    legacy_executions = [dict(row) for row in connection.execute("SELECT * FROM calculation_executions ORDER BY executed_at").fetchall()] if execution_columns else []
    legacy_artifacts = [dict(row) for row in connection.execute("SELECT * FROM calculation_artifacts").fetchall()] if _table_exists(connection, "calculation_artifacts") else []

    if _table_exists(connection, "calculation_artifacts"):
        connection.execute("DROP TABLE calculation_artifacts")
    if _table_exists(connection, "calculation_executions"):
        connection.execute("DROP TABLE calculation_executions")
    if _table_exists(connection, "calculation_versions"):
        connection.execute("DROP TABLE calculation_versions")
    _create_normalized_calculation_tables(connection)

    request_by_key: dict[tuple[str, int], dict] = {}
    version_by_key: dict[tuple[str, int], dict] = {}
    for row in legacy_versions:
        calculation_id = str(row["calculation_id"])
        version = int(row["version"])
        try:
            current_request = json.loads(row.get("request") or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            current_request = {}
        request_by_key[(calculation_id, version)] = current_request
        version_by_key[(calculation_id, version)] = row
        base = int(row["base_version"]) if row.get("base_version") is not None else None
        previous = request_by_key.get((calculation_id, base)) if base is not None else None
        computed_hash = str(row.get("business_hash") or business_hash(current_request))
        diff_value = row.get("diff_json") or full_diff(previous, current_request).model_dump_json()
        changed_value = row.get("changed_fields") or json.dumps(_changed_fields(CalculationDiff.model_validate_json(diff_value)), ensure_ascii=False)
        connection.execute(
            """
            INSERT OR IGNORE INTO calculation_versions(
                calculation_id,version,base_version,created_at,created_by,request,total,index_name,update_competence,
                business_hash,changed_fields,diff_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                calculation_id, version, base, str(row.get("created_at") or timestamp()), str(row.get("created_by") or "legacy"),
                json.dumps(current_request, ensure_ascii=False), row.get("total"), str(row.get("index_name") or "desconhecido"),
                str(row.get("update_competence") or "desconhecida"), computed_hash, changed_value, diff_value,
            ),
        )

    executions_by_key: dict[tuple[str, int], list[dict]] = {}
    for execution in legacy_executions:
        key = (str(execution["calculation_id"]), int(execution["version"]))
        executions_by_key.setdefault(key, []).append(execution)

    artifacts_by_execution: dict[str, list[dict]] = {}
    for artifact in legacy_artifacts:
        artifacts_by_execution.setdefault(str(artifact.get("execution_id")), []).append(artifact)

    for key, version_row in version_by_key.items():
        execution_rows = executions_by_key.get(key) or []
        if not execution_rows:
            execution_rows = [{
                "id": f"exec_{uuid4().hex}",
                "calculation_id": key[0],
                "version": key[1],
                "executed_at": version_row.get("created_at") or timestamp(),
                "executed_by": version_row.get("created_by") or "legacy",
                "response": version_row.get("response") or "{}",
                "input_hash": version_row.get("input_hash") or "legacy",
                "policy_hash": version_row.get("policy_hash") or "legacy",
                "engine_hash": version_row.get("engine_hash") or "legacy",
                "indices_hash": version_row.get("indices_hash") or "legacy",
                "duration_ms": 0.0,
                "pdf": version_row.get("pdf"),
            }]
        for execution in execution_rows:
            execution_id = str(execution.get("id") or f"exec_{uuid4().hex}")
            response_text = execution.get("response") or version_row.get("response") or "{}"
            try:
                response_payload = json.loads(response_text) if isinstance(response_text, str) else response_text
                duration = float(execution.get("duration_ms") or (response_payload.get("metadata") or {}).get("duracao_ms") or 0.0)
            except (TypeError, ValueError, json.JSONDecodeError):
                duration = float(execution.get("duration_ms") or 0.0)
            connection.execute(
                """
                INSERT INTO calculation_executions(
                    id,calculation_id,version,executed_at,executed_by,response,input_hash,policy_hash,engine_hash,indices_hash,duration_ms
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    execution_id, key[0], key[1], str(execution.get("executed_at") or version_row.get("created_at") or timestamp()),
                    str(execution.get("executed_by") or version_row.get("created_by") or "legacy"),
                    response_text if isinstance(response_text, str) else json.dumps(response_text, ensure_ascii=False),
                    str(execution.get("input_hash") or version_row.get("input_hash") or "legacy"),
                    str(execution.get("policy_hash") or version_row.get("policy_hash") or "legacy"),
                    str(execution.get("engine_hash") or version_row.get("engine_hash") or "legacy"),
                    str(execution.get("indices_hash") or version_row.get("indices_hash") or "legacy"), duration,
                ),
            )
            existing_artifacts = [artifact for artifact in (artifacts_by_execution.get(execution_id) or []) if str(artifact.get("kind") or "") == "memoria"]
            if existing_artifacts:
                artifact = existing_artifacts[0]
                content = bytes(artifact.get("content") or b"")
                _insert_artifact(connection, execution_id, "memoria", content, str(artifact.get("created_at") or timestamp()))
            else:
                normal = execution.get("pdf") if "pdf" in execution else version_row.get("pdf")
                if normal is not None:
                    _insert_artifact(connection, execution_id, "memoria", bytes(normal), str(execution.get("executed_at") or timestamp()))



def _ensure_learning_and_finops(connection: sqlite3.Connection) -> None:
    """Cria estruturas imutáveis de feedback supervisionado e FinOps da IA."""
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS extraction_feedback(
            id TEXT PRIMARY KEY CHECK(id GLOB 'fb_[0-9a-f]*'),
            event_fingerprint TEXT NOT NULL UNIQUE CHECK(length(event_fingerprint)=64),
            process TEXT,
            draft TEXT NOT NULL,
            extraction_job TEXT,
            field TEXT NOT NULL,
            action TEXT NOT NULL CHECK(action IN ('confirmed','corrected','removed','added','not_found','ambiguous')),
            reason_code TEXT NOT NULL,
            comment TEXT,
            model_value TEXT,
            human_value TEXT,
            document_name TEXT,
            page INTEGER CHECK(page IS NULL OR page >= 1),
            model_evidence TEXT,
            document_type TEXT,
            prompt_version TEXT,
            model_name TEXT,
            pipeline_version TEXT NOT NULL,
            reviewer_hash TEXT NOT NULL CHECK(length(reviewer_hash)=64),
            created_at TEXT NOT NULL,
            curation_status TEXT NOT NULL DEFAULT 'pending' CHECK(curation_status IN ('pending','approved','rejected')),
            curated_by_hash TEXT,
            curated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS training_examples(
            id TEXT PRIMARY KEY CHECK(id GLOB 'ex_[0-9a-f]*'),
            feedback_id TEXT NOT NULL UNIQUE,
            field TEXT NOT NULL,
            task TEXT NOT NULL,
            evidence TEXT,
            model_value TEXT,
            expected_value TEXT,
            reason_code TEXT NOT NULL,
            content_sha256 TEXT NOT NULL CHECK(length(content_sha256)=64),
            created_at TEXT NOT NULL,
            FOREIGN KEY(feedback_id) REFERENCES extraction_feedback(id) ON DELETE RESTRICT
        );
        CREATE TABLE IF NOT EXISTS training_dataset_versions(
            id TEXT PRIMARY KEY CHECK(id GLOB 'ds_[0-9a-f]*'),
            created_at TEXT NOT NULL,
            created_by_hash TEXT NOT NULL CHECK(length(created_by_hash)=64),
            sha256 TEXT NOT NULL UNIQUE CHECK(length(sha256)=64),
            example_count INTEGER NOT NULL CHECK(example_count >= 0),
            example_ids TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS ai_usage_events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            job TEXT,
            stage TEXT NOT NULL,
            model TEXT NOT NULL,
            request_sha256 TEXT NOT NULL CHECK(length(request_sha256)=64),
            cache_hit INTEGER NOT NULL DEFAULT 0 CHECK(cache_hit IN (0,1)),
            success INTEGER NOT NULL DEFAULT 1 CHECK(success IN (0,1)),
            input_chars INTEGER NOT NULL CHECK(input_chars >= 0),
            output_chars INTEGER NOT NULL CHECK(output_chars >= 0),
            input_tokens_actual INTEGER CHECK(input_tokens_actual IS NULL OR input_tokens_actual >= 0),
            cached_input_tokens_actual INTEGER CHECK(cached_input_tokens_actual IS NULL OR cached_input_tokens_actual >= 0),
            output_tokens_actual INTEGER CHECK(output_tokens_actual IS NULL OR output_tokens_actual >= 0),
            input_tokens_estimated INTEGER NOT NULL CHECK(input_tokens_estimated >= 0),
            output_tokens_estimated INTEGER NOT NULL CHECK(output_tokens_estimated >= 0),
            cost_estimated_usd TEXT,
            duration_ms REAL NOT NULL CHECK(duration_ms >= 0),
            pages INTEGER CHECK(pages IS NULL OR pages >= 0),
            structural_repair INTEGER NOT NULL DEFAULT 0 CHECK(structural_repair IN (0,1))
        );
        CREATE TABLE IF NOT EXISTS ai_prompt_cache(
            request_sha256 TEXT PRIMARY KEY CHECK(length(request_sha256)=64),
            model TEXT NOT NULL,
            stage TEXT NOT NULL,
            response_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_hit_at TEXT,
            hit_count INTEGER NOT NULL DEFAULT 0 CHECK(hit_count >= 0)
        );
        CREATE INDEX IF NOT EXISTS idx_feedback_status_created ON extraction_feedback(curation_status, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_feedback_field_action ON extraction_feedback(field, action);
        CREATE INDEX IF NOT EXISTS idx_feedback_process ON extraction_feedback(process, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_training_examples_task ON training_examples(task, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_ai_usage_created ON ai_usage_events(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_ai_usage_stage ON ai_usage_events(stage, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_ai_usage_job ON ai_usage_events(job, id);

        CREATE TRIGGER IF NOT EXISTS trg_feedback_immutable_delete
        BEFORE DELETE ON extraction_feedback
        BEGIN SELECT RAISE(ABORT, 'feedback events cannot be deleted'); END;
        CREATE TRIGGER IF NOT EXISTS trg_training_examples_immutable_update
        BEFORE UPDATE ON training_examples
        BEGIN SELECT RAISE(ABORT, 'training examples are immutable'); END;
        CREATE TRIGGER IF NOT EXISTS trg_training_examples_immutable_delete
        BEFORE DELETE ON training_examples
        BEGIN SELECT RAISE(ABORT, 'training examples are immutable'); END;
        CREATE TRIGGER IF NOT EXISTS trg_dataset_versions_immutable_update
        BEFORE UPDATE ON training_dataset_versions
        BEGIN SELECT RAISE(ABORT, 'dataset versions are immutable'); END;
        CREATE TRIGGER IF NOT EXISTS trg_dataset_versions_immutable_delete
        BEFORE DELETE ON training_dataset_versions
        BEGIN SELECT RAISE(ABORT, 'dataset versions are immutable'); END;
    """)
    # Compatibilidade com instalações que tenham criado a tabela de telemetria
    # numa versão intermediária sem a coluna de sucesso.
    usage_columns = _columns(connection, "ai_usage_events")
    if "success" not in usage_columns:
        connection.execute(
            "ALTER TABLE ai_usage_events ADD COLUMN success INTEGER NOT NULL DEFAULT 1 CHECK(success IN (0,1))"
        )

def _indexes(connection: sqlite3.Connection) -> None:
    connection.executescript("""
        CREATE INDEX IF NOT EXISTS idx_extraction_queue_ready ON extraction_queue(state, available_at, created_at);
        CREATE INDEX IF NOT EXISTS idx_parameter_changes_process ON parameter_changes(process, moment);
        CREATE INDEX IF NOT EXISTS idx_parameter_changes_draft ON parameter_changes(draft, moment);
        CREATE INDEX IF NOT EXISTS idx_calculation_records_process ON calculation_records(process);
        CREATE INDEX IF NOT EXISTS idx_calculation_records_state_updated ON calculation_records(state, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_calculation_versions_created ON calculation_versions(calculation_id, version DESC);
        CREATE UNIQUE INDEX IF NOT EXISTS uq_calculation_versions_business_hash ON calculation_versions(calculation_id, business_hash);
        CREATE INDEX IF NOT EXISTS idx_calculation_executions_version ON calculation_executions(calculation_id, version, executed_at DESC);
        CREATE INDEX IF NOT EXISTS idx_calculation_artifacts_execution ON calculation_artifacts(execution_id, kind);

        CREATE TRIGGER IF NOT EXISTS trg_calculation_versions_base_insert
        BEFORE INSERT ON calculation_versions
        WHEN NEW.base_version IS NOT NULL AND (
            NEW.base_version >= NEW.version OR
            NOT EXISTS(
                SELECT 1 FROM calculation_versions previous
                WHERE previous.calculation_id=NEW.calculation_id AND previous.version=NEW.base_version
            )
        )
        BEGIN SELECT RAISE(ABORT, 'invalid calculation base version'); END;

        CREATE TRIGGER IF NOT EXISTS trg_calculation_versions_hash_insert
        BEFORE INSERT ON calculation_versions WHEN length(NEW.business_hash) <> 64
        BEGIN SELECT RAISE(ABORT, 'invalid calculation business hash'); END;

        CREATE TRIGGER IF NOT EXISTS trg_calculation_versions_immutable_update
        BEFORE UPDATE ON calculation_versions
        BEGIN SELECT RAISE(ABORT, 'calculation versions are immutable'); END;
        CREATE TRIGGER IF NOT EXISTS trg_calculation_versions_immutable_delete
        BEFORE DELETE ON calculation_versions
        BEGIN SELECT RAISE(ABORT, 'calculation versions are immutable'); END;

        CREATE TRIGGER IF NOT EXISTS trg_calculation_executions_hashes_insert
        BEFORE INSERT ON calculation_executions
        WHEN length(NEW.input_hash) <> 64 OR length(NEW.policy_hash) <> 64 OR length(NEW.engine_hash) <> 64 OR length(NEW.indices_hash) <> 64
        BEGIN SELECT RAISE(ABORT, 'invalid calculation execution hash'); END;
        CREATE TRIGGER IF NOT EXISTS trg_calculation_executions_immutable_update
        BEFORE UPDATE ON calculation_executions
        BEGIN SELECT RAISE(ABORT, 'calculation executions are immutable'); END;
        CREATE TRIGGER IF NOT EXISTS trg_calculation_executions_immutable_delete
        BEFORE DELETE ON calculation_executions
        BEGIN SELECT RAISE(ABORT, 'calculation executions are immutable'); END;

        CREATE TRIGGER IF NOT EXISTS trg_calculation_artifacts_hash_insert
        BEFORE INSERT ON calculation_artifacts WHEN length(NEW.sha256) <> 64
        BEGIN SELECT RAISE(ABORT, 'invalid calculation artifact hash'); END;
        CREATE TRIGGER IF NOT EXISTS trg_calculation_artifacts_immutable_update
        BEFORE UPDATE ON calculation_artifacts
        BEGIN SELECT RAISE(ABORT, 'calculation artifacts are immutable'); END;
        CREATE TRIGGER IF NOT EXISTS trg_calculation_artifacts_immutable_delete
        BEFORE DELETE ON calculation_artifacts
        BEGIN SELECT RAISE(ABORT, 'calculation artifacts are immutable'); END;
    """)


def migrate(database: SQLiteDatabase) -> None:
    """Aplica migrações antes de os serviços iniciarem.

    ``executescript`` pode abrir/fechar transações internamente no SQLite; por isso
    a migração usa ``commit`` explícito ao final, em vez de assumir um ``BEGIN``
    manual ainda ativo após cada script. A inicialização ocorre antes dos workers.
    """
    connection = database.connect(foreign_keys=False)
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        _base_schema(connection)
        _ensure_parameter_changes(connection)
        _ensure_calculation_records(connection)
        _normalize_calculation_storage(connection)
        _ensure_learning_and_finops(connection)
        _indexes(connection)
        connection.execute(
            "INSERT OR REPLACE INTO schema_migrations(version,applied_at) VALUES(?,?)",
            (SCHEMA_VERSION, timestamp()),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
