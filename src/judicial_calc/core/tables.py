"""Normalização de tabelas de índices."""
from __future__ import annotations

from typing import Any

import pandas as pd

from judicial_calc.core.numbers import D


def normalizar_tabela_mensal(
    tabela: pd.DataFrame | list[dict[str, Any]],
    coluna_valor: str = "indice",
) -> pd.DataFrame:
    """Normaliza tabela mensal para o formato usado nos cálculos.

    Entrada:
        ``tabela``: ``DataFrame`` ou ``list[dict]`` com coluna ``mes`` e uma
        coluna de valor; ``coluna_valor``: nome dessa coluna, padrão ``indice``.

    Saída:
        ``DataFrame`` com ``mes`` ``AAAA-MM`` e valor ``Decimal`` ordenado.

    Exemplo:
        ``[{"mes":"2024-08-01", "indice":"1,05"}]`` vira
        ``mes="2024-08"`` e ``indice=Decimal("1.05")``.
    """
    df = pd.DataFrame(tabela).copy()
    if "mes" not in df.columns:
        raise ValueError("A tabela precisa ter a coluna 'mes'.")
    if coluna_valor not in df.columns:
        raise ValueError(f"A tabela precisa ter a coluna '{coluna_valor}'.")
    df["mes"] = df["mes"].astype(str).str[:7]
    df[coluna_valor] = df[coluna_valor].apply(D)
    return df[["mes", coluna_valor]].sort_values("mes").reset_index(drop=True)
