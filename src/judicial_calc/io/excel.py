from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from judicial_calc.core.types import ResultadoCalculo


def _safe_df(value: Any) -> pd.DataFrame:
    """Converte listas/dicts/escalares para DataFrame sem quebrar exportação."""
    if isinstance(value, pd.DataFrame):
        return value.copy()
    if isinstance(value, list):
        return pd.DataFrame(value)
    if isinstance(value, dict):
        # evidence_map tem formato campo -> lista de evidências.
        if value and all(isinstance(v, list) for v in value.values()):
            rows = []
            for field, evidences in value.items():
                for evidence in evidences:
                    if isinstance(evidence, dict):
                        rows.append({"field_path": field, **evidence})
                    else:
                        rows.append({"field_path": field, "evidence": evidence})
            return pd.DataFrame(rows)
        return pd.DataFrame([value])
    if value is None:
        return pd.DataFrame()
    return pd.DataFrame([{"valor": value}])


def _write_if_not_empty(writer: pd.ExcelWriter, sheet_name: str, value: Any) -> None:
    """Escreve uma aba somente quando há conteúdo."""
    df = _safe_df(value)
    if df.empty:
        return
    safe_name = sheet_name[:31]
    df.to_excel(writer, sheet_name=safe_name, index=False)


def salvar_resultado_excel(resultado: ResultadoCalculo, caminho: str | Path) -> None:
    """Salva a memória, resumo e trilha auditável do cálculo em Excel.

    Além das abas históricas ``memoria`` e ``resumo``, o export agora inclui
    evidências, documentos, conflitos, verbas, validações
    e itens de revisão humana quando essas estruturas estiverem em
    ``resultado.parametros``.
    """
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    parametros = dict(resultado.parametros or {})

    parametros_simples = {
        key: value
        for key, value in parametros.items()
        if key
        not in {
            "evidence_map",
            "extraction_audit",
            "document_roles",
            "document_conflicts",
            "ignored_jurisprudence_audit",
            "validation_issues",
            "verbas",
            "human_review_checklist",
        }
    }

    with pd.ExcelWriter(caminho, engine="openpyxl") as writer:
        resultado.resumo.to_excel(writer, sheet_name="Resumo", index=False)
        resultado.memoria.to_excel(writer, sheet_name="Memoria_calculo", index=False)
        _write_if_not_empty(writer, "Parametros_utilizados", [{"campo": k, "valor": v} for k, v in parametros_simples.items()])
        _write_if_not_empty(writer, "Evidencias_parametros", parametros.get("evidence_map"))
        _write_if_not_empty(writer, "Auditoria_extracao", parametros.get("extraction_audit"))
        _write_if_not_empty(writer, "Documentos_lidos", parametros.get("document_roles"))
        _write_if_not_empty(writer, "Alertas_auditoria", parametros.get("validation_issues"))
        _write_if_not_empty(writer, "Jurisprudencia_ignorada", parametros.get("ignored_jurisprudence_audit"))
        _write_if_not_empty(writer, "Conflitos_documentos", parametros.get("document_conflicts"))
        _write_if_not_empty(writer, "Verbas", parametros.get("verbas"))
        _write_if_not_empty(writer, "Checklist_revisao", parametros.get("human_review_checklist"))
