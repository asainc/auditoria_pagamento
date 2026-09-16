"""Exceções estruturadas usadas na fronteira do motor de cálculo.

O objetivo deste módulo é permitir que as camadas web e de interface saibam
*qual campo* precisa de revisão sem interpretar texto de exceção. A mensagem
pública nunca contém o valor recebido, o que reduz o risco de ecoar conteúdo
sensível em logs ou respostas HTTP.
"""
from __future__ import annotations

from collections.abc import Iterable


class CalculationValidationError(ValueError):
    """Representa uma combinação inválida de parâmetros do motor.

    Args:
        code: Código técnico estável para testes, telemetria e tratamento por API.
        fields: Chaves de parâmetros que o operador deve revisar.
        message: Mensagem pública sem os valores fornecidos pelo usuário.

    Atributos:
        code: Identificador programático do erro.
        fields: Tupla ordenada e sem duplicidade com as chaves relacionadas.
    """

    def __init__(self, code: str, fields: Iterable[str] = (), message: str = "Parâmetros de cálculo incompatíveis.") -> None:
        """Inicializa código estável, campos relacionados e mensagem pública sanitizada."""
        normalized_fields = tuple(dict.fromkeys(str(field) for field in fields if field))
        self.code = str(code)
        self.fields = normalized_fields
        super().__init__(message)
