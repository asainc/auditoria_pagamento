"""Valida cálculo de custo sem realizar chamadas de rede ou usar dados reais."""
from decimal import Decimal

from backend.services.token_usage import PricingCatalog


def test_known_model_cost_separates_cached_input():
    catalog = PricingCatalog()
    cost = catalog.estimate(model="gpt-5.6-sol", input_tokens=1_000_000, cached_tokens=500_000, output_tokens=100_000)
    # 500k entrada normal = US$2; 500k cache = US$0,20; 100k saída = US$2.
    assert cost == Decimal("4.200000")


def test_unknown_model_never_invents_price():
    catalog = PricingCatalog()
    assert catalog.estimate(model="modelo-nao-catalogado", input_tokens=100, cached_tokens=0, output_tokens=10) is None
