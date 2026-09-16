"""Compara o contrato Angular -> API -> fachada com o motor real e sem rede."""
from __future__ import annotations

import copy
import io
from decimal import Decimal

import pytest
from pypdf import PdfReader

from judicial_calc import calcular_debitos
from backend.services.engine import dataframe_table


def test_angular_payload_runs_real_engine(client, payload):
    response = client.post("/api/calculos", json=payload)
    assert response.status_code == 200
    body = response.json()
    expected = calcular_debitos([dict(item=index, **row) for index, row in enumerate(payload["parcelas"], 1)], **payload["parametros"], eventos_financeiros=[], auto_atualizar_planilhas_indices=False)
    assert body["memoria"] == dataframe_table(expected.memoria).model_dump()
    assert {row["campo"]: row["valor"] for row in body["resumo"]}["total_geral"] == "1234.56"
    assert body["metadata"]["revisao_humana_confirmada"] is True
    assert len(body["metadata"]["entrada_sha256"]) == 64
    assert len(body["metadata"]["politica_sha256"]) == 64
    assert len(body["metadata"]["motor_sha256"]) == 64
    assert len(body["metadata"]["indices_sha256"]) == 64


@pytest.mark.parametrize("changes", [
    {"juros_moratorios_tipo": "capitalizacao_simples", "juros_moratorios_taxa": "1", "juros_moratorios_periodicidade": "mensal"},
    {"juros_compensatorios_tipo": "capitalizacao_composta", "juros_compensatorios_taxa": "0.5", "juros_compensatorios_periodicidade": "mensal"},
    {"compensacao_flag": True, "compensacao_tipo_calculo": "fixo", "compensacao_valor": "100"},
    {"compensacao_flag": True, "compensacao_tipo_calculo": "percentual", "compensacao_valor": "10"},
    {"prescricao_flag": True, "prescricao_anos": 5, "prescricao_data_referencia_tipo": "data_decisao", "prescricao_data_referencia": "2026-01-01"},
    {"multa_percentual": "2", "honorarios": "10", "honorarios_tipo": "percentual", "art_523": "aplicar_multa_honorarios"},
    {"duplo_indice_flag": True, "duplo_indice_primeiro_indice": "sem_correcao", "duplo_indice_primeiro_data_inicio": "2024-01-01", "duplo_indice_primeiro_data_fim": "2025-01-31", "duplo_indice_segundo_indice": "sem_correcao", "duplo_indice_segundo_data_inicio": "2025-02-01", "duplo_indice_segundo_data_fim": "2026-03-31"},
])
def test_facade_matches_direct_engine_calculation(client, payload, changes):
    """Compara a resposta HTTP com a execução direta do mesmo motor e dos mesmos parâmetros."""
    payload["parametros"].update(changes)
    payload["parcelas"].append({"data": "2025-03-01", "valor_singelo": "350.00", "descricao": "Parcela sintética moral", "verba_tipo": "dano_moral"})
    response = client.post("/api/calculos", json=payload)
    assert response.status_code == 200, response.text
    expected = calcular_debitos([dict(item=index, **row) for index, row in enumerate(payload["parcelas"], 1)], **payload["parametros"], auto_atualizar_planilhas_indices=False, eventos_financeiros=[])
    assert response.json()["memoria"] == dataframe_table(expected.memoria).model_dump()
    assert response.json()["resumo"] == [{"campo": str(row["campo"]), "valor": str(row["valor"])} for row in expected.resumo.to_dict("records")]


def test_financial_event_reaches_engine(client, payload):
    payload["eventos_financeiros"] = [{"tipo": "pagamento_parcial", "data": "2025-04-01", "valor": "234.56", "criterio": "descontar_no_final"}]
    response = client.post("/api/calculos", json=payload)
    assert response.status_code == 200
    totals = {row["campo"]: row["valor"] for row in response.json()["resumo"]}
    assert totals["total_apos_eventos_financeiros"] == "1000.00"


@pytest.mark.parametrize("audit", [False, True])
def test_pdf_is_valid_and_matches_confirmed_total(client, payload, audit):
    calculated = client.post("/api/calculos", json=payload).json()
    response = client.post("/api/calculos/memoria-pdf", params={"auditavel": str(audit).lower(), "indices_sha256": calculated["metadata"]["indices_sha256"]}, json=payload)
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")
    reader = PdfReader(io.BytesIO(response.content))
    assert len(reader.pages) >= 1
    assert "1.234,56" in " ".join(page.extract_text() for page in reader.pages)


def test_pdf_refuses_changed_index_snapshot(client, payload):
    response = client.post("/api/calculos/memoria-pdf?indices_sha256=divergente", json=payload)
    assert response.status_code == 409


@pytest.mark.parametrize("change", [
    {"revisao_humana_confirmada": False},
    {"revisao_humana_confirmada": None},
    {"parcelas": []},
    {"campo_desconhecido": True},
])
def test_invalid_request_is_rejected(client, payload, change):
    payload.update(change)
    assert client.post("/api/calculos", json=payload).status_code == 422


@pytest.mark.parametrize("value", ["-1.00", "NaN", "Infinity", "123.456", "1,20"])
def test_invalid_money_is_rejected_at_boundary(client, payload, value):
    payload["parcelas"][0]["valor_singelo"] = value
    response = client.post("/api/calculos", json=payload)
    assert response.status_code == 422
    assert '"input"' not in response.text


def test_required_interest_and_active_fields(client, payload):
    payload["parametros"]["juros_moratorios_tipo"] = "capitalizacao_simples"
    assert client.post("/api/calculos", json=payload).status_code == 422
    payload["parametros"]["juros_moratorios_tipo"] = "sem_juros"
    payload["parametros"]["compensacao_flag"] = True
    assert client.post("/api/calculos", json=payload).status_code == 422


def test_health_and_versioned_alias(client):
    assert client.get("/api/saude").status_code == 200
    response = client.get("/api/v1/saude")
    assert response.status_code == 200
    assert response.headers["x-api-version"] == "1"


def test_input_hash_changes_when_calculation_input_changes(client, payload):
    """O hash de entrada identifica exatamente o request aceito sem armazenar seu conteúdo."""
    first = client.post("/api/calculos", json=payload)
    assert first.status_code == 200
    modified = copy.deepcopy(payload)
    modified["parcelas"][0]["valor_singelo"] = "1234.57"
    second = client.post("/api/calculos", json=modified)
    assert second.status_code == 200
    assert first.json()["metadata"]["entrada_sha256"] != second.json()["metadata"]["entrada_sha256"]
    assert first.json()["metadata"]["politica_sha256"] == second.json()["metadata"]["politica_sha256"]


def test_policy_endpoint_exposes_defaults_by_origin(client):
    manual = client.get("/api/calculos/politica/manual")
    process = client.get("/api/calculos/politica/processo")
    assert manual.status_code == process.status_code == 200
    assert manual.json()["parametros_padrao"]["juros_moratorios_tipo"] == "sem_juros"
    assert process.json()["parametros_padrao"]["juros_moratorios_tipo"] == "taxa_legal_12_aa_6_aa"
