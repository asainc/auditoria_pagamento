"""Regressão do contrato externo e validação interna após Structured Outputs."""
import json
import secrets
import httpx2
import pytest
from pydantic import SecretStr
from backend.config import Settings
from backend.services.extraction import ExtractionFragment, ExtractionProvider, ExtractionProviderError, ProviderResult
from tests.test_openai_provider import install_transport, response


def inspect_schema(node):
    """Esquema externo utiliza somente o subconjunto estrutural escolhido."""
    if isinstance(node, dict):
        assert not ({"default", "pattern", "format", "minimum", "maximum", "maxLength", "minLength", "allOf"} & node.keys())
        if node.get("type") == "object":
            assert node["additionalProperties"] is False
            assert set(node["required"]) == set(node["properties"])
        for value in node.values():
            inspect_schema(value)
    elif isinstance(node, list):
        for value in node:
            inspect_schema(value)


def test_actual_serialized_schema_has_no_defaults_or_decimal_regex(monkeypatch, pdf_bytes):
    def handler(request):
        schema = json.loads(request.content)["text"]["format"]["schema"]
        inspect_schema(schema)
        assert schema["$defs"]["WireInstallment"]["properties"]["valor_singelo"]["type"] == "string"
        return httpx2.Response(200, json=response({"campos": [], "parcelas": [], "eventos_financeiros": [], "alertas": []}))
    install_transport(monkeypatch, handler)
    result = ExtractionProvider(Settings(openai_api_key=SecretStr(secrets.token_urlsafe(32)))).extract("Sintético", [("1001_1.pdf", pdf_bytes)], stage="teste", max_output_tokens=8192)
    assert isinstance(result, ProviderResult)
    assert isinstance(result.fragmento, ExtractionFragment)


@pytest.mark.parametrize("date,value", [("2025-02-30", "1.00"), ("2025-01-01", "-1.00"), ("2025-01-01", "1.001"), ("2025-01-01", "99999999999999999.99")])
def test_simple_wire_schema_does_not_weaken_business_validation(monkeypatch, pdf_bytes, date, value):
    fragment = {"campos": [], "parcelas": [{"data": date, "valor_singelo": value, "descricao": "", "verba_tipo": "dano_material"}], "eventos_financeiros": [], "alertas": []}
    install_transport(monkeypatch, lambda request: httpx2.Response(200, json=response(fragment)))
    with pytest.raises(ExtractionProviderError) as caught:
        ExtractionProvider(Settings(openai_api_key=SecretStr(secrets.token_urlsafe(32)))).extract("Sintético", [("1001_1.pdf", pdf_bytes)], stage="teste", max_output_tokens=8192)
    assert caught.value.code == "openai_saida_invalida"


@pytest.mark.parametrize("code,param,message,expected", [
    ("invalid_json_schema", None, "", "openai_schema_rejeitado"),
    ("invalid_request_error", "text.format.schema", "", "openai_schema_rejeitado"),
    ("invalid_request_error", None, "Invalid schema for response_format", "openai_schema_rejeitado"),
    ("invalid_value", "reasoning.effort", "", "openai_raciocinio_incompativel"),
    ("invalid_value", "model", "", "openai_modelo_indisponivel"),
    ("context_length_exceeded", None, "", "openai_limite_contexto"),
    ("file_too_large", None, "", "openai_limite_contexto"),
    ("invalid_value", "max_output_tokens", "", "openai_limite_saida"),
    ("invalid_file", "input[0].content[1]", "", "openai_entrada_rejeitada"),
])
def test_bad_request_diagnostics_are_specific_and_private(monkeypatch, pdf_bytes, code, param, message, expected):
    secret = secrets.token_urlsafe(32)
    install_transport(monkeypatch, lambda request: httpx2.Response(400, headers={"x-request-id": "req_synthetic_schema"}, json={"error": {"message": message + secret, "code": code, "param": param, "type": "invalid_request_error"}}))
    with pytest.raises(ExtractionProviderError) as caught:
        ExtractionProvider(Settings(openai_api_key=SecretStr(secret))).extract("Sintético", [("1001_1.pdf", pdf_bytes)], stage="teste", max_output_tokens=8192)
    assert caught.value.code == expected
    assert "req_synthetic_schema" in str(caught.value)
    assert secret not in str(caught.value)
