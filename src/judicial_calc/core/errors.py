"""Exceções estruturadas usadas na fronteira do motor de cálculo.

O objetivo deste módulo é permitir que as camadas web e de interface saibam
*qual campo* precisa de revisão sem interpretar texto de exceção. A mensagem
pública nunca contém o valor recebido, o que reduz o risco de ecoar conteúdo
sensível em logs ou respostas HTTP.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


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

    def __init__(
        self,
        code: str,
        fields: Iterable[str] = (),
        message: str = "Parâmetros de cálculo incompatíveis.",
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        """Inicializa código estável, campos relacionados e metadados seguros.

        ``metadata`` existe apenas para informações técnicas já sanitizadas,
        como chave de índice e competência ``AAAA-MM``. Conteúdo documental,
        valores de parcelas ou outros dados do processo não devem ser incluídos.
        """
        normalized_fields = tuple(dict.fromkeys(str(field) for field in fields if field))
        self.code = str(code)
        self.fields = normalized_fields
        self.metadata = dict(metadata or {})
        super().__init__(message)
