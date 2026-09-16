"""Protege a refatoração estrutural do motor contra alteração numérica acidental.

Os cenários foram congelados antes da separação dos módulos de parâmetros.
Qualquer mudança futura nas fórmulas deve atualizar estes resultados somente
após validação explícita da regra de negócio.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import json
from pathlib import Path
from typing import Any

from judicial_calc import calcular_debitos

FIXTURE = Path(__file__).parent / "fixtures" / "golden_calculations.json"


def _normalize(value: Any) -> Any:
    """Converte tipos financeiros/data para uma representação JSON determinística."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    try:
        if value != value:
            return None
    except Exception:
        pass
    return str(value)


def _frame_records(frame) -> list[dict[str, Any]]:
    """Serializa um DataFrame preservando a ordem de linhas e colunas do motor."""
    return [{str(key): _normalize(value) for key, value in row.items()} for row in frame.to_dict("records")]


def test_engine_matches_golden_master_after_structural_refactor():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert fixture["version"] == 1

    for scenario in fixture["scenarios"]:
        result = calcular_debitos(scenario["parcelas"], **scenario["params"])
        actual = {
            "memoria": _frame_records(result.memoria),
            "resumo": _frame_records(result.resumo),
        }
        assert actual == scenario["expected"], scenario["name"]
