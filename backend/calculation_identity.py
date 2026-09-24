"""Normalização determinística das identidades usadas no histórico de cálculos."""
from __future__ import annotations

import re


def normalize_process_number(value: str) -> str:
    """Retorna somente os dígitos para comparar processos sem depender de pontuação.

    A função não valida juridicamente o dígito verificador CNJ; ela apenas remove a
    formatação para impedir que o mesmo número seja cadastrado duas vezes com máscaras
    diferentes. Qualquer validação jurídica adicional deve ser homologada pelo time
    responsável antes de virar regra bloqueante.
    """
    digits = re.sub(r"\D", "", str(value or "").strip())
    if not digits:
        raise ValueError("Número do processo inválido.")
    return digits


def display_process_number(value: str) -> str:
    """Aplica a máscara CNJ quando houver exatamente vinte dígitos.

    Identificadores processuais legados ou sintéticos com outro tamanho permanecem
    somente com dígitos, preservando compatibilidade com testes e bases antigas.
    """
    digits = normalize_process_number(value)
    if len(digits) != 20:
        return digits
    return f"{digits[:7]}-{digits[7:9]}.{digits[9:13]}.{digits[13]}.{digits[14:16]}.{digits[16:20]}"


def normalize_manual_identifier(value: str) -> str:
    """Normaliza o identificador manual para comparação sem alterar o rótulo exibido."""
    normalized = str(value or "").strip().upper()
    if not normalized:
        raise ValueError("Identificador do cálculo manual ausente.")
    return normalized
