"""Estratégias base para correção monetária."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal
from typing import Any

import pandas as pd

from judicial_calc.core.dates import competencia_data, somar_meses
from judicial_calc.core.tables import normalizar_tabela_mensal


class CorrectionIndexStrategy(ABC):
    """Contrato para qualquer índice de correção monetária.

    Entrada:
        Classes filhas definem ``key`` e implementam ``final_competence`` e ``factor``.

    Saída:
        Estratégias retornam fator ``Decimal`` para multiplicar o valor base.
    """

    key: str

    @abstractmethod
    def final_competence(self, competencia_atualizacao: str) -> str:
        """Retorna a competência final usada no cálculo do índice.

        Entrada:
            ``competencia_atualizacao``: mês-alvo ``AAAA-MM``.

        Saída:
            ``str`` ``AAAA-MM``.
        """
        raise NotImplementedError

    @abstractmethod
    def factor(
        self,
        *,
        data_parcela: date,
        competencia_atualizacao: str,
        tabela_indices: pd.DataFrame | list[dict[str, Any]] | None,
        deflacionar_valor_nominal: bool,
    ) -> Decimal:
        """Calcula o fator de correção da parcela.

        Entrada:
            ``data_parcela``: data original; ``competencia_atualizacao``:
            mês-alvo; ``tabela_indices``: tabela opcional; ``deflacionar``:
            permite fator abaixo de um quando verdadeiro.

        Saída:
            Fator ``Decimal``.
        """
        raise NotImplementedError

    def _apply_floor(self, fator: Decimal, deflacionar_valor_nominal: bool) -> Decimal:
        """Aplica piso de fator mínimo igual a um quando não há deflação.

        Entrada:
            ``fator``: multiplicador calculado; ``deflacionar_valor_nominal``:
            opção do usuário.

        Saída:
            ``fator`` original ou ``Decimal("1")``.
        """
        return fator if deflacionar_valor_nominal or fator >= Decimal("1") else Decimal("1")


class NoCorrectionIndex(CorrectionIndexStrategy):
    """Estratégia que não aplica correção monetária.

    Entrada:
        Nenhuma.

    Saída:
        ``factor`` sempre retorna ``Decimal("1")``.
    """

    key = "sem_correcao"

    def final_competence(self, competencia_atualizacao: str) -> str:
        """Retorna o mês anterior por consistência com índices mensais.

        Entrada:
            ``competencia_atualizacao``: mês-alvo ``AAAA-MM``.

        Saída:
            Competência anterior ``AAAA-MM``.
        """
        return somar_meses(competencia_atualizacao, -1)

    def factor(
        self,
        *,
        data_parcela: date,
        competencia_atualizacao: str,
        tabela_indices: pd.DataFrame | list[dict[str, Any]] | None,
        deflacionar_valor_nominal: bool,
    ) -> Decimal:
        """Retorna fator neutro para qualquer parcela.

        Entrada:
            Parâmetros do contrato, ignorados nesta estratégia.

        Saída:
            ``Decimal("1")``.
        """
        return Decimal("1")


class ValueTableCorrectionIndex(CorrectionIndexStrategy):
    """Correção por tabela customizada de número-índice mensal.

    Entrada de construção:
        ``key``: nome técnico do índice; ``final_uses_update_month``: se a
        competência final é o próprio mês de atualização.

    Saída:
        ``factor`` calcula ``indice_final / indice_inicial``.
    """

    def __init__(self, key: str = "custom_value_table", final_uses_update_month: bool = False) -> None:
        """Inicializa a estratégia de tabela customizada.

        Exemplo:
            ``ValueTableCorrectionIndex("meu_indice")``.
        """
        self.key = key
        self.final_uses_update_month = final_uses_update_month

    def final_competence(self, competencia_atualizacao: str) -> str:
        """Retorna a competência final da tabela customizada.

        Entrada:
            ``competencia_atualizacao``: mês-alvo ``AAAA-MM``.

        Saída:
            ``AAAA-MM`` do mês-alvo ou do mês anterior.
        """
        if self.final_uses_update_month:
            return competencia_atualizacao
        return somar_meses(competencia_atualizacao, -1)

    def factor(
        self,
        *,
        data_parcela: date,
        competencia_atualizacao: str,
        tabela_indices: pd.DataFrame | list[dict[str, Any]] | None,
        deflacionar_valor_nominal: bool,
    ) -> Decimal:
        """Calcula fator pela tabela customizada do usuário.

        Entrada:
            ``tabela_indices`` deve conter ``mes`` e ``indice``.

        Saída:
            Fator ``Decimal`` por razão entre índice final e inicial.
        """
        if tabela_indices is None:
            raise ValueError("Informe tabela_indices para usar um índice de tabela de valor mensal customizada.")
        inicio = competencia_data(data_parcela)
        fim = self.final_competence(competencia_atualizacao)
        if fim < inicio:
            return Decimal("1")
        fator = fator_tabela_valor_mensal(tabela_indices, inicio, fim)
        return self._apply_floor(fator, deflacionar_valor_nominal)


def fator_tabela_valor_mensal(tabela: pd.DataFrame | list[dict[str, Any]], inicio: str, fim: str) -> Decimal:
    """Calcula fator por tabela de número-índice mensal.

    Entrada:
        ``tabela``: ``DataFrame`` ou ``list[dict]`` com ``mes`` e ``indice``;
        ``inicio`` e ``fim``: competências ``AAAA-MM``.

    Saída:
        ``Decimal`` igual a ``indice[fim] / indice[inicio]``.

    Exemplo:
        índice inicial ``100`` e final ``125`` retornam ``1.25``.
    """
    df = normalizar_tabela_mensal(tabela, "indice")
    mapa = dict(zip(df["mes"], df["indice"]))
    if inicio not in mapa:
        raise ValueError(f"Tabela de índices sem competência inicial {inicio}.")
    if fim not in mapa:
        raise ValueError(f"Tabela de índices sem competência final {fim}.")
    return mapa[fim] / mapa[inicio]
