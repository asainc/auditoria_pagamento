"""Testa o avaliador offline sem chamar provedor externo."""
from scripts.evaluate_extraction import evaluate


def test_exact_field_evaluator_reports_mismatches():
    gold = {
        "cases": [
            {"id": "a", "expected_fields": {"parametros.indice": "sem_correcao", "parametros.art_523": "nao_aplicar"}},
        ]
    }
    predictions = {
        "cases": [
            {"id": "a", "predicted_fields": {"parametros.indice": "sem_correcao", "parametros.art_523": "aplicar_multa"}},
        ]
    }
    result = evaluate(gold, predictions)
    assert result["fields_evaluated"] == 2
    assert result["exact_matches"] == 1
    assert result["exact_match_rate"] == 0.5
    assert result["mismatches"][0]["field"] == "parametros.art_523"
