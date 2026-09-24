"""Regressões específicas da refatoração arquitetural de 2026-09-24."""
from __future__ import annotations

from decimal import Decimal

from backend.contracts.calculation import CalculationParameters
from backend.domain.calculation_parameters import normalize_parameters
from backend.version import API_CONTRACT_VERSION


def _parameters(**overrides):
    base = {
        "mes_atualizacao": "janeiro",
        "ano_atualizacao": 2026,
        "indice": "sem_correcao",
        "juros_compensatorios_tipo": "sem_juros",
        "juros_moratorios_tipo": "sem_juros",
    }
    base.update(overrides)
    return CalculationParameters.model_validate(base)


def test_amount_rules_distinguish_percentage_from_fixed_money():
    percentage = normalize_parameters(_parameters(multa_tipo="percentual", multa_valor="2"))
    fixed = normalize_parameters(_parameters(multa_tipo="fixo", multa_valor="500.00"))

    assert percentage.multa is not None
    assert percentage.multa.tipo == "percentual"
    assert percentage.multa.percentual == Decimal("2")
    assert percentage.multa.valor_fixo is None

    assert fixed.multa is not None
    assert fixed.multa.tipo == "fixo"
    assert fixed.multa.valor_fixo == Decimal("500.00")
    assert fixed.multa.percentual is None


def test_structured_error_and_canonical_api_version(client):
    response = client.get("/api/v2/calculos/calc_0123456789abcdef0123456789abcdef/versoes/1")
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "CALCULATION_VERSION_NOT_FOUND"
    assert body["message"]
    assert body["fields"] == []
    assert body["retryable"] is False
    assert body["request_id"] == response.headers["x-request-id"]
    assert response.headers["x-api-version"] == API_CONTRACT_VERSION == "2.0.0"


def test_openapi_exposes_v2_as_canonical_and_hides_legacy_aliases(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v2/saude" in paths
    assert "/api/saude" not in paths
    assert "/api/v1/saude" not in paths
    assert client.get("/api/saude").status_code == 200
    assert client.get("/api/v1/saude").status_code == 200
