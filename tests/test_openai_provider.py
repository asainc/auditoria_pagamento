"""SDK real com transporte HTTP simulado: nenhum documento sai do ambiente de testes."""
from __future__ import annotations

import json
import secrets
import time

import httpx2
import pytest
from fastapi.testclient import TestClient
from openai import OpenAI
from pydantic import SecretStr

from backend.config import Settings
from backend.principal import create_app
from backend.services.extraction import ExtractionProvider, ExtractionProviderError


def install_transport(monkeypatch, handler):
    """Mantém serialização, parsing Pydantic e erros do SDK usados em produção."""
    def factory(**options):
        return OpenAI(**options, http_client=httpx2.Client(transport=httpx2.MockTransport(handler)))
    monkeypatch.setattr("backend.services.extraction.OpenAI", factory)


def response(fragment, status="completed"):
    return {"id": "resp_synthetic", "object": "response", "created_at": 0, "status": status,
            "model": "gpt-5.6-sol", "output": [{"type": "message", "id": "msg_synthetic", "role": "assistant", "status": "completed", "content": [{"type": "output_text", "text": json.dumps(fragment), "annotations": []}]}]}


def test_sdk_receives_pdf_token_and_structured_schema(monkeypatch, pdf_bytes, tmp_path):
    token = secrets.token_urlsafe(32)
    settings = Settings(data_dir=tmp_path, openai_api_key=SecretStr(token))
    requests = []
    def handler(request):
        assert request.headers["authorization"] == "Bearer " + token
        body = json.loads(request.content)
        requests.append(body)
        return httpx2.Response(200, json=response({"campos": [], "parcelas": [], "eventos_financeiros": [], "alertas": []}))
    install_transport(monkeypatch, handler)
    result = ExtractionProvider(settings).extract("Extração sintética", [("1001_1.pdf", pdf_bytes)], stage="teste", max_output_tokens=8192)
    assert result.fragmento.parcelas == []
    body = requests[0]
    assert body["model"] == "gpt-5.6-sol"
    assert body["reasoning"] == {"effort": "medium"}
    assert body["store"] is False
    assert body["max_output_tokens"] == 8192
    assert body["input"][0]["content"][1]["file_data"].startswith("data:application/pdf;base64,JVBER")
    assert body["text"]["format"]["type"] == "json_schema"
    assert body["text"]["format"]["strict"] is True
    assert token not in json.dumps(body)


@pytest.mark.parametrize("http_status,code,expected", [
    (401, "invalid_api_key", "openai_token_invalido"),
    (403, "permission_denied", "openai_acesso_negado"),
    (404, "model_not_found", "openai_modelo_indisponivel"),
    (429, "insufficient_quota", "openai_quota_insuficiente"),
    (429, "rate_limit_exceeded", "openai_limite_requisicoes"),
    (400, "invalid_request_error", "openai_requisicao_rejeitada"),
    (503, "server_error", "openai_indisponivel"),
])
def test_provider_errors_are_actionable_and_do_not_echo_secrets(monkeypatch, http_status, code, expected, pdf_bytes):
    token = secrets.token_urlsafe(32)
    def handler(request):
        return httpx2.Response(http_status, headers={"x-should-retry": "false"}, json={"error": {"message": "Não ecoar " + token, "code": code, "type": code}})
    install_transport(monkeypatch, handler)
    with pytest.raises(ExtractionProviderError) as caught:
        ExtractionProvider(Settings(openai_api_key=SecretStr(token))).extract("Sintético", [("1001_1.pdf", pdf_bytes)], stage="teste", max_output_tokens=8192)
    assert caught.value.code == expected
    assert token not in str(caught.value)


@pytest.mark.parametrize("timeout,expected", [(False, "openai_conexao"), (True, "openai_tempo_esgotado")])
def test_provider_connection_is_distinct_from_local_api(monkeypatch, timeout, expected, pdf_bytes):
    def handler(request):
        error_type = httpx2.ReadTimeout if timeout else httpx2.ConnectError
        raise error_type("Falha sintética", request=request)
    install_transport(monkeypatch, handler)
    with pytest.raises(ExtractionProviderError) as caught:
        ExtractionProvider(Settings(openai_api_key=SecretStr(secrets.token_urlsafe(32)))).extract("Sintético", [("1001_1.pdf", pdf_bytes)], stage="teste", max_output_tokens=8192)
    assert caught.value.code == expected


def test_upload_reaches_real_sdk_and_preserves_bank_evidence(monkeypatch, tmp_path, pdf_bytes):
    calls = []
    def handler(request):
        body = json.loads(request.content)
        prompt = body["input"][0]["content"][0]["text"]
        calls.append(prompt)
        fragment = {"campos": [], "parcelas": [], "eventos_financeiros": [], "alertas": []}
        if "# Extraindo parcelas" in prompt:
            values = {"data": "2025-01-01", "valor_singelo": "100.00", "verba_tipo": "dano_material"}
            source = {"documento": "1001_1.pdf", "pagina": 1, "trecho": "Parcela: 100.00. Data: 2025-01-01. Tipo: dano_material.", "escopo": "caso_concreto", "natureza": "fato", "efeito": "informa"}
            fragment["parcelas"] = [{**values, "descricao": "Parcela sintética"}]
            fragment["campos"] = [{**source, "campo": "parcelas.0." + name, "valor": value} for name, value in values.items()]
        return httpx2.Response(200, json=response(fragment))
    install_transport(monkeypatch, handler)
    settings = Settings(data_dir=tmp_path, openai_api_key=SecretStr(secrets.token_urlsafe(32)))
    with TestClient(create_app(settings)) as client:
        uploaded = client.post("/api/documentos/upload", files=[("files", ("1001_1.pdf", pdf_bytes, "application/pdf"))])
        assert uploaded.status_code == 202
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            status = client.get("/api/extracoes/1001/status").json()
            if status["estado"] not in {"aguardando", "executando"}:
                break
            time.sleep(0.01)
        assert status["estado"] == "pronto", status
        assert len(calls) == 10
        result = client.get("/api/extracoes/1001/resultado").json()
        assert result["parcelas"][0]["valor_singelo"] == "100.00"
        assert result["parcelas"][0]["verba_tipo"] == "dano_material"
        assert result["campos"][0]["pagina"] == 1


def test_incomplete_output_is_not_returned_as_success(monkeypatch, pdf_bytes):
    install_transport(monkeypatch, lambda request: httpx2.Response(200, json=response({"campos": [], "parcelas": [], "eventos_financeiros": [], "alertas": []}, "incomplete")))
    with pytest.raises(ExtractionProviderError) as caught:
        ExtractionProvider(Settings(openai_api_key=SecretStr(secrets.token_urlsafe(32)))).extract("Sintético", [("1001_1.pdf", pdf_bytes)], stage="teste", max_output_tokens=8192)
    assert caught.value.code == "openai_resposta_incompleta"


def test_configuration_endpoint_never_returns_the_token(tmp_path):
    token = secrets.token_urlsafe(32)
    with TestClient(create_app(Settings(data_dir=tmp_path, openai_api_key=SecretStr(token)))) as client:
        result = client.get("/api/extracoes/configuracao")
        assert result.status_code == 200
        assert result.json()["configurada"] is True
        assert result.json()["modelo"] == "gpt-5.6-sol"
        assert token not in result.text


def test_token_failure_is_persisted_and_visible_without_losing_pdf(monkeypatch, tmp_path, pdf_bytes):
    token = secrets.token_urlsafe(32)
    install_transport(monkeypatch, lambda request: httpx2.Response(401, json={"error": {"message": token, "code": "invalid_api_key", "type": "invalid_request_error"}}))
    with TestClient(create_app(Settings(data_dir=tmp_path, openai_api_key=SecretStr(token)))) as client:
        upload = client.post("/api/documentos/upload", files=[("files", ("1001_1.pdf", pdf_bytes, "application/pdf"))])
        assert upload.status_code == 202
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            status = client.get("/api/extracoes/1001/status")
            if status.json()["estado"] == "falha":
                break
            time.sleep(0.01)
        assert status.json()["codigo_erro"] == "openai_token_invalido"
        assert "API_TOKEN" in status.json()["mensagem"]
        assert token not in status.text
        identifier = upload.json()["documentos"][0]["identificador"]
        assert client.get(f"/api/documentos/{identifier}/arquivo").content == pdf_bytes
        assert client.get("/api/extracoes/1001/resultado").status_code == 409
