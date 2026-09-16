"""Compara predições de extração com um conjunto de referência revisado.

O script não chama provedor externo e não envia documentos pela rede. Ele calcula
somente correspondência exata por campo a partir de dois JSONs previamente gerados.
Uma métrica produzida aqui só é significativa quando os rótulos de referência foram
validados pelo time jurídico responsável pelo caso de uso.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _case_map(payload: dict[str, Any], field_name: str) -> dict[str, dict[str, Any]]:
    """Indexa casos por identificador e valida a presença do objeto de campos."""
    result: dict[str, dict[str, Any]] = {}
    for case in payload.get("cases", []):
        identifier = str(case.get("id", "")).strip()
        fields = case.get(field_name)
        if not identifier or not isinstance(fields, dict):
            raise ValueError(f"Cada caso deve conter id e {field_name} como objeto.")
        result[identifier] = fields
    return result


def evaluate(gold: dict[str, Any], predictions: dict[str, Any]) -> dict[str, Any]:
    """Calcula acerto exato por campo e lista divergências sem ocultá-las em média."""
    expected = _case_map(gold, "expected_fields")
    predicted = _case_map(predictions, "predicted_fields")
    total = correct = 0
    mismatches: list[dict[str, Any]] = []
    for case_id, fields in expected.items():
        actual = predicted.get(case_id, {})
        for key, value in fields.items():
            total += 1
            if actual.get(key) == value:
                correct += 1
            else:
                mismatches.append({"case": case_id, "field": key, "expected": value, "predicted": actual.get(key)})
    return {
        "fields_evaluated": total,
        "exact_matches": correct,
        "exact_match_rate": (correct / total) if total else None,
        "mismatches": mismatches,
    }


def main() -> int:
    """Lê arquivos informados em CLI e imprime relatório JSON reproduzível."""
    parser = argparse.ArgumentParser(description="Avalia campos extraídos contra referência revisada.")
    parser.add_argument("--gold", required=True, type=Path)
    parser.add_argument("--predictions", required=True, type=Path)
    args = parser.parse_args()
    gold = json.loads(args.gold.read_text(encoding="utf-8"))
    predictions = json.loads(args.predictions.read_text(encoding="utf-8"))
    print(json.dumps(evaluate(gold, predictions), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
