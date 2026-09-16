"""Tipos públicos retornados pela biblioteca."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class ResultadoCalculo:
    """Resultado completo do cálculo judicial.

    Atributos:
        ``memoria``: ``DataFrame`` linha a linha com parcelas, correção,
        juros, multa, honorários e total;
        ``resumo``: ``DataFrame`` com totais consolidados;
        ``parametros``: ``dict[str, Any]`` com os parâmetros usados.

    Exemplo:
        ``resultado.memoria`` pode ser salvo em Excel pela função
        ``salvar_resultado_excel``.
    """

    memoria: pd.DataFrame
    resumo: pd.DataFrame
    parametros: dict[str, Any]
