"""Histórico avançado: versões de negócio, execuções, concorrência, filtros e comparação."""
from __future__ import annotations

import copy


def history_page(client, **params):
    response = client.get("/api/calculos/historico", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def versions_page(client, calculation_id: str, **params):
    response = client.get(f"/api/calculos/{calculation_id}/versoes", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_first_process_calculation_creates_version_one_and_execution(client, payload):
    response = client.post("/api/calculos", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    registration = body["registro"]
    execution = body["execucao"]
    assert registration["calculo_id"].startswith("calc_")
    assert registration["versao"] == 1
    assert registration["versao_base"] is None
    assert registration["criada"] is True
    assert execution["execucao_id"].startswith("exec_")
    assert execution["versao"] == 1
    assert execution["nova_versao"] is True

    history = history_page(client)
    assert history["total_itens"] == 1
    item = history["itens"][0]
    assert item["numero_processo"] == payload["numero_processo"]
    assert item["estado"] == "ativo"
    assert item["versao_atual"] == 1
    assert item["quantidade_versoes"] == 1
    assert item["quantidade_execucoes"] == 1
    assert "versoes" not in item  # lazy loading explícito


def test_parameter_change_creates_new_version_with_complete_diff(client, payload):
    first = client.post("/api/calculos", json=payload).json()
    calculation_id = first["registro"]["calculo_id"]

    second_payload = copy.deepcopy(payload)
    second_payload["parametros"]["multa_valor"] = "2"
    second_payload["parcelas"][0]["valor_singelo"] = "2000.00"
    second = client.post(
        "/api/calculos",
        params={"calculo_id": calculation_id, "versao_base": 1},
        json=second_payload,
    )
    assert second.status_code == 200, second.text
    assert second.json()["registro"]["versao"] == 2

    versions = versions_page(client, calculation_id)["itens"]
    assert [row["versao"] for row in versions] == [2, 1]
    current = versions[0]
    assert "parametros.multa_valor" in current["campos_alterados"]
    assert "parcelas" in current["campos_alterados"]
    field_diff = {row["caminho"]: row for row in current["diff"]["campos"]}
    assert field_diff["parametros.multa_valor"]["valor_anterior"] is None
    assert field_diff["parametros.multa_valor"]["valor_novo"] == "2"
    installment = current["diff"]["parcelas"][0]
    assert installment["acao"] == "alterada"
    assert "valor_singelo" in installment["campos_alterados"]
    assert installment["antes"]["valor_singelo"] == "1234.56"
    assert installment["depois"]["valor_singelo"] == "2000.00"


def test_historical_snapshot_is_immutable_and_can_be_reopened(client, payload):
    first = client.post("/api/calculos", json=payload).json()
    calculation_id = first["registro"]["calculo_id"]

    changed = copy.deepcopy(payload)
    changed["parcelas"][0]["valor_singelo"] = "2000.00"
    second = client.post(
        "/api/calculos",
        params={"calculo_id": calculation_id, "versao_base": 1},
        json=changed,
    )
    assert second.status_code == 200

    v1 = client.get(f"/api/calculos/{calculation_id}/versoes/1")
    v2 = client.get(f"/api/calculos/{calculation_id}/versoes/2")
    assert v1.status_code == v2.status_code == 200
    assert v1.json()["requisicao"]["parcelas"][0]["valor_singelo"] == "1234.56"
    assert v2.json()["requisicao"]["parcelas"][0]["valor_singelo"] == "2000.00"
    assert v1.json()["resultado"]["resumo"] != v2.json()["resultado"]["resumo"]

    normal_pdf = client.get(f"/api/calculos/{calculation_id}/versoes/1/memoria-pdf")
    legacy_audit_request = client.get(f"/api/calculos/{calculation_id}/versoes/1/memoria-pdf", params={"auditavel": "true"})
    assert normal_pdf.status_code == legacy_audit_request.status_code == 200
    assert normal_pdf.content.startswith(b"%PDF-")
    # Compatibilidade da tela Histórico: sem artefato auditável novo, a API devolve a mesma memória padrão.
    assert legacy_audit_request.content == normal_pdf.content


def test_any_historical_version_can_be_edited_with_current_version_token(client, payload):
    """Uma versão antiga pode originar uma nova versão sem perder o controle de concorrência."""
    first = client.post("/api/calculos", json=payload).json()
    calculation_id = first["registro"]["calculo_id"]

    v2_payload = copy.deepcopy(payload)
    v2_payload["parametros"]["multa_valor"] = "2"
    v2 = client.post(
        "/api/calculos",
        params={"calculo_id": calculation_id, "versao_base": 1},
        json=v2_payload,
    )
    assert v2.status_code == 200, v2.text
    assert v2.json()["registro"]["versao"] == 2

    detail_v1 = client.get(f"/api/calculos/{calculation_id}/versoes/1")
    assert detail_v1.status_code == 200, detail_v1.text
    assert detail_v1.json()["versao"] == 1
    assert detail_v1.json()["versao_atual"] == 2

    branched = copy.deepcopy(payload)
    branched["parametros"]["honorarios"] = "10"
    v3 = client.post(
        "/api/calculos",
        params={
            "calculo_id": calculation_id,
            "versao_base": 1,
            "versao_atual_esperada": 2,
        },
        json=branched,
    )
    assert v3.status_code == 200, v3.text
    body = v3.json()
    assert body["registro"]["versao"] == 3
    assert body["registro"]["versao_base"] == 1
    assert body["registro"]["criada"] is True

    versions = versions_page(client, calculation_id)["itens"]
    assert [row["versao"] for row in versions] == [3, 2, 1]


def test_historical_edit_rejects_when_current_version_changed_after_open(client, payload):
    first = client.post("/api/calculos", json=payload).json()
    calculation_id = first["registro"]["calculo_id"]

    v2_payload = copy.deepcopy(payload)
    v2_payload["parametros"]["multa_valor"] = "2"
    assert client.post(
        "/api/calculos",
        params={"calculo_id": calculation_id, "versao_base": 1},
        json=v2_payload,
    ).status_code == 200

    # A edição histórica foi aberta quando a versão atual era V2.
    v3_payload = copy.deepcopy(v2_payload)
    v3_payload["parametros"]["honorarios"] = "10"
    assert client.post(
        "/api/calculos",
        params={"calculo_id": calculation_id, "versao_base": 2},
        json=v3_payload,
    ).status_code == 200

    stale_branch = copy.deepcopy(payload)
    stale_branch["parametros"]["honorarios"] = "15"
    response = client.post(
        "/api/calculos",
        params={
            "calculo_id": calculation_id,
            "versao_base": 1,
            "versao_atual_esperada": 2,
        },
        json=stale_branch,
    )
    assert response.status_code == 409
    assert "V3" in response.json()["detail"]
    assert "V2" in response.json()["detail"]


def test_identical_retry_keeps_version_but_creates_new_execution(client, payload):
    first = client.post("/api/calculos", json=payload).json()
    calculation_id = first["registro"]["calculo_id"]
    first_execution = first["execucao"]["execucao_id"]
    retry = client.post(
        "/api/calculos",
        params={"calculo_id": calculation_id, "versao_base": 1},
        json=payload,
    )
    assert retry.status_code == 200, retry.text
    body = retry.json()
    assert body["registro"]["versao"] == 1
    assert body["registro"]["criada"] is False
    assert body["execucao"]["execucao_id"] != first_execution
    assert body["execucao"]["nova_versao"] is False

    history = history_page(client)["itens"][0]
    assert history["quantidade_versoes"] == 1
    assert history["quantidade_execucoes"] == 2
    versions = versions_page(client, calculation_id)["itens"]
    assert versions[0]["quantidade_execucoes"] == 2
    executions = client.get(f"/api/calculos/{calculation_id}/versoes/1/execucoes")
    assert executions.status_code == 200
    assert executions.json()["total_itens"] == 2
    assert len(executions.json()["itens"]) == 2

    execution_pdf = client.get(f"/api/calculos/{calculation_id}/execucoes/{body['execucao']['execucao_id']}/memoria-pdf")
    assert execution_pdf.status_code == 200
    assert execution_pdf.content.startswith(b"%PDF-")


def test_same_process_reuses_registered_calculation_after_new_session_state(client, payload):
    first = client.post("/api/calculos", json=payload).json()
    changed = copy.deepcopy(payload)
    changed["parametros"]["ano_atualizacao"] = 2025
    second = client.post("/api/calculos", json=changed)
    assert second.status_code == 200, second.text
    assert second.json()["registro"]["calculo_id"] == first["registro"]["calculo_id"]
    assert second.json()["registro"]["versao"] == 2


def test_history_is_ordered_by_process_number(client, payload):
    for process in ("20", "3", "100"):
        item = copy.deepcopy(payload)
        item["numero_processo"] = process
        response = client.post("/api/calculos", json=item)
        assert response.status_code == 200, response.text
    history = history_page(client, tamanho_pagina=10)
    assert [item["numero_processo"] for item in history["itens"]] == ["3", "20", "100"]


def test_process_number_is_normalized_and_does_not_duplicate_history(client, payload):
    formatted = copy.deepcopy(payload)
    formatted["numero_processo"] = "1234567-89.2026.8.26.0001"
    first = client.post("/api/calculos", json=formatted)
    assert first.status_code == 200, first.text

    unformatted = copy.deepcopy(payload)
    unformatted["numero_processo"] = "12345678920268260001"
    second = client.post("/api/calculos", json=unformatted)
    assert second.status_code == 200, second.text
    assert second.json()["registro"]["calculo_id"] == first.json()["registro"]["calculo_id"]
    assert second.json()["registro"]["versao"] == 1
    assert second.json()["registro"]["criada"] is False

    history = history_page(client)
    assert history["total_itens"] == 1
    assert history["itens"][0]["numero_processo"] == "1234567-89.2026.8.26.0001"
    assert history["itens"][0]["numero_processo_normalizado"] == "12345678920268260001"


def test_optimistic_concurrency_rejects_stale_edit(client, payload):
    first = client.post("/api/calculos", json=payload).json()
    calculation_id = first["registro"]["calculo_id"]

    change_a = copy.deepcopy(payload)
    change_a["parametros"]["multa_valor"] = "2"
    saved = client.post(
        "/api/calculos",
        params={"calculo_id": calculation_id, "versao_base": 1},
        json=change_a,
    )
    assert saved.status_code == 200
    assert saved.json()["registro"]["versao"] == 2

    change_b = copy.deepcopy(payload)
    change_b["parametros"]["honorarios"] = "10"
    stale = client.post(
        "/api/calculos",
        params={"calculo_id": calculation_id, "versao_base": 1},
        json=change_b,
    )
    assert stale.status_code == 409
    assert "V2" in stale.json()["detail"]
    assert "V1" in stale.json()["detail"]
    assert versions_page(client, calculation_id)["total_itens"] == 2


def test_comparator_returns_full_diff_and_financial_impact(client, payload):
    first = client.post("/api/calculos", json=payload).json()
    calculation_id = first["registro"]["calculo_id"]
    changed = copy.deepcopy(payload)
    changed["parcelas"][0]["valor_singelo"] = "1500.00"
    second = client.post(
        "/api/calculos",
        params={"calculo_id": calculation_id, "versao_base": 1},
        json=changed,
    )
    assert second.status_code == 200

    comparison = client.get(
        f"/api/calculos/{calculation_id}/comparar",
        params={"versao_origem": 1, "versao_destino": 2},
    )
    assert comparison.status_code == 200, comparison.text
    body = comparison.json()
    assert body["versao_origem"] == 1
    assert body["versao_destino"] == 2
    assert body["total_origem"] != body["total_destino"]
    assert body["diferenca_total"] is not None
    assert body["diff"]["parcelas"][0]["antes"]["valor_singelo"] == "1234.56"
    assert body["diff"]["parcelas"][0]["depois"]["valor_singelo"] == "1500.00"


def test_state_archives_without_deleting_history_and_blocks_execution_until_reactivated(client, payload):
    first = client.post("/api/calculos", json=payload).json()
    calculation_id = first["registro"]["calculo_id"]

    archived = client.post(f"/api/calculos/{calculation_id}/estado", json={"estado": "arquivado"})
    assert archived.status_code == 200
    assert archived.json()["estado"] == "arquivado"

    changed = copy.deepcopy(payload)
    changed["parametros"]["multa_valor"] = "2"
    blocked = client.post(
        "/api/calculos",
        params={"calculo_id": calculation_id, "versao_base": 1},
        json=changed,
    )
    assert blocked.status_code == 409
    assert "arquivado" in blocked.json()["detail"].lower()

    filtered = history_page(client, estado="arquivado")
    assert filtered["total_itens"] == 1
    assert filtered["itens"][0]["estado"] == "arquivado"

    active = client.post(f"/api/calculos/{calculation_id}/estado", json={"estado": "ativo"})
    assert active.status_code == 200
    saved = client.post(
        "/api/calculos",
        params={"calculo_id": calculation_id, "versao_base": 1},
        json=changed,
    )
    assert saved.status_code == 200
    assert saved.json()["registro"]["versao"] == 2


def test_backend_pagination_search_and_advanced_filters(client, payload):
    for process in ("1", "2", "3", "4", "5"):
        item = copy.deepcopy(payload)
        item["numero_processo"] = process
        assert client.post("/api/calculos", json=item).status_code == 200

    first_page = history_page(client, pagina=1, tamanho_pagina=2)
    second_page = history_page(client, pagina=2, tamanho_pagina=2)
    assert first_page["total_itens"] == 5
    assert first_page["total_paginas"] == 3
    assert [row["numero_processo"] for row in first_page["itens"]] == ["1", "2"]
    assert [row["numero_processo"] for row in second_page["itens"]] == ["3", "4"]

    search = history_page(client, busca="4")
    assert search["total_itens"] == 1
    assert search["itens"][0]["numero_processo"] == "4"

    filtered = history_page(client, origem="processo", estado="ativo", indice="sem_correcao", criado_por="local")
    assert filtered["total_itens"] == 5


def test_calculation_id_cannot_be_reused_for_another_process(client, payload):
    first = client.post("/api/calculos", json=payload).json()
    other = copy.deepcopy(payload)
    other["numero_processo"] = "2002"
    response = client.post(
        "/api/calculos",
        params={"calculo_id": first["registro"]["calculo_id"], "versao_base": 1},
        json=other,
    )
    assert response.status_code == 409


def test_manual_calculation_requires_business_identifier_and_is_saved_automatically(client, payload):
    manual = copy.deepcopy(payload)
    manual["origem_calculo"] = "manual"
    manual["numero_processo"] = None
    manual.pop("identificador_calculo", None)

    missing = client.post("/api/calculos", json=manual)
    assert missing.status_code == 422

    manual["identificador_calculo"] = "MANUAL-1001"
    first = client.post("/api/calculos", json=manual)
    assert first.status_code == 200, first.text
    assert first.json()["registro"]["versao"] == 1

    history = history_page(client)
    assert history["total_itens"] == 1
    item = history["itens"][0]
    assert item["origem_calculo"] == "manual"
    assert item["identificador_calculo"] == "MANUAL-1001"
    assert item["numero_processo"] is None


def test_manual_identifier_is_case_insensitive_for_business_identity(client, payload):
    manual = copy.deepcopy(payload)
    manual["origem_calculo"] = "manual"
    manual["numero_processo"] = None
    manual["identificador_calculo"] = "manual-a"
    first = client.post("/api/calculos", json=manual).json()

    manual["identificador_calculo"] = "MANUAL-A"
    second = client.post("/api/calculos", json=manual)
    assert second.status_code == 200
    assert second.json()["registro"]["calculo_id"] == first["registro"]["calculo_id"]
    assert history_page(client)["total_itens"] == 1


def test_manual_new_identifier_creates_an_independent_calculation(client, payload):
    first = copy.deepcopy(payload)
    first["origem_calculo"] = "manual"
    first["numero_processo"] = None
    first["identificador_calculo"] = "MANUAL-A"
    first_result = client.post("/api/calculos", json=first)
    assert first_result.status_code == 200, first_result.text

    second = copy.deepcopy(first)
    second["identificador_calculo"] = "MANUAL-B"
    second_result = client.post("/api/calculos", json=second)
    assert second_result.status_code == 200, second_result.text

    assert first_result.json()["registro"]["calculo_id"] != second_result.json()["registro"]["calculo_id"]
    history = history_page(client)
    assert [item["identificador_calculo"] for item in history["itens"]] == ["MANUAL-A", "MANUAL-B"]


def test_two_users_editing_same_base_cannot_create_silent_parallel_versions(tmp_path, payload):
    """Duas instâncias concorrentes: uma salva V2 e a outra recebe conflito da V1 obsoleta."""
    from concurrent.futures import ThreadPoolExecutor

    from fastapi.testclient import TestClient

    from backend.config import Settings
    from backend.principal import create_app

    app_a = create_app(Settings(data_dir=tmp_path))
    app_b = create_app(Settings(data_dir=tmp_path))
    with TestClient(app_a) as client_a, TestClient(app_b) as client_b:
        first = client_a.post("/api/calculos", json=payload)
        assert first.status_code == 200, first.text
        calculation_id = first.json()["registro"]["calculo_id"]

        change_a = copy.deepcopy(payload)
        change_a["parametros"]["multa_valor"] = "2"
        change_b = copy.deepcopy(payload)
        change_b["parametros"]["honorarios"] = "10"

        def save(client, body):
            return client.post(
                "/api/calculos",
                params={"calculo_id": calculation_id, "versao_base": 1},
                json=body,
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(lambda args: save(*args), [(client_a, change_a), (client_b, change_b)]))

        assert sorted(response.status_code for response in responses) == [200, 409]
        conflict = next(response for response in responses if response.status_code == 409)
        assert "Conflito de versão" in conflict.json()["detail"]
        versions = client_a.get(f"/api/calculos/{calculation_id}/versoes").json()
        assert versions["total_itens"] == 2
        assert [item["versao"] for item in versions["itens"]] == [2, 1]


def test_version_execution_artifact_storage_is_normalized_and_immutable(client, payload):
    """Versão guarda estado de negócio; execução guarda resultado; artefatos guardam PDFs."""
    import sqlite3

    created = client.post("/api/v2/calculos", json=payload)
    assert created.status_code == 200, created.text
    calculation_id = created.json()["registro"]["calculo_id"]
    execution_id = created.json()["execucao"]["execucao_id"]

    database = client.app.state.services.database
    with database.connection() as connection:
        version_columns = {row[1] for row in connection.execute("PRAGMA table_info(calculation_versions)").fetchall()}
        execution_columns = {row[1] for row in connection.execute("PRAGMA table_info(calculation_executions)").fetchall()}
        artifact_columns = {row[1] for row in connection.execute("PRAGMA table_info(calculation_artifacts)").fetchall()}
        assert {"response", "pdf", "audit_pdf"}.isdisjoint(version_columns)
        assert {"pdf", "audit_pdf"}.isdisjoint(execution_columns)
        assert {"execution_id", "kind", "sha256", "content"}.issubset(artifact_columns)
        assert connection.execute(
            "SELECT COUNT(*) FROM calculation_versions WHERE calculation_id=?", (calculation_id,)
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM calculation_executions WHERE calculation_id=?", (calculation_id,)
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM calculation_artifacts WHERE execution_id=?", (execution_id,)
        ).fetchone()[0] == 1

        with __import__('pytest').raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "UPDATE calculation_versions SET total='0' WHERE calculation_id=? AND version=1", (calculation_id,)
            )
        with __import__('pytest').raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute("DELETE FROM calculation_executions WHERE id=?", (execution_id,))


def test_execution_endpoint_is_paginated(client, payload):
    """Uma versão muito reexecutada não é carregada integralmente pelo histórico."""
    first = client.post("/api/v2/calculos", json=payload)
    assert first.status_code == 200, first.text
    calculation_id = first.json()["registro"]["calculo_id"]
    for _ in range(4):
        retry = client.post(
            "/api/v2/calculos",
            params={"calculo_id": calculation_id, "versao_base": 1},
            json=payload,
        )
        assert retry.status_code == 200, retry.text

    page1 = client.get(
        f"/api/v2/calculos/{calculation_id}/versoes/1/execucoes",
        params={"pagina": 1, "tamanho_pagina": 2},
    )
    page2 = client.get(
        f"/api/v2/calculos/{calculation_id}/versoes/1/execucoes",
        params={"pagina": 2, "tamanho_pagina": 2},
    )
    assert page1.status_code == page2.status_code == 200
    assert page1.json()["total_itens"] == 5
    assert page1.json()["total_paginas"] == 3
    assert len(page1.json()["itens"]) == len(page2.json()["itens"]) == 2
    assert {row["execucao_id"] for row in page1.json()["itens"]}.isdisjoint(
        {row["execucao_id"] for row in page2.json()["itens"]}
    )
