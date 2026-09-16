"""Mede consumo e custo de IA sem persistir conteúdo documental ou segredos."""
from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from time import perf_counter

from backend.config import ROOT
from backend.models import AiUsage


@dataclass(frozen=True)
class ModelPrice:
    """Tarifas em USD por unidade de tokens definida no catálogo externo."""
    input: Decimal
    cached_input: Decimal
    output: Decimal


class PricingCatalog:
    """Carrega preços versionáveis; modelo desconhecido nunca recebe preço presumido."""

    def __init__(self, path: Path | None = None):
        """Lê uma única fonte local para manter cálculo de custo reproduzível."""
        self.path = path or ROOT / "config/model_pricing.json"
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        self.currency = str(payload["currency"])
        self.unit_tokens = int(payload["unit_tokens"])
        self.verified_at = str(payload["verified_at"])
        self.source = str(payload["source"])
        self.models = {
            name: ModelPrice(Decimal(str(values["input"])), Decimal(str(values["cached_input"])), Decimal(str(values["output"])))
            for name, values in payload["models"].items()
        }

    def estimate(self, *, model: str, input_tokens: int, cached_tokens: int, output_tokens: int) -> Decimal | None:
        """Calcula custo apenas para modelos presentes no catálogo verificado."""
        price = self.models.get(model)
        if price is None:
            return None
        uncached = max(0, input_tokens - cached_tokens)
        cost = (
            Decimal(uncached) * price.input
            + Decimal(cached_tokens) * price.cached_input
            + Decimal(output_tokens) * price.output
        ) / Decimal(self.unit_tokens)
        return cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


class UsageMeter:
    """Converte o objeto ``usage`` da SDK em contrato estável do projeto."""

    def __init__(self, catalog: PricingCatalog | None = None):
        self.catalog = catalog or PricingCatalog()

    def from_response(self, *, response: object, model: str, stage: str, duration_ms: float) -> AiUsage:
        """Tolera evolução da SDK usando apenas campos de uso conhecidos e opcionais."""
        usage = getattr(response, "usage", None)
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        details = getattr(usage, "input_tokens_details", None)
        cached_tokens = int(getattr(details, "cached_tokens", 0) or 0)
        total_tokens = int(getattr(usage, "total_tokens", input_tokens + output_tokens) or input_tokens + output_tokens)
        cost = self.catalog.estimate(model=model, input_tokens=input_tokens, cached_tokens=cached_tokens, output_tokens=output_tokens)
        return AiUsage(
            etapa=stage,
            modelo=model,
            tokens_entrada=input_tokens,
            tokens_entrada_cache=cached_tokens,
            tokens_saida=output_tokens,
            tokens_total=total_tokens,
            custo_estimado_usd=cost,
            duracao_ms=round(duration_ms, 2),
        )


class RequestTimer:
    """Cronômetro pequeno para não espalhar medição de latência pelo provedor."""

    def __init__(self):
        self.started = perf_counter()

    def elapsed_ms(self) -> float:
        return (perf_counter() - self.started) * 1000
