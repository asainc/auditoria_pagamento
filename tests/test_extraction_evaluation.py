"""Regressões determinísticas para cronologia e contratos dos prompts.

Esta suíte não mede acurácia do LLM. Ela verifica regras de consolidação que podem
ser avaliadas sem rede e impede que mudanças de prompt removam instruções críticas.
"""
from __future__ import annotations

import json
from pathlib import Path

from backend.models import FieldEvidence
from backend.services.chronology import ChronologyReducer

ROOT = Path(__file__).resolve().parents[1]


def evidence(
    value,
    document: str,
    *,
    nature: str = "comando_decisorio",
    effect: str = "informa",
    page: int = 1,
    field: str = "parametros.honorarios",
) -> FieldEvidence:
    """Cria evidência sintética sem dados pessoais para testes de regressão."""
    return FieldEvidence(
        campo=field,
        valor=value,
        documento=document,
        pagina=page,
        trecho="Trecho sintético para teste automatizado.",
        escopo="caso_concreto",
        natureza=nature,
        efeito=effect,
    )


def test_later_decision_can_increase_previous_value():
    values, decisions, alerts = ChronologyReducer().reduce([
        evidence("10", "123_2.pdf", effect="informa"),
        evidence("15", "123_5.pdf", effect="majora"),
    ])
    assert values["honorarios"] == "15"
    assert decisions[-1].sequencia == 5
    assert alerts == []


def test_maintaining_decision_preserves_previous_representable_value():
    values, _, alerts = ChronologyReducer().reduce([
        evidence("10", "123_2.pdf", effect="informa"),
        evidence(None, "123_5.pdf", effect="mantem"),
    ])
    assert values["honorarios"] == "10"
    assert alerts == []


def test_decision_has_precedence_over_incompatible_initial_request():
    values, _, alerts = ChronologyReducer().reduce([
        evidence("20", "123_1.pdf", nature="pedido", effect="informa"),
        evidence("10", "123_3.pdf", nature="comando_decisorio", effect="reduz"),
    ])
    assert values["honorarios"] == "10"
    assert alerts == []


def test_conflicting_commands_in_same_sequence_remain_for_human_review():
    values, _, alerts = ChronologyReducer().reduce([
        evidence("10", "123_4.pdf", page=3, effect="altera"),
        evidence("15", "123_4.pdf", page=8, effect="altera"),
    ])
    assert "honorarios" not in values
    assert any("revisão humana" in alert for alert in alerts)


def test_conflicting_facts_without_decision_are_not_resolved_by_recency():
    values, _, alerts = ChronologyReducer().reduce([
        evidence("100", "123_1.pdf", nature="fato", effect="informa", field="parametros.compensacao_valor"),
        evidence("120", "123_9.pdf", nature="fato", effect="informa", field="parametros.compensacao_valor"),
    ])
    assert "compensacao_valor" not in values
    assert any("Conflito documental" in alert for alert in alerts)


def test_prompt_base_requires_nature_effect_and_no_operational_defaults():
    base = (ROOT / "prompts" / "_base.md").read_text(encoding="utf-8")
    assert "natureza=comando_decisorio" in base
    assert "efeito=mantem" in base
    assert "Não aplique valores padrão" in base


def test_installment_prompt_covers_petition_narrative_and_table_values():
    prompt = (ROOT / "prompts" / "01_parcelas.md").read_text(encoding="utf-8")
    assert "petição inicial" in prompt
    assert "R$ 1.250,00" in prompt
    assert "Data | Histórico | Valor" in prompt
    assert "não crie parcela adicional para o total" in prompt


def test_explicit_removal_clears_previous_state_and_stays_auditable():
    values, decisions, alerts = ChronologyReducer().reduce([
        evidence("10", "123_2.pdf", effect="informa", field="parametros.compensacao_valor"),
        evidence(None, "123_7.pdf", effect="afasta", field="parametros.compensacao_valor"),
    ])
    assert "compensacao_valor" not in values
    assert decisions[-1].efeito == "afasta"
    assert decisions[-1].valor is None
    assert any("permanece sem preenchimento automático" in alert for alert in alerts)


def test_synthetic_chronology_fixture_is_stable():
    payload = json.loads((ROOT / "evals" / "extraction_gold.json").read_text(encoding="utf-8"))
    assert payload["version"] == 1
    for case in payload["cases"]:
        items = [FieldEvidence.model_validate(item) for item in case["evidences"]]
        values, _, alerts = ChronologyReducer().reduce(items)
        assert values == case["expected_parameters"], case["id"]
        for expected in case["expected_alert_substrings"]:
            assert any(expected in alert for alert in alerts), case["id"]
