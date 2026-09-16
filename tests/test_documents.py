"""Verifica upload, associação, autorização e recuperação sem dados reais."""
from __future__ import annotations

import hashlib
import io

import pytest
from pypdf import PdfWriter
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.config import Settings
from backend.principal import create_app


def test_upload_starts_extraction_and_serves_pdf(client, pdf_bytes):
    response = client.post("/api/documentos/upload", files=[("files", ("1001_1.pdf", pdf_bytes, "application/pdf"))])
    assert response.status_code == 202
    body = response.json()
    assert body["extracoes"][0]["estado"] == "bloqueada"
    document = body["documentos"][0]
    assert document["sha256"] == hashlib.sha256(pdf_bytes).hexdigest()
    assert len(document["identificador"]) == 32
    file = client.get(f"/api/documentos/{document['identificador']}/arquivo")
    assert file.status_code == 200 and file.content == pdf_bytes
    assert file.headers["cache-control"] == "no-store"
    assert client.get("/api/extracoes/1001/status").json()["estado"] == "bloqueada"
    assert client.get("/api/extracoes/1001/resultado").status_code == 409


def test_processes_stay_separate_and_duplicate_upload_is_idempotent(client, pdf_bytes):
    files = [("files", (name, pdf_bytes, "application/pdf")) for name in ("1001_1.pdf", "2002_1.pdf")]
    first = client.post("/api/documentos/upload", files=files)
    second = client.post("/api/documentos/upload", files=files)
    assert first.status_code == second.status_code == 202
    assert first.json()["documentos"] == second.json()["documentos"]
    assert len(client.get("/api/documentos/processos").json()) == 2
    assert [row["numero_processo"] for row in client.get("/api/documentos/processos/1001").json()] == ["1001"]


@pytest.mark.parametrize("name,media", [("../../1001_1.pdf", "application/pdf"), ("documento.pdf", "application/pdf"), ("1001_1.exe", "application/pdf"), ("1001_1.pdf", "text/html")])
def test_invalid_name_or_type_does_not_persist(client, pdf_bytes, name, media):
    response = client.post("/api/documentos/upload", files=[("files", (name, pdf_bytes, media))])
    assert response.status_code == 422
    assert client.get("/api/documentos/processos").json() == []


def test_invalid_pdf_and_mixed_invalid_batch_do_not_persist(client, pdf_bytes):
    files = [("files", ("1001_1.pdf", pdf_bytes, "application/pdf")), ("files", ("1001_2.pdf", b"%PDF-invalid", "application/pdf"))]
    assert client.post("/api/documentos/upload", files=files).status_code == 422
    assert client.get("/api/documentos/processos").json() == []


def test_changed_content_requires_new_sequence(client, pdf_bytes):
    client.post("/api/documentos/upload", files=[("files", ("1001_1.pdf", pdf_bytes, "application/pdf"))])
    changed = pdf_bytes + b"\n%another-version"
    response = client.post("/api/documentos/upload", files=[("files", ("1001_1.pdf", changed, "application/pdf"))])
    assert response.status_code == 409


def test_upload_size_limit(tmp_path, pdf_bytes):
    with TestClient(create_app(Settings(data_dir=tmp_path, max_upload_bytes=1024))) as client:
        assert len(pdf_bytes) > 1024
        assert client.post("/api/documentos/upload", files=[("files", ("1001_1.pdf", pdf_bytes, "application/pdf"))]).status_code == 413


def test_unknown_document_is_not_a_filesystem_path(client):
    assert client.get("/api/documentos/not-a-document/arquivo").status_code == 404


def test_cors_is_explicit(client):
    allowed = client.options("/api/saude", headers={"Origin": "http://localhost:4200", "Access-Control-Request-Method": "GET"})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:4200"
    refused = client.options("/api/saude", headers={"Origin": "https://untrusted.invalid", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in refused.headers
    with pytest.raises(ValidationError):
        Settings(cors_origins=["*"])


def test_production_gateway_is_required(tmp_path):
    with pytest.raises(ValidationError):
        Settings(environment="production")
    # Valor sintético gerado só para o teste; não é uma credencial real.
    import secrets
    token = secrets.token_urlsafe(32)
    settings = Settings(data_dir=tmp_path, environment="production", gateway_token=token)
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/documentos/processos").status_code == 403
        assert client.get("/api/documentos/processos", headers={"X-Gateway-Token": token}).status_code == 200
