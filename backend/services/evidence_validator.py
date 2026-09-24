"""Validação de evidências contra o texto local e consolidação cronológica."""
from __future__ import annotations

import re

from pydantic import TypeAdapter, ValidationError

from backend.models import CalculationParameters, DocumentMetadata, ExtractionResult, FieldEvidence, Installment
from backend.services.chronology import ChronologyReducer
from backend.services.pdf_text_extractor import PdfTextDocument


class EvidenceValidator:
    """Mantém somente evidências rastreáveis e calcula métricas de aceitação."""

    def __init__(self, reducer: ChronologyReducer | None = None):
        self.reducer = reducer or ChronologyReducer()

    def consolidate(
        self,
        result: ExtractionResult,
        documents: list[DocumentMetadata],
        pdf_documents: list[PdfTextDocument] | None = None,
    ) -> tuple[ExtractionResult, int, int]:
        known = {document.nome: document for document in documents}
        pages: dict[str, dict[int, str]] = {}
        for document in pdf_documents or []:
            pages[document.nome] = {
                page.numero: re.sub(r"\s+", " ", page.texto).strip().casefold()
                for page in document.paginas
            }
        valid: list[FieldEvidence] = []
        rejected = 0
        for evidence in result.campos:
            is_document_classification = evidence.campo.startswith("documentos.") and evidence.campo.endswith(".classificacao")
            if (
                evidence.documento not in known
                or evidence.pagina > known[evidence.documento].paginas
                or not evidence.trecho.strip()
                or (evidence.escopo != "caso_concreto" and not is_document_classification)
            ):
                result.alertas.append("Uma extração sem fonte válida do caso concreto foi descartada.")
                rejected += 1
                continue
            if evidence.campo.startswith("parametros.") and evidence.campo.split(".", 1)[1] not in CalculationParameters.model_fields:
                result.alertas.append("Um parâmetro não reconhecido pelo contrato foi descartado.")
                rejected += 1
                continue
            text = pages.get(evidence.documento, {}).get(evidence.pagina, "")
            quoted = re.sub(r"\s+", " ", evidence.trecho).strip().casefold()
            if text and quoted not in text:
                result.alertas.append("Uma evidência cujo trecho não foi localizado no texto extraído da página foi descartada.")
                rejected += 1
                continue
            if not text:
                result.alertas.append("Página sem texto pesquisável para uma evidência: a conferência visual é obrigatória.")
            if evidence.campo.startswith("parametros.") and evidence.valor is not None:
                key = evidence.campo.split(".", 1)[1]
                try:
                    TypeAdapter(CalculationParameters.model_fields[key].rebuild_annotation()).validate_python(evidence.valor)
                except ValidationError:
                    result.alertas.append(f"Campo {key} fora do contrato: preenchimento manual necessário.")
                    rejected += 1
                    continue
            valid.append(evidence)

        consolidated, decisions, chronology_alerts = self.reducer.reduce(valid)
        result.campos = valid
        result.parametros_consolidados = consolidated
        result.decisoes_cronologicas = decisions
        result.alertas.extend(chronology_alerts)

        accepted_installments: list[Installment] = []
        for index, item in enumerate(result.parcelas):
            required_keys = ["data", "valor_singelo", "verba_tipo"]
            if item.multiplicador is not None:
                required_keys.append("multiplicador")
            if all(
                any(
                    field.campo == f"parcelas.{index}.{key}"
                    and str(field.valor) == str(getattr(item, key))
                    for field in valid
                )
                for key in required_keys
            ):
                accepted_installments.append(item)
        if len(accepted_installments) != len(result.parcelas):
            result.alertas.append("Parcelas sem evidência suficiente foram descartadas.")
        result.parcelas = accepted_installments

        values: dict[str, set[str]] = {}
        for field in valid:
            values.setdefault(field.campo, set()).add(str(field.valor))
        resolved_paths = {f"parametros.{key}" for key in result.parametros_consolidados}
        for field, alternatives in values.items():
            if len(alternatives) > 1 and field not in resolved_paths:
                result.alertas.append(f"Conflito em {field}: escolha o critério após revisão do documento.")
        result.alertas = list(dict.fromkeys(result.alertas))
        return result, len(valid), rejected
