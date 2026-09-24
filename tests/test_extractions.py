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
                    "alertas": [],
                }
            )
        else:
            fragment = ExtractionFragment(campos=[], parcelas=[], alertas=[])
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
    result = ExtractionResult(numero_processo="1001", campos=[FieldEvidence.model_validate(row) for row in fields], parcelas=[], alertas=[], versao_prompts="teste")
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



def test_wire_contract_accepts_safe_omissions_from_text_generator():
    """Omissões sem efeito financeiro não devem derrubar toda a extração."""
    from backend.services.extraction_wire import WireExtractionFragment

    fragment = WireExtractionFragment.model_validate(
        {
            "campos": [
                {
                    "campo": "parametros.multa_percentual",
                    "valor": "2",
                    "documento": "1001_1.pdf",
                    "pagina": 1,
                    "trecho": "multa de 2%",
                    "escopo": "caso_concreto",
                }
            ],
            "parcelas": [
                {
                    "data": "2025-01-01",
                    "valor_singelo": "100.00",
                    "verba_tipo": "dano_material",
                }
            ],
        }
    )
    assert fragment.campos[0].natureza == "indeterminado"
    assert fragment.campos[0].efeito == "informa"
    assert fragment.parcelas[0].descricao == ""
    assert fragment.alertas == []


def test_provider_repairs_structurally_invalid_generator_response():
    """Uma falha de formato recebe uma única correção via text_generator."""
    class RepairBridge:
        configured = True

        def __init__(self):
            self.calls: list[str] = []

        def generate_text(self, payload: str, *, max_tokens: int) -> str:
            self.calls.append(payload)
            if len(self.calls) == 1:
                return '{"campos":"formato_incorreto","parcelas":[],"alertas":[]}'
            return (
                '{"campos":[],"parcelas":[], '
                '"alertas":["Nenhuma evidência encontrada nesta tarefa."]}'
            )

    bridge = RepairBridge()
    provider = ExtractionProvider(Settings(bradesco_text_model="gpt-5.1"), bridge=bridge)  # type: ignore[arg-type]
    result = provider.extract(
        "Prompt sintético",
        [PdfTextDocument(nome="1001_1.pdf", paginas=(PdfTextPage(1, "Texto sintético."),))],
        stage="teste",
        max_output_tokens=1024,
    )
    assert result.fragmento.campos == []
    assert result.fragmento.alertas == ["Nenhuma evidência encontrada nesta tarefa."]
    assert len(bridge.calls) == 2
    assert "Correção estrutural obrigatória" in bridge.calls[1]
    assert len(result.usos) == 2


def test_provider_unwraps_common_corporate_json_wrapper_without_repair():
    """Wrappers técnicos não devem ser tratados como falha de conteúdo."""
    class WrappedBridge:
        configured = True

        def __init__(self):
            self.calls = 0

        def generate_text(self, payload: str, *, max_tokens: int) -> str:
            self.calls += 1
            return '{"resultado":{"campos":[],"parcelas":[],"alertas":[]}}'

    bridge = WrappedBridge()
    provider = ExtractionProvider(Settings(bradesco_text_model="gpt-5.1"), bridge=bridge)  # type: ignore[arg-type]
    result = provider.extract(
        "Prompt sintético",
        [PdfTextDocument(nome="1001_1.pdf", paginas=(PdfTextPage(1, "Texto sintético."),))],
        stage="teste_wrapper",
        max_output_tokens=1024,
    )
    assert result.fragmento.campos == []
    assert bridge.calls == 1


def test_double_value_flag_is_consolidated_from_document_evidence(client, pdf_bytes):
    """Comando expresso de restituição em dobro vira flag sem alterar a parcela extraída."""
    uploaded = client.post("/api/documentos/upload", files=[("files", ("1001_1.pdf", pdf_bytes, "application/pdf"))]).json()["documentos"]
    from backend.models import DocumentMetadata

    documents = [DocumentMetadata.model_validate(row) for row in uploaded]
    result = ExtractionResult(
        numero_processo="1001",
        campos=[
            FieldEvidence(
                campo="parametros.valor_dobrado_flag",
                valor=True,
                documento="1001_1.pdf",
                pagina=1,
                trecho="Parcela: 100.00.",
                escopo="caso_concreto",
                natureza="comando_decisorio",
                efeito="informa",
            )
        ],
        parcelas=[],
        alertas=[],
        versao_prompts="teste",
    )
    pdf_text = [PdfTextDocument(nome="1001_1.pdf", paginas=(PdfTextPage(1, "Parcela: 100.00."),))]
    consolidated = client.app.state.services.extractions.consolidate(result, documents, pdf_text)
    assert consolidated.parametros_consolidados["valor_dobrado_flag"] is True


def test_structured_output_normalizes_aliases_without_second_llm_call():
    """Aliases estruturais conhecidos são corrigidos localmente antes de gastar nova chamada."""
    class AliasBridge:
        configured = True
        def __init__(self): self.calls = 0
        def generate_text(self, payload: str, *, max_tokens: int) -> str:
            self.calls += 1
            return '{"fields":[],"installments":[],"warnings":[]}'

    bridge = AliasBridge()
    provider = ExtractionProvider(Settings(bradesco_text_model="gpt-5.1"), bridge=bridge)  # type: ignore[arg-type]
    result = provider.extract(
        "Prompt sintético",
        [PdfTextDocument(nome="1001_1.pdf", paginas=(PdfTextPage(1, "Texto sintético suficientemente longo para a tarefa."),))],
        stage="teste_alias",
        max_output_tokens=1024,
    )
    assert result.fragmento.campos == []
    assert bridge.calls == 1


def test_prompt_router_reduces_context_to_relevant_pages():
    from backend.services.prompt_router import PromptPageRouter
    documents = [
        PdfTextDocument(
            nome="1001_1.pdf",
            paginas=tuple(
                PdfTextPage(index, text)
                for index, text in enumerate([
                    "capa e qualificação processual",
                    "texto genérico sem juros",
                    "juros de mora de 1% ao mês desde a citação",
                    "outro texto genérico",
                    "mais texto sem relação",
                ], start=1)
            ),
        )
    ]
    selection = PromptPageRouter(max_pages_per_task=2).select("03_moratorios", documents)
    assert selection.paginas == 1
    assert selection.documentos[0].paginas[0].numero == 3


def test_pymupdf_quality_blocks_image_only_text_before_ai():
    from backend.services.pdf_text_extractor import PdfTextExtractor, PdfTextDocument, PdfTextPage, PdfPageQuality
    from backend.errors import ServiceError
    extractor = PdfTextExtractor(Settings())
    document = PdfTextDocument(
        nome="1001_1.pdf",
        paginas=(PdfTextPage(1, "", PdfPageQuality(0,0,0,0,0,0,"inutilizavel")),),
    )
    try:
        extractor.assert_usable([document])
    except ServiceError as exc:
        assert exc.status_code == 422
    else:
        raise AssertionError("PDF sem texto deveria ser bloqueado antes do text_generator")
