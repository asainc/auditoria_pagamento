"""Regressões de aprendizado supervisionado e FinOps sem rede ou dados reais."""
from __future__ import annotations

import hashlib
from decimal import Decimal

from backend.config import Settings
from backend.contracts.quality import FeedbackCurationInput
from backend.persistence.schema import migrate, timestamp
from backend.persistence.sqlite import SQLiteDatabase
from backend.repositories.ai_operations_repository import AiOperationsRepository
from backend.repositories.quality_repository import QualityRepository
from backend.services.ai_usage import UsageMeter


def _database(tmp_path):
    database = SQLiteDatabase(tmp_path)
    migrate(database)
    return database


def test_feedback_curation_creates_only_approved_learning_example(tmp_path):
    database = _database(tmp_path)
    repository = QualityRepository(database)
    fingerprint = hashlib.sha256(b"synthetic-feedback").hexdigest()
    reviewer = hashlib.sha256(b"synthetic-reviewer").hexdigest()
    record, created = repository.add_feedback({
        "event_fingerprint": fingerprint,
        "process": "00000000000000000000",
        "draft": "draft-synthetic",
        "extraction_job": "job-synthetic",
        "field": "parametros.indice",
        "action": "corrected",
        "reason_code": "nao_informado",
        "model_value": '"igpm"',
        "human_value": '"ipca"',
        "document_name": "documento_sintetico.pdf",
        "page": 2,
        "model_evidence": "trecho sintético",
        "document_type": "acordao",
        "prompt_version": "synthetic-v1",
        "model_name": "modelo-corporativo",
        "pipeline_version": "test",
        "reviewer_hash": reviewer,
        "created_at": timestamp(),
        "curation_status": "pending",
    })
    assert created is True
    assert repository.retrieve_examples("02_correcao", "ipca", 3) == []

    approved = repository.curate(
        record.identificador,
        FeedbackCurationInput(status="approved", motivo_codigo="valor_interpretado_incorretamente"),
        reviewer,
    )
    assert approved is not None
    examples = repository.retrieve_examples("02_correcao", "ipca", 3)
    assert len(examples) == 1
    assert examples[0].valor_esperado == "ipca"

    snapshot = repository.create_dataset_snapshot(reviewer)
    assert snapshot.quantidade_exemplos == 1
    assert len(snapshot.sha256) == 64


def test_finops_keeps_cost_unavailable_when_tariff_is_incomplete(tmp_path):
    database = _database(tmp_path)
    repository = AiOperationsRepository(database)
    repository.record_usage({
        "job": "job-synthetic",
        "stage": "02_correcao_parte_1",
        "model": "modelo-corporativo",
        "request_sha256": hashlib.sha256(b"request").hexdigest(),
        "cache_hit": False,
        "success": True,
        "input_chars": 4000,
        "output_chars": 400,
        "input_tokens_estimated": 1000,
        "output_tokens_estimated": 100,
        "duration_ms": 10,
    })
    result = repository.summary(30, monthly_budget_usd=Decimal("100"))
    assert result.tokens_reais is None
    assert result.tokens_estimados == 1100
    assert result.custo_estimado_usd is None
    assert result.status_orcamento == "unavailable"
    assert result.percentual_orcamento is None


def test_usage_meter_uses_only_explicit_tariff_for_cost(tmp_path):
    settings = Settings(
        data_dir=tmp_path,
        ai_finops_input_usd_per_million_tokens=Decimal("1.00"),
        ai_finops_output_usd_per_million_tokens=Decimal("2.00"),
    )
    usage = UsageMeter.from_call(
        model="modelo-corporativo",
        stage="teste",
        duration_ms=1,
        input_chars=4000,
        output_chars=400,
        settings=settings,
    )
    assert usage.tokens_estimados_entrada == 1000
    assert usage.tokens_estimados_saida == 100
    assert usage.custo_estimado_usd == Decimal("0.001200")


def test_finops_counts_failures_separately(tmp_path):
    database = _database(tmp_path)
    repository = AiOperationsRepository(database)
    repository.record_usage({
        "job": "job-synthetic",
        "stage": "01_parcelas_parte_1",
        "model": "modelo-corporativo",
        "request_sha256": hashlib.sha256(b"failed-request").hexdigest(),
        "cache_hit": False,
        "success": False,
        "input_chars": 800,
        "output_chars": 0,
        "input_tokens_estimated": 200,
        "output_tokens_estimated": 0,
        "duration_ms": 20,
    })
    result = repository.summary(30)
    assert result.chamadas_api == 1
    assert result.falhas_api == 1
    assert result.por_etapa[0].falhas_api == 1
