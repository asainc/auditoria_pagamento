"""Contratos simples para extratores de tabelas mensais."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class MonthlyTableExtractor(ABC):
    """Interface para fontes que entregam séries mensais.

    Entrada:
        Classes filhas definem ``source_name`` e ``value_column``.

    Saída:
        O método ``extract`` deve retornar ``DataFrame`` com ``mes`` e valor.
    """

    source_name: str
    value_column: str

    @abstractmethod
    def extract(self, inicio: str, fim: str) -> pd.DataFrame:
        """Extrai uma janela mensal fechada.

        Entrada:
            ``inicio`` e ``fim``: competências ``AAAA-MM``.

        Saída:
            ``DataFrame`` filtrado no intervalo pedido.
        """
        raise NotImplementedError


class InMemoryMonthlyTableExtractor(MonthlyTableExtractor):
    """Extrator para tabelas já carregadas em memória.

    Entrada de construção:
        ``tabela``: ``DataFrame`` ou ``list[dict]``; ``value_column``: coluna
        de valor a normalizar.

    Saída:
        ``extract`` retorna a tabela filtrada por competência.
    """

    def __init__(self, tabela: pd.DataFrame | list[dict[str, Any]], value_column: str = "indice") -> None:
        """Armazena a tabela que será filtrada posteriormente.

        Exemplo:
            ``InMemoryMonthlyTableExtractor([{"mes":"2024-01", "indice":1}])``.
        """
        self.tabela = tabela
        self.source_name = "in_memory"
        self.value_column = value_column

    def extract(self, inicio: str, fim: str) -> pd.DataFrame:
        """Filtra a tabela de memória no intervalo mensal.

        Entrada:
            ``inicio`` e ``fim``: competências ``AAAA-MM``.

        Saída:
            ``DataFrame`` normalizado com meses dentro do intervalo.
        """
        from judicial_calc.core.tables import normalizar_tabela_mensal

        df = normalizar_tabela_mensal(self.tabela, self.value_column)
        return df[(df["mes"] >= inicio) & (df["mes"] <= fim)].reset_index(drop=True)
