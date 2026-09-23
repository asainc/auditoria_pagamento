"""Testa a orquestração com provedor controlado; não executa rede corporativa."""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

from backend.config import Settings
from backend.models import AiUsage, ExtractionResult, FieldEvidence
from backend.principal import create_app
from backend.services.chronology import document_sequence, ordered_documents
from backend.services.extraction import ExtractionFragment, ExtractionProvider, PdfTextDocument, PdfTextPage, ProviderResult


class SyntheticProvider(ExtractionProvider):
    """Dublê fornece somente fatos presentes no texto sintético da fixture."""

    @property
    def configured(self):
        return True

    def read_documents(self, files):
        return [
            PdfTextDocument(
                nome=name,
                paginas=(PdfTextPage(1, "Parcela: 100.00. Data: 2025-01-01. Tipo: dano_material. Multa: 2%."),),
            )
            for name, _, _ in files
        ]

    def extract(self, prompt, documents, *, stage, max_output_tokens):
        source = {
            "documento": documents[0].nome,
            "pagina": 1,
            "trecho": "Parcela: 100.00. Data: 2025-01-01. Tipo: dano_material.",
            "escopo": "caso_concreto",
        }
        if "# Extraindo parcelas" in prompt:
            fragment = ExtractionFragment.model_validate(
                {
                    "campos": [
                        {
                            **source,
                            "campo": "parcelas.0." + key,
                            "valor": value,
                            "natureza": "fato",
                            "efeito": "informa",
                        }
                        for key, value in {
                            "data": "2025-01-01",
                            "valor_singelo": "100.00",
                            "verba_tipo": "dano_material",
                        }.items()
                    ],
                    "parcelas": [
                        {
                            "data": "2025-01-01",
                            "valor_singelo": "100.00",
                            "verba_tipo": "dano_material",
                        }
                    ],
                    "eventos_financeiros": [],
                    "alertas": [],
                }
            )
        else:
            fragment = ExtractionFragment(campos=[], parcelas=[], eventos_financeiros=[], alertas=[])
        usage = AiUsage(etapa=stage, modelo=self.settings.bradesco_text_model, duracao_ms=1)
        return ProviderResult(fragmento=fragment, usos=[usage])


def test_document_sequence_orders_history_by_attachment_number():
    from backend.models import DocumentMetadata

    documents = [
        DocumentMetadata(identificador="a", numero_processo="1001", nome="1001_10.pdf", sha256="a" * 64, tamanho_bytes=1, paginas=1, classificacao="a_classificar"),
        DocumentMetadata(identificador="b", numero_processo="1001", nome="1001_2.pdf", sha256="b" * 64, tamanho_bytes=1, paginas=1, classificacao="a_classificar"),
        DocumentMetadata(identificador="c", numero_processo="1001", nome="1001_3_anexo.pdf", sha256="c" * 64, tamanho_bytes=1, paginas=1, classificacao="a_classificar"),
    ]
    assert document_sequence("1001_10.pdf") == 10
    assert document_sequence("1001_3_anexo.pdf") == 3
    assert [item.nome for item in ordered_documents(documents)] == ["1001_2.pdf", "1001_3_anexo.pdf", "1001_10.pdf"]


def test_pymupdf_reads_text_locally(pdf_bytes):
    provider = ExtractionProvider(Settings(bradesco_text_model="gpt-5.1"))
    documents = provider.read_documents([("1001_1.pdf", pdf_bytes, 1)])
    assert len(documents) == 1
    assert documents[0].paginas[0].numero == 1
    assert "Parcela: 100.00" in documents[0].paginas[0].texto
    assert not any("Container" in alert for alert in documents[0].alertas)


def test_upload_orchestrates_background_extraction(tmp_path, pdf_bytes):
    settings = Settings(data_dir=tmp_path)
    with TestClient(create_app(settings, SyntheticProvider(settings))) as client:
        upload = client.post("/api/documentos/upload", files=[("files", ("1001_1.pdf", pdf_bytes, "application/pdf"))])
        assert upload.status_code == 202
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            status = client.get("/api/extracoes/1001/status").json()
            if status["estado"] not in {"aguardando", "executando"}:
                break
            time.sleep(0.01)
        assert status["estado"] == "pronto", status
        result = client.get("/api/extracoes/1001/resultado").json()
        assert result["parcelas"][0]["valor_singelo"] == "100.00"
        assert result["campos"][0]["documento"] == "1001_1.pdf"
        assert len(result["versao_prompts"]) == 64
        assert result["uso_ia"]["tokens_total"] is None


def test_jurisprudence_wrong_source_and_fabricated_quote_are_rejected(client, pdf_bytes):
    uploaded = client.post("/api/documentos/upload", files=[("files", ("1001_1.pdf", pdf_bytes, "application/pdf"))]).json()["documentos"]
    from backend.models import DocumentMetadata

    documents = [DocumentMetadata.model_validate(row) for row in uploaded]
    valid = {"campo": "parametros.multa_percentual", "valor": "2", "documento": "1001_1.pdf", "pagina": 1, "trecho": "Multa: 2%.", "escopo": "caso_concreto"}
    fields = [
        valid,
        {**valid, "escopo": "jurisprudencia_citada"},
        {**valid, "documento": "9999_1.pdf"},
        {**valid, "pagina": 2},
        {**valid, "trecho": "Trecho inexistente no documento"},
        {**valid, "valor": "-1"},
    ]
    result = ExtractionResult(numero_processo="1001", campos=[FieldEvidence.model_validate(row) for row in fields], parcelas=[], eventos_financeiros=[], alertas=[], versao_prompts="teste")
    pdf_text = [PdfTextDocument(nome="1001_1.pdf", paginas=(PdfTextPage(1, "Multa: 2%."),))]
    consolidated = client.app.state.services.extractions.consolidate(result, documents, pdf_text)
    assert len(consolidated.campos) == 1
    assert consolidated.campos[0].valor == "2"
    assert consolidated.alertas


def test_provider_failure_becomes_explicit_status(tmp_path, pdf_bytes):
    class FailingProvider(SyntheticProvider):
        def extract(self, prompt, documents, *, stage, max_output_tokens):
            raise RuntimeError("Falha sintética do provedor")

    settings = Settings(data_dir=tmp_path)
    with TestClient(create_app(settings, FailingProvider(settings))) as client:
        client.post("/api/documentos/upload", files=[("files", ("1001_1.pdf", pdf_bytes, "application/pdf"))])
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            status = client.get("/api/extracoes/1001/status").json()
            if status["estado"] == "falha":
                break
            time.sleep(0.01)
        assert status["estado"] == "falha"
        assert client.get("/api/extracoes/1001/resultado").status_code == 409
