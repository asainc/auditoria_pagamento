"""Transforma revisão humana em supervisão estruturada, curada e versionável."""
from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation

from backend.config import Settings
from backend.contracts.quality import (
    DatasetSnapshot,
    FeedbackCurationInput,
    FeedbackEventRecord,
    FeedbackPage,
    QualitySummary,
    ReviewCaptureResult,
    ReviewSnapshotInput,
)
from backend.errors import ServiceError
from backend.persistence.schema import timestamp
from backend.repositories.document_repository import DocumentRepository
from backend.repositories.extraction_repository import ExtractionRepository
from backend.repositories.quality_repository import QualityRepository
from backend.version import APP_VERSION


class QualityLearningService:
    """Mantém prediction e revisão separadas; nunca sobrescreve a saída original da IA."""

    def __init__(
        self,
        settings: Settings,
        repository: QualityRepository,
        extraction_repository: ExtractionRepository,
        document_repository: DocumentRepository,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.extractions = extraction_repository
        self.documents = document_repository

    @staticmethod
    def _reviewer_hash(actor: str) -> str:
        # A tabela analítica não recebe e-mail/nome; o evento operacional de auditoria
        # continua separado. O hash serve para análises de consistência sem expor identidade.
        return hashlib.sha256(("judicial-feedback-v1|" + actor).encode("utf-8")).hexdigest()

    @staticmethod
    def _json_value(value: object) -> str | None:
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)

    @staticmethod
    def _equivalent(left: object, right: object) -> bool:
        if left is None and right in (None, ""):
            return True
        if right is None and left in (None, ""):
            return True
        if isinstance(left, bool) or isinstance(right, bool):
            return left is right
        try:
            if left not in (None, "") and right not in (None, ""):
                return Decimal(str(left).replace(",", ".")) == Decimal(str(right).replace(",", "."))
        except (InvalidOperation, ValueError):
            pass
        return str(left).strip() == str(right).strip()

    @staticmethod
    def _action(model_value: object, human_value: object) -> tuple[str, str]:
        model_missing = model_value in (None, "")
        human_missing = human_value in (None, "")
        if model_missing and not human_missing:
            return "added", "adicao_manual"
        if not model_missing and human_missing:
            return "removed", "nao_informado"
        if QualityLearningService._equivalent(model_value, human_value):
            return "confirmed", "confirmado_sem_alteracao"
        return "corrected", "nao_informado"

    @staticmethod
    def _evidence(result, path: str):
        decision = next((item for item in reversed(result.decisoes_cronologicas or []) if item.campo == path), None)
        if decision is not None:
            return decision.documento, decision.pagina, decision.motivo
        field = next((item for item in reversed(result.campos) if item.campo == path and item.escopo == "caso_concreto"), None)
        if field is not None:
            return field.documento, field.pagina, field.trecho
        return None, None, None

    def capture_review(self, snapshot: ReviewSnapshotInput, actor: str) -> ReviewCaptureResult:
        """Compara o snapshot humano com a predição persistida no backend."""
        if snapshot.origem_calculo != "processo" or not snapshot.numero_processo or not snapshot.extracao_id:
            return ReviewCaptureResult(eventos_criados=0, confirmados=0, corrigidos=0, pendentes_curadoria=0)
        result = self.extractions.result(snapshot.numero_processo)
        status = self.extractions.status(snapshot.numero_processo)
        if result is None or status is None or status.identificador != snapshot.extracao_id:
            raise ServiceError(
                "A extração mudou durante a revisão. Recarregue os dados antes de confirmar para preservar a trilha de aprendizado.",
                409,
                code="FEEDBACK_EXTRACTION_CHANGED",
            )
        documents = {item.nome: item for item in self.documents.list_for_process(snapshot.numero_processo)}
        actor_hash = self._reviewer_hash(actor)
        now = timestamp()
        created = confirmed = corrected = pending = 0

        parameter_paths = {
            item.campo for item in result.campos if item.campo.startswith(("parametros.", "parametros_por_dano."))
        } | {
            item.campo for item in (result.decisoes_cronologicas or []) if item.campo.startswith(("parametros.", "parametros_por_dano."))
        }
        for key in result.parametros_consolidados:
            if key.startswith(("dano_material.", "dano_moral.")):
                damage, field = key.split(".", 1)
                parameter_paths.add(f"parametros_por_dano.{damage}.{field}")
            else:
                parameter_paths.add(f"parametros.{key}")

        for path in sorted(parameter_paths):
            if path.startswith("parametros_por_dano."):
                _, damage, key = path.split(".", 2)
                consolidated_key = f"{damage}.{key}"
                human_value = snapshot.parametros_por_dano.get(damage, {}).get(key)
            else:
                key = path.removeprefix("parametros.")
                consolidated_key = key
                human_value = snapshot.parametros.get(key)
            model_value = result.parametros_consolidados.get(consolidated_key)
            if model_value is None:
                decision = next((item for item in reversed(result.decisoes_cronologicas or []) if item.campo == path), None)
                if decision is not None:
                    model_value = decision.valor
                else:
                    evidence = next((item for item in reversed(result.campos) if item.campo == path and item.valor is not None), None)
                    model_value = evidence.valor if evidence else None
            action, reason = self._action(model_value, human_value)
            document_name, page, evidence_text = self._evidence(result, path)
            document_type = documents.get(document_name).classificacao if document_name in documents else None
            fingerprint = hashlib.sha256(
                "|".join([
                    snapshot.extracao_id or "", path, action,
                    self._json_value(model_value) or "null", self._json_value(human_value) or "null", APP_VERSION,
                ]).encode("utf-8")
            ).hexdigest()
            _, was_created = self.repository.add_feedback({
                "event_fingerprint": fingerprint,
                "process": snapshot.numero_processo,
                "draft": snapshot.rascunho_id,
                "extraction_job": snapshot.extracao_id,
                "field": path,
                "action": action,
                "reason_code": reason,
                "model_value": self._json_value(model_value),
                "human_value": self._json_value(human_value),
                "document_name": document_name,
                "page": page,
                "model_evidence": evidence_text,
                "document_type": document_type,
                "prompt_version": result.versao_prompts,
                "model_name": self.settings.bradesco_text_model,
                "pipeline_version": APP_VERSION,
                "reviewer_hash": actor_hash,
                "created_at": now,
                "curation_status": "approved" if action == "confirmed" else "pending",
            })
            if was_created:
                created += 1
                confirmed += int(action == "confirmed")
                corrected += int(action in {"corrected", "removed", "added"})
                pending += int(action != "confirmed")

        model_rows = result.parcelas
        human_rows = snapshot.parcelas
        installment_fields = ("data", "valor_singelo", "descricao", "verba_tipo", "multiplicador")
        for index in range(max(len(model_rows), len(human_rows))):
            model_row = model_rows[index] if index < len(model_rows) else None
            human_row = human_rows[index] if index < len(human_rows) else None
            for field in installment_fields:
                path = f"parcelas.{index}.{field}"
                model_value = getattr(model_row, field, None) if model_row is not None else None
                human_value = getattr(human_row, field, None) if human_row is not None else None
                if model_row is None and human_row is None:
                    continue
                action, reason = self._action(model_value, human_value)
                # Campos vazios em ambos não geram exemplos sem conteúdo.
                if action == "confirmed" and model_value in (None, ""):
                    continue
                document_name, page, evidence_text = self._evidence(result, path)
                document_type = documents.get(document_name).classificacao if document_name in documents else None
                fingerprint = hashlib.sha256(
                    "|".join([
                        snapshot.extracao_id or "", path, action,
                        self._json_value(model_value) or "null", self._json_value(human_value) or "null", APP_VERSION,
                    ]).encode("utf-8")
                ).hexdigest()
                _, was_created = self.repository.add_feedback({
                    "event_fingerprint": fingerprint,
                    "process": snapshot.numero_processo,
                    "draft": snapshot.rascunho_id,
                    "extraction_job": snapshot.extracao_id,
                    "field": path,
                    "action": action,
                    "reason_code": reason,
                    "model_value": self._json_value(model_value),
                    "human_value": self._json_value(human_value),
                    "document_name": document_name,
                    "page": page,
                    "model_evidence": evidence_text,
                    "document_type": document_type,
                    "prompt_version": result.versao_prompts,
                    "model_name": self.settings.bradesco_text_model,
                    "pipeline_version": APP_VERSION,
                    "reviewer_hash": actor_hash,
                    "created_at": now,
                    "curation_status": "approved" if action == "confirmed" else "pending",
                })
                if was_created:
                    created += 1
                    confirmed += int(action == "confirmed")
                    corrected += int(action in {"corrected", "removed", "added"})
                    pending += int(action != "confirmed")
        return ReviewCaptureResult(eventos_criados=created, confirmados=confirmed, corrigidos=corrected, pendentes_curadoria=pending)

    def summary(self) -> QualitySummary:
        return self.repository.summary()

    def feedback_page(self, page: int, page_size: int, status: str | None, field: str | None) -> FeedbackPage:
        return self.repository.page(page=page, page_size=page_size, status=status, field=field)

    def curate(self, feedback_id: str, payload: FeedbackCurationInput, actor: str) -> FeedbackEventRecord:
        row = self.repository.curate(feedback_id, payload, self._reviewer_hash(actor))
        if row is None:
            raise ServiceError("Feedback não encontrado.", 404, code="FEEDBACK_NOT_FOUND")
        return row

    def snapshot_dataset(self, actor: str) -> DatasetSnapshot:
        return self.repository.create_dataset_snapshot(self._reviewer_hash(actor))
