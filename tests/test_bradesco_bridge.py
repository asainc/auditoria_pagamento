"""Valida a integração corporativa com dublês, sem autenticação nem rede real."""
from __future__ import annotations

import json
import sys
import types

from backend.config import Settings
from backend.services.bradesco_bridge import BradescoBridgeClient


def fake_module(calls: list[str]):
    module = types.ModuleType("gpt_bradesco")

    def configure_iagen(parameters):
        calls.append("configure_iagen")
        return {"ambiente": parameters["ambiente"]}

    def file_manager_upload_base64(payload, parameters):
        calls.append("file_manager_upload_base64")
        assert payload["base64"]
        assert parameters["ambiente"] == "dev"
        return {"response": {"file_id": "file-synthetic"}}

    def file_manager_list(payload, parameters):
        calls.append("file_manager_list")
        return {"response": []}

    def ocr_hibrido(payload, parameters):
        calls.append("ocr_hibrido")
        assert payload["workflow_configuration_code"] == "CD_WRFL_OCR_HYBRID_ASYNC"
        assert payload["detailed_output"] is True
        assert payload["async_mode"] is True
        assert payload["figure_settings"]["vision_model"] == "gpt-4o"
        assert payload["table_settings"]["language_model"] == "gpt-4o"
        assert payload["document_settings"]["locale"] == "pt-BR"
        return {"workflow_execution_id": "wf-synthetic", "status": "WF_RUNNING"}

    def wait_for_workflow(identifier, parameters):
        calls.append("wait_for_workflow")
        assert identifier == "wf-synthetic"
        detailed = {"pages": [{"page_number": 1, "text": "Multa: 2%."}]}
        return {
            "status": "WF_COMPLETED_SUCCESS",
            "output_collection": {
                "output_datas": [
                    {
                        "workflow_step_output_collection": {
                            "output": {"json_data": {"output_text": json.dumps(detailed)}}
                        }
                    }
                ]
            },
        }

    def file_manager_delete_file(payload, parameters):
        calls.append("file_manager_delete_file")
        assert payload["file_id"] == "file-synthetic"
        return "ok"

    def text_generator(payload, parameters):
        calls.append("text_generator")
        assert parameters["deployment_name"] == "gpt-5.1"
        assert parameters["message_format"] == {"type": "json_object"}
        return json.dumps({"campos": [], "parcelas": [], "eventos_financeiros": [], "alertas": []})

    for name, function in locals().copy().items():
        if callable(function) and name not in {"fake_module"}:
            setattr(module, name, function)
    return module


def test_ocr_and_text_use_only_corporate_module(monkeypatch):
    calls: list[str] = []
    monkeypatch.setitem(sys.modules, "gpt_bradesco", fake_module(calls))
    settings = Settings(
        bradesco_authorization_token="synthetic-token",
        bradesco_ocr_container="container-sintetico",
    )
    client = BradescoBridgeClient(settings)
    assert client.configured
    document = client.ocr_pdf("1001_1.pdf", b"%PDF-synthetic", expected_pages=1)
    assert document.paginas[0].texto == "Multa: 2%."
    output = client.generate_text("Prompt sintético", max_tokens=4096)
    assert json.loads(output)["campos"] == []
    assert calls == [
        "configure_iagen",
        "file_manager_upload_base64",
        "ocr_hibrido",
        "wait_for_workflow",
        "file_manager_delete_file",
        "text_generator",
    ]
