"""Orquestração de extração documental com leitura local, seleção de páginas e fila durável."""
from __future__ import annotations

import hashlib
import json
import logging
from threading import Lock
from uuid import uuid4

from backend.config import ROOT, Settings
from backend.errors import ServiceError
from backend.contracts.extraction import AiUsage, AiUsageSummary, ExtractionResult, ExtractionStatus
from backend.contracts.document import DocumentMetadata
from backend.persistence.schema import timestamp
from backend.repositories.audit_repository import AuditRepository
from backend.repositories.document_repository import DocumentRepository
from backend.repositories.extraction_repository import ExtractionRepository
from backend.services.bradesco_bridge import BradescoBridgeClient
from backend.services.chronology import ordered_documents
from backend.services.documents import DocumentService
from backend.services.evidence_validator import EvidenceValidator
from backend.services.extraction_jobs import ClaimedExtractionJob, DurableExtractionWorkers
from backend.services.extraction_types import ExtractionFragment, ProviderResult
from backend.services.operational_policy import OperationalPolicy
from backend.services.pdf_text_extractor import PdfTextDocument, PdfTextExtractor, PdfTextPage
from backend.services.prompt_context import PromptContextBuilder
from backend.services.prompt_executor import PromptExecutionError, PromptExecutionMetrics, PromptExecutor

logger = logging.getLogger("judicial")


class ExtractionProviderError(ServiceError):
    """Erro público estável; nunca inclui corpo da resposta, prompt ou credencial."""

    def __init__(self, code: str, message: str, status_code: int = 502, retryable: bool = False):
        super().__init__(message, status_code)
        self.code = code
        self.retryable = retryable


class ExtractionProvider:
    """Fachada testável para PyMuPDF, roteamento de páginas e text_generator."""

    def __init__(self, settings: Settings, bridge: BradescoBridgeClient | None = None):
        self.settings = settings
        self.bridge = bridge or BradescoBridgeClient(settings)
        self.pdf = PdfTextExtractor(settings)
        self.prompts = PromptExecutor(settings, self.bridge)

    @property
    def configured(self) -> bool:
        return self.bridge.configured

    def read_documents(self, files: list[tuple[str, bytes, int]]) -> list[PdfTextDocument]:
        try:
            documents = self.pdf.read(files)
            self.pdf.assert_usable(documents)
            return documents
        except ServiceError as exc:
            raise ExtractionProviderError("pdf_texto_baixa_qualidade", exc.message, exc.status_code) from None

    def extract_with_metrics(
        self,
        prompt: str,
        documents: list[PdfTextDocument],
        *,
        stage: str,
        max_output_tokens: int,
    ) -> tuple[ProviderResult, PromptExecutionMetrics]:
        """Executa a tarefa e devolve métricas sem quebrar provedores de teste legados.

        Provedores especializados anteriores sobrescreviam ``extract`` diretamente.
        A refatoração para métricas preserva esse contrato para evitar que integrações
        internas precisem conhecer a implementação de observabilidade do orquestrador.
        """
        if type(self).extract is not ExtractionProvider.extract:
            result = self.extract(
                prompt,
                documents,
                stage=stage,
                max_output_tokens=max_output_tokens,
            )
            pages = sum(len(document.paginas) for document in documents)
            characters = sum(len(page.texto) for document in documents for page in document.paginas)
            return result, PromptExecutionMetrics(pages, characters, 1, 0, "provedor_especializado")
        try:
            return self.prompts.execute(
                prompt,
                documents,
                stage=stage,
                max_output_tokens=max_output_tokens,
            )
        except PromptExecutionError as exc:
            raise ExtractionProviderError(exc.code, exc.message, exc.status_code, exc.retryable) from None

    def extract(
        self,
        prompt: str,
        documents: list[PdfTextDocument],
        *,
        stage: str,
        max_output_tokens: int,
    ) -> ProviderResult:
        """Compatibilidade para testes e integrações que não consomem métricas detalhadas."""
        return self.extract_with_metrics(
            prompt,
            documents,
            stage=stage,
            max_output_tokens=max_output_tokens,
        )[0]


class ExtractionService:
    """Orquestra fila durável, prompts especializados, validação e persistência."""

    def __init__(
        self,
        settings: Settings,
        extraction_repository: ExtractionRepository,
        document_repository: DocumentRepository,
        audit_repository: AuditRepository,
        documents: DocumentService,
        provider: ExtractionProvider,
    ):
        self.settings = settings
        self.extraction_repository = extraction_repository
        self.document_repository = document_repository
        self.audit_repository = audit_repository
        self.documents = documents
        self.provider = provider
        self.policy = OperationalPolicy(settings.operational)
        self.lock = Lock()
        prompt_directory = ROOT / "prompts"
        self.base_prompt = prompt_directory / "_base.md"
        self.prompts = sorted(path for path in prompt_directory.glob("*.md") if not path.name.startswith("_"))
        self.context_builder = PromptContextBuilder(self.base_prompt)
        self.validator = EvidenceValidator()
        self.task_config = json.loads((ROOT / "config/extraction_tasks.json").read_text(encoding="utf-8"))
        versioned_files = [
            self.base_prompt,
            *self.prompts,
            ROOT / "config/calculation_policy.json",
            ROOT / "config/extraction_tasks.json",
            ROOT / "gpt_bradesco.py",
        ]
        self.version = hashlib.sha256(b"".join(path.read_bytes() for path in versioned_files)).hexdigest()
        self.workers = DurableExtractionWorkers(
            extraction_repository,
            settings.extraction_workers,
            self._handle_claimed_job,
            lease_seconds=settings.extraction_lease_seconds,
        )

    def start(self, process: str, new_upload: bool = False) -> ExtractionStatus:
        """Cria uma revisão e a persiste na fila; trabalhos ativos são compartilhados."""
        documents = self.document_repository.list_for_process(process)
        if not documents:
            raise ServiceError("Envie documentos para este processo antes da extração.", 404)
        with self.lock:
            current = self.extraction_repository.status(process)
            if current and current.estado in {"aguardando", "executando"} and not new_upload:
                return current
            status = ExtractionStatus(
                numero_processo=process,
                identificador=uuid4().hex,
                estado="aguardando",
                etapa="Recebendo documentos",
                mensagem="Extração registrada na fila durável.",
                atualizado_em=timestamp(),
            )
            if not self.provider.configured:
                status.estado = "bloqueada"
                status.codigo_erro = "bradesco_nao_configurado"
                status.mensagem = (
                    "Configure BRADESCO_TEXT_MODEL e mantenha gpt_bradesco.py com text_generator funcional; "
                    "depois repita a extração. Os PDFs locais já foram preservados."
                )
                self.extraction_repository.start_job(status, max_attempts=self.settings.extraction_max_attempts)
                self.extraction_repository.finish_job(status.identificador, success=False)
                return status
            self.extraction_repository.start_job(status, max_attempts=self.settings.extraction_max_attempts)
        return status

    def _handle_claimed_job(self, claimed: ClaimedExtractionJob) -> None:
        status = self.extraction_repository.status(claimed.process)
        if status is None or status.identificador != claimed.job_id:
            self.extraction_repository.finish_job(claimed.job_id, success=False)
            return
        documents = self.document_repository.list_for_process(claimed.process)
        try:
            self._run_once(status, documents, claimed.attempt)
        except ExtractionProviderError as exc:
            if exc.retryable and claimed.attempt < claimed.max_attempts:
                status.estado = "aguardando"
                status.etapa = "Aguardando nova tentativa"
                status.codigo_erro = exc.code
                status.mensagem = (
                    f"Falha transitória na extração. Nova tentativa automática {claimed.attempt + 1} de {claimed.max_attempts} será realizada."
                )
                status.atualizado_em = timestamp()
                self.extraction_repository.update_job(status)
                self.extraction_repository.retry_job(
                    claimed.job_id,
                    self.settings.extraction_retry_delay_seconds * claimed.attempt,
                )
                self.audit_repository.append(
                    "extraction_retry_scheduled",
                    {"job": claimed.job_id, "attempt": claimed.attempt, "error_code": exc.code},
                )
                return
            self._persist_failure(status, exc.code, exc.message)
            self.extraction_repository.finish_job(claimed.job_id, success=False)
        except Exception as exc:
            logger.error(
                "extraction_failed",
                extra={"job_id": claimed.job_id, "error_type": type(exc).__name__},
            )
            self._persist_failure(
                status,
                "extracao_falhou",
                "Extração não concluída. Os documentos foram preservados. Repita a extração e, se persistir, consulte o suporte.",
            )
            self.extraction_repository.finish_job(claimed.job_id, success=False)
        else:
            self.extraction_repository.finish_job(claimed.job_id, success=True)

    def _persist_failure(self, status: ExtractionStatus, code: str, message: str) -> None:
        status.estado = "falha"
        status.codigo_erro = code
        status.mensagem = message
        status.atualizado_em = timestamp()
        self.extraction_repository.update_job(status)
        self.audit_repository.append("extraction_failed", {"job": status.identificador, "error_code": code})

    def _run_once(self, status: ExtractionStatus, documents: list[DocumentMetadata], attempt: int) -> None:
        status.estado = "executando"
        status.etapa = "Extraindo texto dos PDFs com PyMuPDF"
        status.mensagem = "Lendo e avaliando a qualidade da camada de texto dos documentos localmente, sem OCR."
        status.atualizado_em = timestamp()
        self.extraction_repository.update_job(status)

        documents = ordered_documents(documents)
        files = [
            (document.nome, self.documents.path(document.identificador)[0].read_bytes(), document.paginas)
            for document in documents
        ]
        pdf_documents = self.provider.read_documents(files)
        page_count = sum(len(document.paginas) for document in pdf_documents)
        usable_pages = sum(len(document.paginas_utilizaveis) for document in pdf_documents)
        usable_chars = sum(document.caracteres_utilizaveis for document in pdf_documents)
        pdf_metrics = {
            "job": status.identificador, "attempt": attempt, "documents": len(pdf_documents),
            "pages": page_count, "usable_pages": usable_pages, "characters": usable_chars,
        }
        self.audit_repository.append("extraction_pdf_text_ready", pdf_metrics)
        logger.info("extraction_pdf_text_ready", extra={"job_id":status.identificador,"attempt":attempt,"pages":page_count,"characters":usable_chars})

        context = self.context_builder.build(status.numero_processo, documents)
        result = ExtractionResult(
            numero_processo=status.numero_processo,
            campos=[],
            parcelas=[],
            alertas=[alert for document in pdf_documents for alert in document.alertas],
            versao_prompts=self.version,
        )
        usages: list[AiUsage] = []
        for path in self.prompts:
            current = self.extraction_repository.status(status.numero_processo)
            if current is None or current.identificador != status.identificador:
                return
            stage = path.stem
            status.etapa = path.read_text(encoding="utf-8").splitlines()[0].lstrip("# ")
            status.atualizado_em = timestamp()
            self.extraction_repository.update_job(status)
            prompt = context.for_task(path)
            budget = int(
                self.task_config.get(stage, {}).get(
                    "max_output_tokens",
                    self.provider.settings.bradesco_text_max_tokens,
                )
            )
            provider_result, metrics = self.provider.extract_with_metrics(
                prompt,
                pdf_documents,
                stage=stage,
                max_output_tokens=budget,
            )
            fragment = provider_result.fragmento
            usages.extend(provider_result.usos)
            status.uso_ia = self._summarize_usage(usages)
            self.extraction_repository.update_job(status)
            result.campos.extend(fragment.campos)
            result.parcelas.extend(fragment.parcelas)
            result.alertas.extend(fragment.alertas)
            prompt_metrics = {
                "job": status.identificador, "stage": stage,
                "prompt_hash": hashlib.sha256(path.read_bytes()).hexdigest(),
                "pages": metrics.paginas_contexto, "characters": metrics.caracteres_contexto,
                "chunks": metrics.chunks, "repairs": metrics.reparos_estruturais,
                "fields": len(fragment.campos), "installments": len(fragment.parcelas),
            }
            self.audit_repository.append("extraction_prompt_completed", prompt_metrics)
            logger.info("extraction_prompt_completed", extra={"job_id":status.identificador,"stage":stage,"pages":metrics.paginas_contexto,"characters":metrics.caracteres_contexto})

        status.etapa = "Consolidando informações"
        self.extraction_repository.update_job(status)
        result, accepted_evidence, rejected_evidence = self.validator.consolidate(result, documents, pdf_documents)
        result = self.policy.apply(result)
        result.uso_ia = self._summarize_usage(usages)
        self.audit_repository.append("extraction_evidence_validated", {"job":status.identificador,"accepted":accepted_evidence,"rejected":rejected_evidence})
        logger.info("extraction_evidence_validated", extra={"job_id":status.identificador,"accepted":accepted_evidence,"rejected":rejected_evidence})

        for index, document in enumerate(documents):
            classifications = [
                field.valor for field in result.campos
                if field.campo == f"documentos.{index}.classificacao"
            ]
            if len(set(classifications)) == 1 and classifications[0] in {
                "peticao_inicial", "sentenca", "acordao", "comprovante_pagamento", "extrato", "decisao", "outro",
            }:
                self.document_repository.classify(document.identificador, str(classifications[0]))

        status.estado = "pronto"
        status.etapa = "Pronto para revisão"
        status.mensagem = "Confira os campos extraídos e suas fontes antes do cálculo."
        status.codigo_erro = None
        status.atualizado_em = timestamp()
        self.extraction_repository.update_job(status, result)
        self.audit_repository.append(
            "extraction_completed",
            {
                "job": status.identificador,
                "prompt_hash": self.version,
                "fields": len(result.campos),
                "calls": result.uso_ia.chamadas if result.uso_ia else 0,
                "duration_ms": result.uso_ia.duracao_total_ms if result.uso_ia else 0,
            },
        )

    def run(self, status: ExtractionStatus, documents: list[DocumentMetadata]) -> None:
        """Compatibilidade de teste: executa uma tentativa síncrona fora da fila."""
        try:
            self._run_once(status, documents, 1)
        except ExtractionProviderError as exc:
            self._persist_failure(status, exc.code, exc.message)
        except Exception as exc:
            logger.error("extraction_failed", extra={"error_type": type(exc).__name__})
            self._persist_failure(
                status,
                "extracao_falhou",
                "Extração não concluída. Os documentos foram preservados. Repita a extração e, se persistir, consulte o suporte.",
            )

    @staticmethod
    def _sum_optional(values: list[int | None]) -> int | None:
        return sum(value for value in values if value is not None) if values and all(value is not None for value in values) else None

    @classmethod
    def _summarize_usage(cls, usages: list[AiUsage]) -> AiUsageSummary:
        return AiUsageSummary(
            chamadas=len(usages),
            tokens_entrada=cls._sum_optional([item.tokens_entrada for item in usages]),
            tokens_entrada_cache=cls._sum_optional([item.tokens_entrada_cache for item in usages]),
            tokens_saida=cls._sum_optional([item.tokens_saida for item in usages]),
            tokens_total=cls._sum_optional([item.tokens_total for item in usages]),
            custo_estimado_usd=None,
            duracao_total_ms=round(sum(item.duracao_ms for item in usages), 2),
            detalhamento=list(usages),
        )

    def consolidate(
        self,
        result: ExtractionResult,
        documents: list[DocumentMetadata],
        pdf_documents: list[PdfTextDocument] | None = None,
    ) -> ExtractionResult:
        """Compatibilidade pública para testes de consolidação."""
        return self.validator.consolidate(result, documents, pdf_documents)[0]

    def close(self) -> None:
        self.workers.close()
