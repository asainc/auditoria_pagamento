"""Persistência da supervisão humana, curadoria e datasets versionados."""
from __future__ import annotations

import hashlib
import json
import math
import re
from decimal import Decimal
from uuid import uuid4

from backend.contracts.quality import (
    DatasetSnapshot,
    FeedbackCurationInput,
    FeedbackEventRecord,
    FeedbackFieldMetric,
    FeedbackPage,
    FeedbackReasonMetric,
    LearningExample,
    QualitySummary,
)
from backend.persistence.schema import timestamp
from backend.persistence.sqlite import SQLiteDatabase


_STAGE_FIELDS: dict[str, tuple[str, ...]] = {
    "00_classificacao": ("documentos.",),
    "01_parcelas": ("parcelas.",),
    "02_correcao": ("parametros.indice", "parametros.mes_atualizacao", "parametros.ano_atualizacao", "parametros.deflacionar_valor_nominal", "parametros.competencia_final_taxa_legal"),
    "03_moratorios": ("parametros.juros_moratorios_",),
    "05_encargos": ("parametros.multa_", "parametros.honorarios", "parametros.honorarios_tipo", "parametros.art_523", "parametros.incidir_"),
    "06_prescricao": ("parametros.prescricao_",),
    "07_compensacao": ("parametros.compensacao_",),
    "08_duplo_indice": ("parametros.duplo_indice_",),
    "09_valor_dobrado": ("parametros.valor_dobrado_flag",),
}


def stage_for_field(field: str) -> str:
    for stage, prefixes in _STAGE_FIELDS.items():
        if any(field.startswith(prefix) for prefix in prefixes):
            return stage
    return "outro"


def _decode_scalar(value: str | None):
    if value is None:
        return None
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return value


class QualityRepository:
    """Repositório analítico separado do banco operacional de extração."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def add_feedback(self, payload: dict) -> tuple[FeedbackEventRecord, bool]:
        """Insere evento imutável e deduplica reenvios pelo fingerprint."""
        event_id = payload.get("id") or f"fb_{uuid4().hex}"
        with self.database.connection() as connection:
            existing = connection.execute(
                "SELECT * FROM extraction_feedback WHERE event_fingerprint=?",
                (payload["event_fingerprint"],),
            ).fetchone()
            created = existing is None
            if created:
                connection.execute(
                    """
                    INSERT INTO extraction_feedback(
                        id,event_fingerprint,process,draft,extraction_job,field,action,reason_code,comment,
                        model_value,human_value,document_name,page,model_evidence,document_type,prompt_version,
                        model_name,pipeline_version,reviewer_hash,created_at,curation_status
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        event_id, payload["event_fingerprint"], payload.get("process"), payload["draft"],
                        payload.get("extraction_job"), payload["field"], payload["action"], payload["reason_code"],
                        payload.get("comment"), payload.get("model_value"), payload.get("human_value"),
                        payload.get("document_name"), payload.get("page"), payload.get("model_evidence"),
                        payload.get("document_type"), payload.get("prompt_version"), payload.get("model_name"),
                        payload["pipeline_version"], payload["reviewer_hash"], payload["created_at"],
                        payload.get("curation_status", "pending"),
                    ),
                )
                row = connection.execute("SELECT * FROM extraction_feedback WHERE id=?", (event_id,)).fetchone()
            else:
                row = existing
        return self._feedback_record(row), created

    @staticmethod
    def _feedback_record(row) -> FeedbackEventRecord:
        return FeedbackEventRecord(
            identificador=str(row["id"]),
            numero_processo=row["process"],
            rascunho_id=str(row["draft"]),
            extracao_id=row["extraction_job"],
            campo=str(row["field"]),
            acao=str(row["action"]),
            motivo_codigo=str(row["reason_code"]),
            comentario=row["comment"],
            valor_modelo=_decode_scalar(row["model_value"]),
            valor_humano=_decode_scalar(row["human_value"]),
            documento=row["document_name"],
            pagina=int(row["page"]) if row["page"] is not None else None,
            evidencia_modelo=row["model_evidence"],
            tipo_documento=row["document_type"],
            versao_prompts=row["prompt_version"],
            modelo=row["model_name"],
            pipeline_version=str(row["pipeline_version"]),
            revisor_pseudonimo=str(row["reviewer_hash"]),
            criado_em=str(row["created_at"]),
            status_curadoria=str(row["curation_status"]),
        )

    def page(self, *, page: int, page_size: int, status: str | None = None, field: str | None = None) -> FeedbackPage:
        clauses: list[str] = []
        args: list[object] = []
        if status:
            clauses.append("curation_status=?")
            args.append(status)
        if field:
            clauses.append("field LIKE ?")
            args.append(f"%{field}%")
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self.database.connection() as connection:
            total = int(connection.execute(f"SELECT COUNT(*) FROM extraction_feedback{where}", args).fetchone()[0])
            rows = connection.execute(
                f"SELECT * FROM extraction_feedback{where} ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?",
                (*args, page_size, (page - 1) * page_size),
            ).fetchall()
        return FeedbackPage(
            itens=[self._feedback_record(row) for row in rows],
            pagina=page,
            tamanho_pagina=page_size,
            total_itens=total,
            total_paginas=math.ceil(total / page_size) if total else 0,
        )

    def curate(self, feedback_id: str, payload: FeedbackCurationInput, curator_hash: str) -> FeedbackEventRecord | None:
        now = timestamp()
        with self.database.connection() as connection:
            row = connection.execute("SELECT * FROM extraction_feedback WHERE id=?", (feedback_id,)).fetchone()
            if row is None:
                return None
            reason = payload.motivo_codigo or row["reason_code"]
            comment = payload.comentario if payload.comentario is not None else row["comment"]
            connection.execute(
                "UPDATE extraction_feedback SET curation_status=?,reason_code=?,comment=?,curated_by_hash=?,curated_at=? WHERE id=?",
                (payload.status, reason, comment, curator_hash, now, feedback_id),
            )
            if payload.status == "approved":
                content = {
                    "field": row["field"],
                    "task": stage_for_field(str(row["field"])),
                    "evidence": row["model_evidence"],
                    "model_value": row["model_value"],
                    "expected_value": row["human_value"],
                    "reason_code": reason,
                }
                digest = hashlib.sha256(json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
                connection.execute(
                    """
                    INSERT OR IGNORE INTO training_examples(
                        id,feedback_id,field,task,evidence,model_value,expected_value,reason_code,content_sha256,created_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?)
                    """,
                    (f"ex_{uuid4().hex}", feedback_id, row["field"], content["task"], row["model_evidence"], row["model_value"], row["human_value"], reason, digest, now),
                )
            updated = connection.execute("SELECT * FROM extraction_feedback WHERE id=?", (feedback_id,)).fetchone()
        return self._feedback_record(updated)

    def summary(self) -> QualitySummary:
        with self.database.connection() as connection:
            actions = {str(row["action"]): int(row["count"]) for row in connection.execute("SELECT action,COUNT(*) AS count FROM extraction_feedback GROUP BY action")}
            pending = int(connection.execute("SELECT COUNT(*) FROM extraction_feedback WHERE curation_status='pending'").fetchone()[0])
            field_rows = connection.execute(
                """
                SELECT field,
                    COUNT(*) total,
                    SUM(action='confirmed') confirmed,
                    SUM(action='corrected') corrected,
                    SUM(action='removed') removed,
                    SUM(action='added') added
                FROM extraction_feedback GROUP BY field ORDER BY (SUM(action!='confirmed') * 1.0 / COUNT(*)) DESC,total DESC LIMIT 30
                """
            ).fetchall()
            reason_rows = connection.execute(
                "SELECT reason_code,COUNT(*) count FROM extraction_feedback WHERE action!='confirmed' GROUP BY reason_code ORDER BY count DESC"
            ).fetchall()
        confirmed = actions.get("confirmed", 0)
        corrected = actions.get("corrected", 0)
        removed = actions.get("removed", 0)
        added = actions.get("added", 0)
        total = sum(actions.values())
        intervention = corrected + removed + added + actions.get("not_found", 0) + actions.get("ambiguous", 0)
        rate = Decimal(intervention) / Decimal(total) if total else Decimal("0")
        metrics: list[FeedbackFieldMetric] = []
        for row in field_rows:
            row_total = int(row["total"])
            row_intervention = int(row["corrected"] or 0) + int(row["removed"] or 0) + int(row["added"] or 0)
            metrics.append(FeedbackFieldMetric(
                campo=str(row["field"]), total=row_total, confirmados=int(row["confirmed"] or 0),
                corrigidos=int(row["corrected"] or 0), removidos=int(row["removed"] or 0), adicionados=int(row["added"] or 0),
                taxa_intervencao=(Decimal(row_intervention) / Decimal(row_total) if row_total else Decimal("0")),
            ))
        return QualitySummary(
            total_eventos=total, confirmados=confirmed, corrigidos=corrected, removidos=removed, adicionados=added,
            pendentes_curadoria=pending, taxa_intervencao=rate, por_campo=metrics,
            motivos=[FeedbackReasonMetric(motivo_codigo=str(row["reason_code"]), quantidade=int(row["count"])) for row in reason_rows],
        )

    def create_dataset_snapshot(self, actor_hash: str) -> DatasetSnapshot:
        now = timestamp()
        with self.database.connection() as connection:
            rows = connection.execute("SELECT id,content_sha256 FROM training_examples ORDER BY id").fetchall()
            ids = [str(row["id"]) for row in rows]
            digest = hashlib.sha256("\n".join(f"{row['id']}:{row['content_sha256']}" for row in rows).encode()).hexdigest()
            existing = connection.execute("SELECT * FROM training_dataset_versions WHERE sha256=?", (digest,)).fetchone()
            if existing is None:
                identifier = f"ds_{uuid4().hex}"
                connection.execute(
                    "INSERT INTO training_dataset_versions(id,created_at,created_by_hash,sha256,example_count,example_ids) VALUES(?,?,?,?,?,?)",
                    (identifier, now, actor_hash, digest, len(ids), json.dumps(ids)),
                )
                row = connection.execute("SELECT * FROM training_dataset_versions WHERE id=?", (identifier,)).fetchone()
            else:
                row = existing
        return DatasetSnapshot(
            identificador=str(row["id"]), criado_em=str(row["created_at"]), criado_por=str(row["created_by_hash"]),
            sha256=str(row["sha256"]), quantidade_exemplos=int(row["example_count"]),
        )

    @staticmethod
    def _tokens(value: str) -> set[str]:
        return {item for item in re.findall(r"[a-zà-ÿ0-9]{3,}", value.lower()) if len(item) >= 3}

    def retrieve_examples(self, stage: str, context: str, limit: int) -> list[LearningExample]:
        """Recuperação lexical local: zero chamadas extras de IA e somente exemplos aprovados."""
        if limit <= 0:
            return []
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT field,task,evidence,model_value,expected_value,reason_code FROM training_examples WHERE task=? ORDER BY created_at DESC LIMIT 200",
                (stage,),
            ).fetchall()
        context_tokens = self._tokens(context)
        scored: list[tuple[float, object]] = []
        for row in rows:
            evidence = str(row["evidence"] or "")
            tokens = self._tokens(evidence)
            overlap = len(context_tokens & tokens) / max(1, len(tokens)) if tokens else 0.0
            # Recência continua como desempate; exemplos sem trecho podem ser úteis para regras recorrentes.
            scored.append((overlap, row))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            LearningExample(
                campo=str(row["field"]), tarefa=str(row["task"]), evidencia=row["evidence"],
                valor_modelo=_decode_scalar(row["model_value"]), valor_esperado=_decode_scalar(row["expected_value"]),
                motivo_codigo=str(row["reason_code"]),
            )
            for _, row in scored[:limit]
        ]
