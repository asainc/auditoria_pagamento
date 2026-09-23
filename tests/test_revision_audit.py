"""A trilha de revisão humana deve ser imutável e enriquecida pelo servidor."""
from __future__ import annotations

from backend.models import ChronologyDecision, ExtractionResult, ExtractionStatus
from backend.repository import timestamp


def test_manual_parameter_changes_are_persisted_in_order(client):
    first = {
        "origem_calculo": "manual",
        "numero_processo": None,
        "rascunho_id": "draft_manual_001",
        "campo": "art_523",
        "valor_anterior": "nao_aplicar",
        "valor_novo": "aplicar_multa",
        "extracao_id": None,
    }
    second = {**first, "valor_anterior": "aplicar_multa", "valor_novo": "nao_aplicar"}

    one = client.post("/api/auditoria/parametros", json=first)
    two = client.post("/api/auditoria/parametros", json=second)
    assert one.status_code == 200
    assert two.status_code == 200
    assert one.json()["identificador"] < two.json()["identificador"]
    assert one.json()["ator_tecnico"] == "local"

    listed = client.get("/api/auditoria/parametros", params={"rascunho_id": "draft_manual_001"})
    assert listed.status_code == 200
    assert [row["valor_novo"] for row in listed.json()] == ["aplicar_multa", "nao_aplicar"]


def test_process_change_is_enriched_with_consolidated_document_source(client):
    repository = client.app.state.services.repository
    status = ExtractionStatus(
        numero_processo="1001",
        identificador="job_audit_001",
        estado="pronto",
        etapa="concluido",
        mensagem="Extração sintética pronta.",
        atualizado_em=timestamp(),
    )
    repository.start_job(status)
    result = ExtractionResult(
        numero_processo="1001",
        campos=[],
        parcelas=[],
        alertas=[],
        versao_prompts="synthetic",
        parametros_consolidados={"art_523": "nao_aplicar"},
        decisoes_cronologicas=[
            ChronologyDecision(
                campo="parametros.art_523",
                valor="nao_aplicar",
                documento="1001_4.pdf",
                pagina=7,
                sequencia=4,
                natureza="comando_decisorio",
                efeito="informa",
                motivo="Comando sintético para teste.",
            )
        ],
    )
    repository.update_job(status, result)

    response = client.post("/api/auditoria/parametros", json={
        "origem_calculo": "processo",
        "numero_processo": "1001",
        "rascunho_id": "draft_process_001",
        "campo": "art_523",
        "valor_anterior": "nao_aplicar",
        "valor_novo": "aplicar_multa",
        "extracao_id": "job_audit_001",
    })
    assert response.status_code == 200
    body = response.json()
    assert body["valor_extraido"] == "nao_aplicar"
    assert "1001_4.pdf" in body["origem_extraida"]
    assert "página 7" in body["origem_extraida"]


def test_audit_query_requires_exactly_one_scope(client):
    assert client.get("/api/auditoria/parametros").status_code == 422
    assert client.get("/api/auditoria/parametros", params={"numero_processo": "1001", "rascunho_id": "draft_xxx"}).status_code == 422
