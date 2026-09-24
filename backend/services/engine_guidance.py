"""Transforma erros estruturados do motor em orientação operacional segura.

A camada HTTP não interpreta mensagens textuais do motor. O motor informa um
código estável e as chaves dos campos relacionados; esta camada apenas converte
essas chaves para os rótulos mantidos no catálogo central de parâmetros.
"""
from __future__ import annotations

from backend.calculation_policy import parameter_label
from judicial_calc.core.errors import CalculationValidationError


MONTH_ABBREVIATIONS = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")


def _format_competence(value: object) -> str:
    """Formata ``AAAA-MM`` sem depender do locale do sistema operacional."""
    text = str(value or "")
    if len(text) >= 7 and text[4] == "-" and text[:4].isdigit() and text[5:7].isdigit():
        month = int(text[5:7])
        if 1 <= month <= 12:
            return f"{MONTH_ABBREVIATIONS[month - 1]}/{text[:4]}"
    return text or "competência não identificada"


def _labels(keys: tuple[str, ...]) -> str:
    """Formata os campos do erro usando a mesma nomenclatura exibida na interface."""
    labels = [parameter_label(key) for key in dict.fromkeys(keys)]
    if not labels:
        return "Parâmetros do cálculo"
    if len(labels) == 1:
        return f'“{labels[0]}”'
    return ", ".join(f'“{label}”' for label in labels[:-1]) + f' e “{labels[-1]}”'


def engine_error_guidance(error: Exception) -> str:
    """Retorna orientação para correção sem analisar nem devolver o texto da exceção.

    ``CalculationValidationError`` carrega os campos do contrato que originaram
    a falha. Exceções não estruturadas recebem uma orientação genérica para que
    nenhum valor potencialmente sensível seja ecoado para a interface.
    """
    if isinstance(error, CalculationValidationError) and error.code == "index_coverage_missing":
        metadata = error.metadata
        label = str(metadata.get("index_label") or "O índice selecionado")
        required = _format_competence(metadata.get("required_competence"))
        first = _format_competence(metadata.get("first_available_competence"))
        last = _format_competence(metadata.get("last_available_competence"))
        maximum_update = _format_competence(metadata.get("maximum_update_competence"))
        reason = str(metadata.get("reason") or "")
        noun = "taxa" if metadata.get("mode") == "rate_decimal" else "valor do índice"
        if reason == "before_first":
            return (
                f"{label} não possui {noun} para {required}. "
                f"Primeira competência disponível: {first}."
            )
        if reason == "gap":
            return (
                f"{label} possui uma lacuna na série em {required}. "
                f"Intervalo observado no arquivo: {first} a {last}."
            )
        return (
            f"{label} não possui {noun} para {required}. "
            f"Última competência disponível: {last}. "
            f"A competência máxima de atualização suportada é {maximum_update}."
        )

    if isinstance(error, CalculationValidationError) and error.code == "index_series_empty":
        label = str(error.metadata.get("index_label") or "O índice selecionado")
        return f"{label} não possui dados disponíveis na planilha instalada. Selecione outro índice ou atualize as séries."

    if isinstance(error, CalculationValidationError) and error.fields:
        return f"Ajuste o(s) parâmetro(s) {_labels(error.fields)} e tente calcular novamente."

    if isinstance(error, CalculationValidationError) and error.code == "missing_installment_columns":
        return "Revise as parcelas informadas; existem campos obrigatórios ausentes antes do cálculo."

    return (
        "Revise os parâmetros de atualização monetária e as datas informadas nas parcelas; "
        "o motor encontrou uma combinação incompatível."
    )
