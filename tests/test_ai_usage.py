"""Telemetria não inventa tokens ou custo ausentes do contrato corporativo."""
from backend.services.ai_usage import UsageMeter


def test_corporate_usage_keeps_unavailable_metrics_null():
    usage = UsageMeter.from_call(model="modelo-corporativo", stage="teste", duration_ms=12.34)
    assert usage.tokens_total is None
    assert usage.custo_estimado_usd is None
    assert usage.duracao_ms == 12.34
