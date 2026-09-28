"""Telemetria FinOps: separa métricas reais, estimativas locais e custo configurado."""
from __future__ import annotations

import math
from decimal import Decimal
from time import perf_counter

from backend.config import Settings
from backend.models import AiUsage


class UsageMeter:
    """Mede somente o que é observável e rotula explicitamente qualquer estimativa."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings

    @staticmethod
    def estimate_tokens(characters: int) -> int:
        """Heurística local para planejamento; não representa faturamento do gateway."""
        return max(0, math.ceil(max(0, characters) / 4))

    @staticmethod
    def _estimated_cost(
        settings: Settings | None,
        *,
        input_tokens: int,
        cached_input_tokens: int,
        output_tokens: int,
    ) -> Decimal | None:
        if settings is None:
            return None
        input_rate = settings.ai_finops_input_usd_per_million_tokens
        output_rate = settings.ai_finops_output_usd_per_million_tokens
        cached_rate = settings.ai_finops_cached_input_usd_per_million_tokens
        if input_rate is None or output_rate is None:
            return None
        paid_input = max(0, input_tokens - cached_input_tokens)
        # Só usamos tarifa própria de cache quando ela foi fornecida/verificada.
        # Sem ela, tokens cacheados são cobrados pela tarifa de entrada comum na estimativa,
        # evitando inventar um desconto não confirmado.
        cached_effective_rate = cached_rate if cached_rate is not None else input_rate
        million = Decimal(1_000_000)
        return (
            Decimal(paid_input) * input_rate / million
            + Decimal(cached_input_tokens) * cached_effective_rate / million
            + Decimal(output_tokens) * output_rate / million
        ).quantize(Decimal("0.000001"))

    @staticmethod
    def from_call(
        *,
        model: str,
        stage: str,
        duration_ms: float,
        input_chars: int = 0,
        output_chars: int = 0,
        input_tokens_actual: int | None = None,
        cached_input_tokens_actual: int | None = None,
        output_tokens_actual: int | None = None,
        cache_hit: bool = False,
        request_sha256: str | None = None,
        settings: Settings | None = None,
    ) -> AiUsage:
        estimated_input = UsageMeter.estimate_tokens(input_chars)
        estimated_output = UsageMeter.estimate_tokens(output_chars)
        if cache_hit:
            origin = "cache"
        elif input_tokens_actual is not None and output_tokens_actual is not None:
            origin = "gateway"
        else:
            origin = "estimativa_local"
        input_for_cost = input_tokens_actual if input_tokens_actual is not None else estimated_input
        output_for_cost = output_tokens_actual if output_tokens_actual is not None else estimated_output
        cached_for_cost = cached_input_tokens_actual or 0
        cost = None if cache_hit else UsageMeter._estimated_cost(
            settings,
            input_tokens=input_for_cost,
            cached_input_tokens=cached_for_cost,
            output_tokens=output_for_cost,
        )
        actual_total = None
        if input_tokens_actual is not None and output_tokens_actual is not None:
            actual_total = input_tokens_actual + output_tokens_actual
        return AiUsage(
            etapa=stage,
            modelo=model,
            tokens_entrada=input_tokens_actual,
            tokens_entrada_cache=cached_input_tokens_actual,
            tokens_saida=output_tokens_actual,
            tokens_total=actual_total,
            tokens_estimados_entrada=estimated_input,
            tokens_estimados_saida=estimated_output,
            origem_tokens=origin,
            custo_estimado_usd=cost,
            duracao_ms=round(duration_ms, 2),
            caracteres_entrada=input_chars,
            caracteres_saida=output_chars,
            cache_hit=cache_hit,
            request_sha256=request_sha256,
        )


class RequestTimer:
    """Cronômetro monotônico para medir somente latência técnica."""

    def __init__(self) -> None:
        self.started = perf_counter()

    def elapsed_ms(self) -> float:
        return (perf_counter() - self.started) * 1000
