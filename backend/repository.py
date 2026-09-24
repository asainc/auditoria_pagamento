"""Persistência transacional do estado de negócio; nenhum estado visual é salvo."""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from backend.models import DocumentMetadata, ExtractionResult, ExtractionStatus, ParameterChangeInput, ParameterChangeRecord, ProcessSummary


def timestamp() -> str:
    """Horário UTC torna eventos comparáveis em instalações distintas."""
    return datetime.now(timezone.utc).isoformat()


class Repository:
    """SQLite com conexão curta por operação e compare-and-set para trabalhos."""
    def __init__(self, data_dir: Path):
        """Recebe dependências explicitamente para manter configuração e testes isolados."""
        self.data_dir = data_dir
        data_dir.mkdir(parents=True, exist_ok=True)
        self.path = data_dir / "business.sqlite3"
        with self.connection() as connection:
            # Primeiro criamos apenas estruturas que não dependem de colunas
            # adicionadas em versões posteriores. Os índices são criados depois
            # da migração para permitir abrir bases SQLite de versões antigas.
            connection.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, process TEXT NOT NULL, hash TEXT NOT NULL, payload TEXT NOT NULL, UNIQUE(process,hash));
                CREATE TABLE IF NOT EXISTS extractions(process TEXT PRIMARY KEY, job TEXT NOT NULL, payload TEXT NOT NULL, result TEXT);
                CREATE TABLE IF NOT EXISTS extraction_queue(
                    job TEXT PRIMARY KEY,
                    process TEXT NOT NULL,
                    state TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    available_at REAL NOT NULL,
                    lease_until REAL,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, moment TEXT NOT NULL, event TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS index_state(id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL);
            """)
            self._ensure_parameter_changes_schema(connection)
            connection.executescript("""
                CREATE INDEX IF NOT EXISTS idx_extraction_queue_ready ON extraction_queue(state, available_at, created_at);
                CREATE INDEX IF NOT EXISTS idx_parameter_changes_process ON parameter_changes(process, moment);
                CREATE INDEX IF NOT EXISTS idx_parameter_changes_draft ON parameter_changes(draft, moment);
            """)

    @staticmethod
    def _parameter_changes_ddl(table: str = "parameter_changes") -> str:
        """Retorna o DDL canônico da trilha de revisão humana."""
        return f"""
            CREATE TABLE {table}(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                moment TEXT NOT NULL,
                draft TEXT NOT NULL,
                process TEXT,
                origin TEXT NOT NULL,
                field TEXT NOT NULL,
                payload TEXT NOT NULL
            )
        """

    def _ensure_parameter_changes_schema(self, connection: sqlite3.Connection) -> None:
        """Migra versões antigas da tabela sem descartar o histórico original.

        Versões anteriores armazenavam somente processo/campo/payload. A interface
        atual também audita cálculos manuais por ``draft`` e ``origin``. Como
        ``CREATE TABLE IF NOT EXISTS`` não adiciona colunas, bases persistidas
        precisavam de uma migração explícita. O legado é mantido em uma tabela
        renomeada e registros reconhecíveis são copiados para o contrato atual.
        """
        existing = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='parameter_changes'"
        ).fetchone()
        if existing is None:
            connection.execute(self._parameter_changes_ddl())
            return

        columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(parameter_changes)").fetchall()}
        expected = {"id", "moment", "draft", "process", "origin", "field", "payload"}
        if expected.issubset(columns):
            return

        suffix = 1
        legacy = "parameter_changes_legacy_v1"
        existing_tables = {str(row[0]) for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        while legacy in existing_tables:
            suffix += 1
            legacy = f"parameter_changes_legacy_v{suffix}"

        connection.execute(f'ALTER TABLE parameter_changes RENAME TO "{legacy}"')
        connection.execute(self._parameter_changes_ddl())

        rows = connection.execute(f'SELECT * FROM "{legacy}"').fetchall()
        for row in rows:
            raw = dict(row)
            try:
                payload = json.loads(raw.get("payload") or "{}")
            except (TypeError, ValueError, json.JSONDecodeError):
                payload = {}
            if not isinstance(payload, dict):
                payload = {}

            field = str(raw.get("field") or payload.get("campo") or "").strip()
            # Linhas sem campo reconhecível continuam preservadas na tabela legacy;
            # não são materializadas no contrato atual para não quebrar a UI.
            if not field:
                continue
            process = raw.get("process") or payload.get("numero_processo")
            origin = str(raw.get("origin") or payload.get("origem_calculo") or ("processo" if process else "manual"))
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

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        """Commit ou rollback integral, sem conexões compartilhadas entre threads."""
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def add_document(self, document: DocumentMetadata) -> DocumentMetadata:
        """A unicidade por processo e hash torna o reenvio idempotente."""
        with self.connection() as connection:
            connection.execute("INSERT OR IGNORE INTO documents VALUES(?,?,?,?)", (document.identificador, document.numero_processo, document.sha256, document.model_dump_json()))
            row = connection.execute("SELECT payload FROM documents WHERE process=? AND hash=?", (document.numero_processo, document.sha256)).fetchone()
        return DocumentMetadata.model_validate_json(row["payload"])

    def documents(self, process: str) -> list[DocumentMetadata]:
        """Consulta documentos pelo processo com parâmetros SQL vinculados."""
        with self.connection() as connection:
            rows = connection.execute("SELECT payload FROM documents WHERE process=? ORDER BY rowid", (process,)).fetchall()
        return [DocumentMetadata.model_validate_json(row["payload"]) for row in rows]

    def document(self, identifier: str) -> DocumentMetadata | None:
        """Resolve identificador opaco sem aceitar caminhos do usuário."""
        with self.connection() as connection:
            row = connection.execute("SELECT payload FROM documents WHERE id=?", (identifier,)).fetchone()
        return DocumentMetadata.model_validate_json(row["payload"]) if row else None

    def classify_document(self, identifier: str, classification: str) -> None:
        """Somente a classificação muda; hash e associação ao processo permanecem fixos."""
        document = self.document(identifier)
        if document:
            document.classificacao = classification
            with self.connection() as connection:
                connection.execute("UPDATE documents SET payload=? WHERE id=?", (document.model_dump_json(), identifier))

    def processes(self) -> list[ProcessSummary]:
        """Deriva a lista de processos do estado documental persistido."""
        with self.connection() as connection:
            rows = connection.execute("SELECT process, COUNT(*) AS count FROM documents GROUP BY process ORDER BY process").fetchall()
        return [ProcessSummary(numero_processo=row["process"], quantidade_documentos=row["count"]) for row in rows]

    def start_job(self, status: ExtractionStatus, *, max_attempts: int = 3) -> None:
        """Registra a revisão vigente e enfileira trabalho durável de forma idempotente."""
        now = time.time()
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO extractions VALUES(?,?,?,NULL) ON CONFLICT(process) DO UPDATE SET job=excluded.job,payload=excluded.payload,result=NULL",
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

    def claim_extraction_job(self, lease_seconds: int) -> tuple[str, str, int, int] | None:
        """Reserva atomicamente o próximo job pronto e recupera leases expirados."""
        now = time.time()
        connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE extraction_queue SET state='queued',lease_until=NULL "
                "WHERE state='leased' AND lease_until IS NOT NULL AND lease_until<?",
                (now,),
            )
            row = connection.execute(
                "SELECT job,process,attempts,max_attempts FROM extraction_queue "
                "WHERE state='queued' AND available_at<=? ORDER BY created_at LIMIT 1",
                (now,),
            ).fetchone()
            if row is None:
                connection.execute("COMMIT")
                return None
            job, process, attempts, max_attempts = row
            attempt = int(attempts) + 1
            connection.execute(
                "UPDATE extraction_queue SET state='leased',attempts=?,lease_until=? WHERE job=?",
                (attempt, now + lease_seconds, job),
            )
            connection.execute("COMMIT")
            return str(job), str(process), attempt, int(max_attempts)
        except Exception:
            connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def retry_extraction_job(self, job: str, delay_seconds: float) -> None:
        """Reagenda job após falha transitória sem criar uma nova revisão."""
        with self.connection() as connection:
            connection.execute(
                "UPDATE extraction_queue SET state='queued',available_at=?,lease_until=NULL WHERE job=?",
                (time.time() + max(0.0, delay_seconds), job),
            )

    def finish_extraction_job(self, job: str, *, success: bool) -> None:
        """Finaliza job; histórico técnico permanece no SQLite para diagnóstico."""
        with self.connection() as connection:
            connection.execute(
                "UPDATE extraction_queue SET state=?,lease_until=NULL WHERE job=?",
                ("done" if success else "failed", job),
            )

    def update_job(self, status: ExtractionStatus, result: ExtractionResult | None = None) -> None:
        """Atualiza somente a revisão ainda vigente e rejeita retornos atrasados."""
        with self.connection() as connection:
            connection.execute("UPDATE extractions SET payload=?, result=? WHERE process=? AND job=?", (status.model_dump_json(), result.model_dump_json() if result else None, status.numero_processo, status.identificador))

    def status(self, process: str) -> ExtractionStatus | None:
        """Consulta estado persistido; ausência é distinta de falha de processamento."""
        with self.connection() as connection:
            row = connection.execute("SELECT payload FROM extractions WHERE process=?", (process,)).fetchone()
        return ExtractionStatus.model_validate_json(row["payload"]) if row else None

    def result(self, process: str) -> ExtractionResult | None:
        """Só disponibiliza resultado associado à revisão vigente."""
        with self.connection() as connection:
            row = connection.execute("SELECT result FROM extractions WHERE process=?", (process,)).fetchone()
        return ExtractionResult.model_validate_json(row["result"]) if row and row["result"] else None

    def recover_jobs(self) -> None:
        """Reinício recoloca jobs pendentes na fila em vez de exigir repetição manual."""
        now = time.time()
        with self.connection() as connection:
            connection.execute(
                "UPDATE extraction_queue SET state='queued',available_at=?,lease_until=NULL WHERE state IN ('queued','leased')",
                (now,),
            )
        for process in self.processes():
            status = self.status(process.numero_processo)
            if status and status.estado in {"aguardando", "executando", "interrompida"}:
                status.estado = "aguardando"
                status.etapa = "Recuperando trabalho"
                status.mensagem = "Extração recuperada após reinício e devolvida à fila durável."
                status.atualizado_em = timestamp()
                self.update_job(status)

    def add_parameter_change(
        self,
        change: ParameterChangeInput,
        *,
        actor: str,
        extracted_value: object = None,
        extracted_source: str | None = None,
    ) -> ParameterChangeRecord:
        """Persiste evento imutável de revisão e devolve o registro materializado."""
        moment = timestamp()
        payload = change.model_dump(mode="json")
        payload.update({
            "ator_tecnico": actor,
            "valor_extraido": extracted_value,
            "origem_extraida": extracted_source,
        })
        with self.connection() as connection:
            cursor = connection.execute(
                "INSERT INTO parameter_changes(moment,draft,process,origin,field,payload) VALUES(?,?,?,?,?,?)",
                (moment, change.rascunho_id, change.numero_processo, change.origem_calculo, change.campo, json.dumps(payload, ensure_ascii=False)),
            )
            identifier = int(cursor.lastrowid)
        return ParameterChangeRecord(
            **change.model_dump(),
            identificador=identifier,
            registrado_em=moment,
            ator_tecnico=actor,
            valor_extraido=extracted_value,
            origem_extraida=extracted_source,
        )

    def parameter_changes(self, *, process: str | None = None, draft: str | None = None) -> list[ParameterChangeRecord]:
        """Consulta a trilha por processo real ou por rascunho manual, em ordem temporal."""
        if bool(process) == bool(draft):
            raise ValueError("Informe exatamente process ou draft para consultar alterações.")
        column, value = ("process", process) if process else ("draft", draft)
        with self.connection() as connection:
            rows = connection.execute(
                f"SELECT id,moment,payload FROM parameter_changes WHERE {column}=? ORDER BY id",  # coluna é constante interna
                (value,),
            ).fetchall()
        records: list[ParameterChangeRecord] = []
        for row in rows:
            payload = json.loads(row["payload"])
            records.append(ParameterChangeRecord(
                origem_calculo=payload["origem_calculo"],
                numero_processo=payload.get("numero_processo"),
                rascunho_id=payload["rascunho_id"],
                campo=payload["campo"],
                valor_anterior=payload.get("valor_anterior"),
                valor_novo=payload.get("valor_novo"),
                extracao_id=payload.get("extracao_id"),
                identificador=int(row["id"]),
                registrado_em=row["moment"],
                ator_tecnico=payload.get("ator_tecnico", "desconhecido"),
                valor_extraido=payload.get("valor_extraido"),
                origem_extraida=payload.get("origem_extraida"),
            ))
        return records

    def audit(self, event: str, payload: dict[str, str | int | float | bool]) -> None:
        """Somente identificadores técnicos, contagens e hashes; nunca conteúdo documental."""
        with self.connection() as connection:
            connection.execute("INSERT INTO audit(moment,event,payload) VALUES(?,?,?)", (timestamp(), event, json.dumps(payload)))
