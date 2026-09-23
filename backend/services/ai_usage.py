"""Telemetria de chamadas corporativas sem estimar consumo não informado."""
from __future__ import annotations

from time import perf_counter

from backend.models import AiUsage


class UsageMeter:
    """Cria telemetria conservadora a partir dos dados realmente observáveis.

    O ``text_generator`` corporativo retorna o texto final, mas não expõe neste
    contrato os contadores de tokens nem cobrança. Por isso esses campos ficam
    nulos em vez de serem estimados ou inventados.
    """

    @staticmethod
    def from_call(*, model: str, stage: str, duration_ms: float) -> AiUsage:
        return AiUsage(
            etapa=stage,
            modelo=model,
            tokens_entrada=None,
            tokens_entrada_cache=None,
            tokens_saida=None,
            tokens_total=None,
            custo_estimado_usd=None,
            duracao_ms=round(duration_ms, 2),
        )


class RequestTimer:
    """Cronômetro monotônico para medir somente latência técnica."""

    def __init__(self) -> None:
        self.started = perf_counter()

    def elapsed_ms(self) -> float:
        return (perf_counter() - self.started) * 1000
