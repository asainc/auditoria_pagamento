"""Valida compatibilidade com contratos antigos e novos de gpt_bradesco.py sem rede."""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path

from backend.config import Settings
from backend.services.bradesco_bridge import BradescoBridgeClient


def _settings() -> Settings:
    return Settings(bradesco_ocr_container="container-sintetico", bradesco_text_model="gpt-5.1")


def test_hybrid_contract_does_not_require_optional_helpers(monkeypatch):
    """A versão mostrada pelo usuário pode expor só upload, OCR híbrido e text_generator."""
    calls: list[str] = []
    module = types.ModuleType("gpt_bradesco")

    def file_manager_upload_base64(payload):
        calls.append("file_manager_upload_base64")
        assert payload["base64"]
        return {"response": {"file_id": "file-synthetic"}}

    def ocr_hibrido(payload):
        calls.append("ocr_hibrido")
        assert payload["files_id"] == ["file-synthetic"]
        # Sem wait_for_workflow o adaptador pede retorno síncrono.
        assert payload["async_mode"] == "false"
        assert payload["workflow_configuration_code"] == "CD_WRFL_OCR_HYBRID_ASYNC"
        return {"pages": [{"page_number": 1, "text": "Multa: 2%."}]}

    def text_generator(payload, parameters):
        calls.append("text_generator")
        assert parameters["deployment_name"] == "gpt-5.1"
        assert parameters["message_format"] == {"type": "json_object"}
        return json.dumps({"campos": [], "parcelas": [], "eventos_financeiros": [], "alertas": []})

    module.file_manager_upload_base64 = file_manager_upload_base64
    module.ocr_hibrido = ocr_hibrido
    module.text_generator = text_generator
    monkeypatch.setitem(sys.modules, "gpt_bradesco", module)

    client = BradescoBridgeClient(_settings())
    assert client.configured
    document = client.ocr_pdf("1001_1.pdf", b"%PDF-synthetic", expected_pages=1)
    assert document.paginas[0].texto == "Multa: 2%."
    assert json.loads(client.generate_text("Prompt sintético", max_tokens=4096))["campos"] == []
    assert calls == ["file_manager_upload_base64", "ocr_hibrido", "text_generator"]


def test_legacy_contract_uses_local_upload_list_get_text_and_optional_delete(monkeypatch):
    """Compatibilidade com as assinaturas legadas exibidas nas primeiras imagens."""
    calls: list[str] = []
    module = types.ModuleType("gpt_bradesco")

    def file_manager_upload(path_file, file_name, container_name, create_container="false", overwrite="true"):
        calls.append("file_manager_upload")
        assert Path(path_file).is_file()
        assert container_name == "container-sintetico"
        assert overwrite == "false"
        module.remote_name = file_name
        return 200

    def file_manager_list_files(container_name):
        calls.append("file_manager_list_files")
        assert container_name == "container-sintetico"
        return {"files": [{"id": "legacy-id", "file_name": module.remote_name, "file_path": f"folder/{module.remote_name}"}]}

    def get_text_ocr(files_path, container, input_text):
        calls.append("get_text_ocr")
        assert files_path == [f"folder/{module.remote_name}"]
        assert container == "container-sintetico"
        assert "Extraia integralmente" in input_text
        return {"response": {"text": "Juros moratórios desde a citação."}}

    def file_manager_delete(file_id):
        calls.append("file_manager_delete")
        assert file_id == "legacy-id"
        return "200 Arquivo deletado com sucesso"

    def text_generator(payload, parameters):
        calls.append("text_generator")
        return json.dumps({"campos": [], "parcelas": [], "eventos_financeiros": [], "alertas": []})

    module.file_manager_upload = file_manager_upload
    module.file_manager_list_files = file_manager_list_files
    module.get_text_ocr = get_text_ocr
    module.file_manager_delete = file_manager_delete
    module.text_generator = text_generator
    monkeypatch.setitem(sys.modules, "gpt_bradesco", module)

    client = BradescoBridgeClient(_settings())
    document = client.ocr_pdf("1001_1.pdf", b"%PDF-synthetic", expected_pages=1)
    assert document.paginas[0].texto == "Juros moratórios desde a citação."
    assert calls == [
        "file_manager_upload",
        "file_manager_list_files",
        "get_text_ocr",
        "file_manager_delete",
    ]


def test_new_contract_can_configure_and_wait(monkeypatch):
    """Recursos adicionais continuam aproveitados quando existirem no módulo."""
    calls: list[str] = []
    module = types.ModuleType("gpt_bradesco")

    def configure_iagen(parameters):
        calls.append("configure_iagen")
        assert parameters["token"] == "synthetic-token"
        return parameters

    def file_manager_upload_base64(payload, parameters):
        calls.append("file_manager_upload_base64")
        return {"file_id": "file-new"}

    def ocr_hibrido(payload, parameters):
        calls.append("ocr_hibrido")
        assert payload["async_mode"] == "true"
        return {"workflow_execution_id": "wf-1", "status": "WF_RUNNING"}

    def wait_for_workflow(identifier, parameters):
        calls.append("wait_for_workflow")
        assert identifier == "wf-1"
        return {"pages": [{"page_number": 1, "text": "Texto final."}]}

    def file_manager_delete_file(payload, parameters):
        calls.append("file_manager_delete_file")
        return "ok"

    def text_generator(payload, parameters):
        calls.append("text_generator")
        return "{}"

    for name, value in list(locals().items()):
        if name not in {"module", "calls"} and callable(value):
            setattr(module, name, value)
    monkeypatch.setitem(sys.modules, "gpt_bradesco", module)

    settings = Settings(
        bradesco_authorization_token="synthetic-token",
        bradesco_ocr_container="container-sintetico",
        bradesco_text_model="gpt-5.1",
    )
    client = BradescoBridgeClient(settings)
    document = client.ocr_pdf("1001_1.pdf", b"%PDF-synthetic", expected_pages=1)
    assert document.paginas[0].texto == "Texto final."
    assert calls == [
        "configure_iagen",
        "file_manager_upload_base64",
        "ocr_hibrido",
        "wait_for_workflow",
        "file_manager_delete_file",
    ]
