"""Monta contexto enxuto e específico por tarefa para reduzir tokens repetidos."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from judicial_calc.indices.registry import create_default_index_registry

from backend.config import ROOT
from backend.models import CalculationParameters, DocumentMetadata
from backend.services.chronology import document_sequence


TASK_FIELDS: dict[str, tuple[str, ...]] = {
    "00_classificacao": (),
    "01_parcelas": (),
    "02_correcao": ("mes_atualizacao", "ano_atualizacao", "indice", "deflacionar_valor_nominal", "competencia_final_taxa_legal"),
    "03_moratorios": ("juros_moratorios_tipo", "juros_moratorios_taxa", "juros_moratorios_periodicidade", "juros_moratorios_pro_rata", "juros_moratorios_data_inicio", "juros_moratorios_sobre_compensatorios"),
    "04_compensatorios": ("juros_compensatorios_tipo", "juros_compensatorios_taxa", "juros_compensatorios_periodicidade", "juros_compensatorios_pro_rata", "juros_compensatorios_data_inicio"),
    "05_encargos": ("multa_percentual", "honorarios", "honorarios_tipo", "art_523", "incidir_multa_sobre_juros_compensatorios", "incidir_multa_sobre_juros_moratorios", "incidir_multa_sobre_parcelas_a_vencer", "incidir_honorarios_sobre_multa"),
    "06_prescricao": ("prescricao_flag", "prescricao_anos", "prescricao_data_referencia_tipo", "prescricao_data_referencia"),
    "07_compensacao": ("compensacao_flag", "compensacao_tipo_calculo", "compensacao_valor"),
    "08_duplo_indice": tuple(field for field in CalculationParameters.model_fields if field.startswith("duplo_indice_")),
    "09_valor_dobrado": ("valor_dobrado_flag",),
}


@dataclass(frozen=True)
class PromptContext:
    """Prefixo comum estável e contexto processual reutilizados no mesmo processo."""
    base: str
    process_context: str
    parameter_schema: dict

    def for_task(self, task_path: Path) -> str:
        """Inclui somente o subcontrato necessário à tarefa para reduzir payload textual."""
        task = task_path.read_text(encoding="utf-8")
        task_key = task_path.stem
        fields = TASK_FIELDS.get(task_key, ())
        properties = self.parameter_schema.get("properties", {})
        relevant = {field: properties[field] for field in fields if field in properties}
        contract = (
            "Campos de parâmetros permitidos nesta tarefa: " + json.dumps(relevant, ensure_ascii=False, separators=(",", ":"))
            if relevant else
            "Esta tarefa não deve preencher parâmetros de cálculo."
        )
        # A base vem primeiro para favorecer cache de prefixo entre chamadas do mesmo job.
        return f"{self.base}\n\n{self.process_context}\n\n## Subcontrato da tarefa\n{contract}\n\n---\n\n# Tarefa especializada\n\n{task}"


class PromptContextBuilder:
    """Pré-calcula dados estáveis e evita repetir o schema integral em todas as chamadas."""

    def __init__(self, base_path: Path | None = None):
        self.base_path = base_path or ROOT / "prompts/_base.md"
        self.base = self.base_path.read_text(encoding="utf-8")
        registry = create_default_index_registry()
        self.index_catalog = sorted({registry.get(key).key for key in registry.names()})
        self.parameter_schema = CalculationParameters.model_json_schema()

    def build(self, process: str, documents: list[DocumentMetadata]) -> PromptContext:
        """Materializa apenas cronologia e catálogo; o subcontrato entra por tarefa."""
        chronology = [
            {
                "indice_documento": index,
                "arquivo": document.nome,
                "sequencia": document_sequence(document.nome),
                "classificacao_atual": document.classificacao,
            }
            for index, document in enumerate(documents)
        ]
        dynamic = "\n".join([
            "## Contexto fornecido pelo backend",
            f"Processo interno em análise: {process}",
            "Cronologia dos anexos (maior sequência = anexo mais recente): " + json.dumps(chronology, ensure_ascii=False, separators=(",", ":")),
            "Chaves reais de índices aceitas pelo motor: " + json.dumps(self.index_catalog, ensure_ascii=False, separators=(",", ":")),
            "Use somente campos e valores autorizados no subcontrato da tarefa; nunca complete defaults ausentes.",
        ])
        return PromptContext(base=self.base, process_context=dynamic, parameter_schema=self.parameter_schema)
