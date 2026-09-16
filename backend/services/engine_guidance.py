"""Transforma erros estruturados do motor em orientação operacional segura.

A camada HTTP não interpreta mensagens textuais do motor. O motor informa um
código estável e as chaves dos campos relacionados; esta camada apenas converte
essas chaves para os rótulos mantidos no catálogo central de parâmetros.
"""
from __future__ import annotations

from backend.calculation_policy import parameter_label
from judicial_calc.core.errors import CalculationValidationError


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
    if isinstance(error, CalculationValidationError) and error.fields:
        return f"Ajuste o(s) parâmetro(s) {_labels(error.fields)} e tente calcular novamente."

    if isinstance(error, CalculationValidationError) and error.code == "missing_installment_columns":
        return "Revise as parcelas informadas; existem campos obrigatórios ausentes antes do cálculo."

    return (
        "Revise os parâmetros de atualização monetária e as datas informadas nas parcelas; "
        "o motor encontrou uma combinação incompatível."
    )
