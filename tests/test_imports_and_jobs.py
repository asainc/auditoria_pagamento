"""Importações, recuperação e revisões concorrentes são validadas sem rede."""
from __future__ import annotations

import io
import json

from openpyxl import Workbook
from backend.models import DocumentMetadata, ExtractionStatus
from backend.persistence.schema import migrate, timestamp
from backend.persistence.sqlite import SQLiteDatabase
from backend.repositories.document_repository import DocumentRepository
from backend.repositories.extraction_repository import ExtractionRepository


def _stores(tmp_path):
    """Cria somente os repositórios usados pelos testes de documentos e extração."""
    database = SQLiteDatabase(tmp_path)
    migrate(database)
    documents = DocumentRepository(database)
    extractions = ExtractionRepository(database, documents)
    return database, documents, extractions


def test_excel_and_csv_import_use_canonical_dates_and_money(client):
    book = Workbook()
    book.active.append(["data", "valor_singelo", "descricao", "verba_tipo"])
    book.active.append(["2025-02-03", "1.234,56", "Linha sintética", "dano_moral"])
    content = io.BytesIO()
    book.save(content)
    response = client.post("/api/documentos/parcelas/importar?verba_tipo=dano_material", files={"file": ("parcelas.xlsx", content.getvalue())})
    assert response.status_code == 200
    assert response.json()[0]["data"] == "2025-02-03"
    assert response.json()[0]["valor_singelo"] == "1234.56"
    assert response.json()[0]["verba_tipo"] == "dano_moral"
    csv = "data;valor_singelo\n03/02/2025;1234,56\n".encode()
    response = client.post("/api/documentos/parcelas/importar?verba_tipo=dano_material", files={"file": ("parcelas.csv", csv)})
    assert response.status_code == 200
    assert response.json()[0]["data"] == "2025-02-03"


def test_import_does_not_silently_discard_bad_rows(client):
    content = b"data;valor_singelo\n2025-01-01;100.00\n2025-02-31;200.00\n"
    response = client.post("/api/documentos/parcelas/importar?verba_tipo=dano_material", files={"file": ("parcelas.csv", content)})
    assert response.status_code == 422
    assert "nenhuma parcela" in response.json()["detail"]


def test_batch_import_clears_review_and_batch_calculates_real_engine(client, payload):
    uploaded = client.post("/api/lotes/importar", files={"file": ("lote.json", json.dumps({"processos": [payload]}).encode(), "application/json")})
    assert uploaded.status_code == 200
    imported = uploaded.json()["processos"]
    assert imported[0]["revisao_humana_confirmada"] is False
    assert client.post("/api/lotes/executar", json={"processos": imported}).status_code == 422
    imported[0]["revisao_humana_confirmada"] = True
    response = client.post("/api/lotes/executar", json={"processos": imported})
    assert response.status_code == 200
    assert response.json()["resultados"][0]["resultado"]["memoria"]["linhas"]


def test_batch_reports_error_per_process(client, payload):
    import copy
    invalid = copy.deepcopy(payload)
    invalid["numero_processo"] = "2002"
    invalid["parametros"]["indice"] = "indice_inexistente"
    response = client.post("/api/lotes/executar", json={"processos": [payload, invalid]})
    assert response.status_code == 200
    results = response.json()["resultados"]
    assert results[0]["resultado"] is not None
    assert results[1]["erro"] and results[1]["resultado"] is None


def test_late_job_cannot_replace_new_revision(tmp_path):
    _, _, extractions = _stores(tmp_path)
    first = ExtractionStatus(numero_processo="1001", identificador="first", estado="executando", etapa="teste", mensagem="teste", atualizado_em=timestamp())
    second = first.model_copy(update={"identificador": "second", "estado": "aguardando"})
    extractions.start_job(first)
    extractions.start_job(second)
    first.estado = "pronto"
    extractions.update_job(first)
    assert extractions.status("1001").identificador == "second"
    assert extractions.status("1001").estado == "aguardando"


def test_repository_survives_restart_and_recovers_pending_jobs(tmp_path):
    _, documents, extractions = _stores(tmp_path)
    document = DocumentMetadata(identificador="synthetic", numero_processo="1001", nome="1001_1.pdf", sha256="synthetic", tamanho_bytes=1, paginas=1, classificacao="outro")
    documents.add(document)
    extractions.start_job(ExtractionStatus(numero_processo="1001", identificador="pending", estado="executando", etapa="teste", mensagem="teste", atualizado_em=timestamp()))

    _, reopened_documents, reopened_extractions = _stores(tmp_path)
    reopened_extractions.recover_jobs()
    assert reopened_documents.list_for_process("1001") == [document]
    assert reopened_extractions.status("1001").estado == "aguardando"


def test_index_catalog_and_initial_status_are_real(client):
    options = client.get("/api/indices").json()
    assert any(option["chave"] == "sem_correcao" for option in options)
    assert len({option["chave"] for option in options}) == len(options)
    status = client.get("/api/indices/status").json()
    assert status["estado"] == "nao_verificado"
    assert len(status["arquivos_sha256"]) == 3
