"""Funções utilitárias para conversão e arredondamento numérico."""
from __future__ import annotations

import math
from decimal import Decimal, ROUND_HALF_EVEN, ROUND_HALF_UP, getcontext
from typing import Any

getcontext().prec = 42


def D(valor: Any) -> Decimal:
    """Converte valores comuns para ``Decimal`` de forma segura.

    Entrada:
        ``valor``: ``Decimal``, número, texto brasileiro ``"1.234,56"`` ou vazio.

    Saída:
        ``Decimal``. Valores vazios ou ``NaN`` retornam ``Decimal("0")``.

    Exemplo:
        ``D("1.234,56")`` retorna ``Decimal("1234.56")``.
    """
    if isinstance(valor, Decimal):
        return valor
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return Decimal("0")
    texto = str(valor).strip()
    if not texto:
        return Decimal("0")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    return Decimal(texto)


def moeda(valor: Any) -> Decimal:
    """Arredonda um valor para centavos com regra comercial.

    Entrada:
        ``valor``: qualquer entrada aceita por ``D``.

    Saída:
        ``Decimal`` com duas casas decimais.

    Exemplo:
        ``moeda("10.005")`` retorna ``Decimal("10.01")``.
    """
    return D(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def percentual_taxa_legal(valor_decimal: Decimal) -> Decimal:
    """Arredonda percentuais equivalentes da Taxa Legal.

    Entrada:
        ``valor_decimal``: percentual em forma decimal, por exemplo ``0.123456``.

    Saída:
        ``Decimal`` em forma decimal, arredondado a cinco casas percentuais.
    """
    pontos_percentuais = (valor_decimal * Decimal("100")).quantize(
        Decimal("0.00001"),
        rounding=ROUND_HALF_UP,
    )
    return pontos_percentuais / Decimal("100")


def arredondar_abnt(valor: Decimal, casas: int) -> Decimal:
    """Arredonda usando o critério ABNT/meio par.

    Entrada:
        ``valor``: ``Decimal``; ``casas``: número de casas decimais.

    Saída:
        ``Decimal`` arredondado com ``ROUND_HALF_EVEN``.
    """
    return valor.quantize(Decimal("1").scaleb(-casas), rounding=ROUND_HALF_EVEN)
