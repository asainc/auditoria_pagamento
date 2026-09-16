"""Persistência transacional do estado de negócio; nenhum estado visual é salvo."""
from __future__ import annotations

import json
import sqlite3
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
            connection.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, process TEXT NOT NULL, hash TEXT NOT NULL, payload TEXT NOT NULL, UNIQUE(process,hash));
                CREATE TABLE IF NOT EXISTS extractions(process TEXT PRIMARY KEY, job TEXT NOT NULL, payload TEXT NOT NULL, result TEXT);
                CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, moment TEXT NOT NULL, event TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS parameter_changes(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    moment TEXT NOT NULL,
                    draft TEXT NOT NULL,
                    process TEXT,
                    origin TEXT NOT NULL,
                    field TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_parameter_changes_process ON parameter_changes(process, moment);
                CREATE INDEX IF NOT EXISTS idx_parameter_changes_draft ON parameter_changes(draft, moment);
                CREATE TABLE IF NOT EXISTS index_state(id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL);
            """)

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

    def start_job(self, status: ExtractionStatus) -> None:
        """Registra a revisão vigente do trabalho e permite rejeitar resultados de outra revisão."""
        with self.connection() as connection:
            connection.execute("INSERT INTO extractions VALUES(?,?,?,NULL) ON CONFLICT(process) DO UPDATE SET job=excluded.job,payload=excluded.payload,result=NULL", (status.numero_processo, status.identificador, status.model_dump_json()))

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
        """Reinício não simula conclusão: trabalhos pendentes ficam disponíveis para repetição."""
        for process in self.processes():
            status = self.status(process.numero_processo)
            if status and status.estado in {"aguardando", "executando"}:
                status.estado = "interrompida"
                status.mensagem = "Serviço reiniciado. Solicite nova extração."
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
