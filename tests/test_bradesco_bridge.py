"""Valida que a calculadora depende apenas de ``text_generator`` do módulo corporativo."""
from __future__ import annotations

import json
import sys
import types

from backend.config import Settings
from backend.services.bradesco_bridge import BradescoBridgeClient, BradescoBridgeError


def _settings(**values) -> Settings:
    return Settings(bradesco_text_model="gpt-5.1", **values)


def test_only_text_generator_is_required(monkeypatch):
    """OCR e File Manager não fazem parte do contrato mínimo da calculadora."""
    calls: list[tuple[str, object]] = []
    module = types.ModuleType("gpt_bradesco")

    def text_generator(payload, parameters):
        calls.append((payload, parameters))
        assert parameters["deployment_name"] == "gpt-5.1"
        assert parameters["message_format"] == {"type": "text"}
        assert set(parameters) == {
            "deployment_name", "temperature", "max_tokens",
            "async_mode", "stream", "message_format",
        }
        return json.dumps({"campos": [], "parcelas": [], "alertas": []})

    module.text_generator = text_generator
    monkeypatch.setitem(sys.modules, "gpt_bradesco", module)

    client = BradescoBridgeClient(_settings())
    assert client.configured
    response = client.generate_text("Prompt + texto do PDF", max_tokens=4096)
    assert json.loads(response)["campos"] == []
    assert len(calls) == 1


def test_optional_configuration_is_used_when_available(monkeypatch):
    """Versões com ``configure_iagen`` continuam suportadas sem torná-la obrigatória."""
    calls: list[str] = []
    module = types.ModuleType("gpt_bradesco")

    def configure_iagen(parameters):
        calls.append("configure_iagen")
        assert parameters["token"] == "synthetic-token"
        return parameters

    def text_generator(payload, parameters):
        calls.append("text_generator")
        return "{}"

    module.configure_iagen = configure_iagen
    module.text_generator = text_generator
    monkeypatch.setitem(sys.modules, "gpt_bradesco", module)

    client = BradescoBridgeClient(_settings(bradesco_authorization_token="synthetic-token"))
    assert client.generate_text("Prompt sintético", max_tokens=1024) == "{}"
    assert calls == ["configure_iagen", "text_generator"]


def test_legacy_text_generator_receives_only_common_parameters(monkeypatch):
    """O bridge não envia parâmetros novos a uma implementação corporativa legada."""
    module = types.ModuleType("gpt_bradesco")

    def text_generator(payload, parameters):
        allowed = {
            "deployment_name", "temperature", "max_tokens",
            "async_mode", "stream", "message_format",
        }
        assert set(parameters) == allowed
        assert parameters["message_format"] == {"type": "text"}
        return json.dumps({"campos": [], "parcelas": [], "alertas": []})

    module.text_generator = text_generator
    monkeypatch.setitem(sys.modules, "gpt_bradesco", module)
    client = BradescoBridgeClient(_settings())
    assert client.generate_text("Prompt", max_tokens=2048).startswith("{")


def test_http_400_from_legacy_module_is_classified_without_response_body(monkeypatch):
    """Erros legados em texto expõem somente o código HTTP ao diagnóstico público."""
    module = types.ModuleType("gpt_bradesco")

    def text_generator(payload, parameters):
        raise Exception("Erro na execução: 400 - resposta interna que não deve aparecer")

    module.text_generator = text_generator
    monkeypatch.setitem(sys.modules, "gpt_bradesco", module)
    client = BradescoBridgeClient(_settings())
    try:
        client.generate_text("Prompt", max_tokens=2048)
    except BradescoBridgeError as exc:
        assert exc.code == "bradesco_requisicao_rejeitada"
        assert "HTTP 400" in exc.message
        assert "resposta interna" not in exc.message
    else:
        raise AssertionError("Era esperado BradescoBridgeError")
