"""Endpoints de qualidade supervisionada e FinOps da extração."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from backend.access import technical_actor
from backend.container import Services, services
from backend.contracts.quality import (
    DatasetSnapshot,
    FeedbackCurationInput,
    FeedbackEventRecord,
    FeedbackPage,
    FinOpsSummary,
    QualitySummary,
    ReviewCaptureResult,
    ReviewSnapshotInput,
)

router = APIRouter(prefix="/qualidade", tags=["Qualidade IA"])
Dependency = Annotated[Services, Depends(services)]


@router.post("/revisoes", response_model=ReviewCaptureResult)
def capture_review(payload: ReviewSnapshotInput, request: Request, service: Dependency):
    """Registra IA × humano sem sobrescrever a predição original."""
    return service.quality.capture_review(payload, technical_actor(request))


@router.get("/resumo", response_model=QualitySummary)
def quality_summary(service: Dependency):
    return service.quality.summary()


@router.get("/feedback", response_model=FeedbackPage)
def feedback_page(
    service: Dependency,
    pagina: int = Query(default=1, ge=1),
    tamanho: int = Query(default=25, ge=1, le=100),
    status: str | None = Query(default="pending"),
    campo: str | None = Query(default=None),
):
    return service.quality.feedback_page(pagina, tamanho, status, campo)


@router.post("/feedback/{feedback_id}/curadoria", response_model=FeedbackEventRecord)
def curate_feedback(feedback_id: str, payload: FeedbackCurationInput, request: Request, service: Dependency):
    return service.quality.curate(feedback_id, payload, technical_actor(request))


@router.post("/datasets/snapshot", response_model=DatasetSnapshot)
def snapshot_dataset(request: Request, service: Dependency):
    """Congela IDs/hashes dos exemplos aprovados; não duplica conteúdo documental."""
    return service.quality.snapshot_dataset(technical_actor(request))


@router.get("/finops", response_model=FinOpsSummary)
def finops(service: Dependency, dias: int = Query(default=30, ge=1, le=365)):
    return service.ai_operations_repository.summary(
        dias,
        monthly_budget_usd=service.settings.ai_finops_monthly_budget_usd,
        budget_warning_ratio=service.settings.ai_finops_budget_warning_ratio,
    )
