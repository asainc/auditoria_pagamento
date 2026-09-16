"""Gates executáveis de arquitetura, integridade do motor e limites entre camadas."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from backend.config import ROOT
from scripts.validate_architecture import architecture_errors


def test_architecture_has_no_legacy_ui_or_dependency_conflict():
    assert architecture_errors(ROOT) == []


def test_guard_detects_reintroduced_import(tmp_path):
    (tmp_path / "bad.py").write_text("import streamlit as st\nst.session_state['x'] = 1\n")
    assert len(architecture_errors(tmp_path)) == 2


def test_engine_source_matches_integrity_manifest():
    """Compara os bytes do motor com o manifesto de integridade versionado no projeto."""
    manifest = json.loads((ROOT / "docs/motor_sha256.json").read_text())
    actual = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in (ROOT / "src").rglob("*.py")}
    assert actual == {name: value for name, value in manifest.items() if name.endswith(".py")}


def test_minimum_http_endpoints_are_documented():
    specification = json.loads((ROOT / "docs/openapi.json").read_text())
    expected = {
        "/api/saude": "get",
        "/api/documentos/upload": "post",
        "/api/documentos/processos": "get",
        "/api/documentos/processos/{numero_processo}": "get",
        "/api/documentos/{identificador_documento}/arquivo": "get",
        "/api/extracoes": "post",
        "/api/extracoes/{numero_processo}/status": "get",
        "/api/extracoes/{numero_processo}/resultado": "get",
        "/api/indices": "get",
        "/api/indices/status": "get",
        "/api/indices/atualizar": "post",
        "/api/calculos": "post",
        "/api/calculos/politica/{origem_calculo}": "get",
        "/api/calculos/memoria-pdf": "post",
        "/api/auditoria/parametros": "get",
        "/api/lotes/importar": "post",
        "/api/lotes/executar": "post",
    }
    for path, method in expected.items():
        assert method in specification["paths"][path]
    assert "post" in specification["paths"]["/api/auditoria/parametros"]


def test_python_dependency_versions_are_pinned():
    lines = (ROOT / "requirements.lock").read_text().splitlines()
    assert lines and all("==" in line for line in lines if line and not line.startswith("#"))


def test_legacy_ai_package_was_removed():
    """A extração web usa uma única implementação em ``backend/services``."""
    assert not (ROOT / "src/judicial_calc/ai").exists()


def test_legacy_engine_batch_service_was_removed():
    """O lote web possui uma única implementação na camada de aplicação."""
    assert not (ROOT / "src/judicial_calc/services/batch.py").exists()
