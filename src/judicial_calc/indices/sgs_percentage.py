"""Índices de correção obtidos de séries percentuais mensais SGS/Bacen."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pandas as pd

from judicial_calc.core.dates import competencia_data, iter_competencias, somar_meses
from judicial_calc.core.numbers import D
from judicial_calc.extraction.sgs import baixar_sgs
from judicial_calc.indices.base import CorrectionIndexStrategy

INDICES_SGS = {
    "igp_m_fgv": {"codigo": 189, "nome": "igp_m_fgv", "inicio": "1989-06"},
    "ipca_15_ibge": {"codigo": 7478, "nome": "ipca_15_ibge", "inicio": "2000-05"},
    "ipca_ibge": {"codigo": 433, "nome": "ipca_ibge", "inicio": "1980-01"},
    "inpc_ibge": {"codigo": 188, "nome": "inpc_ibge", "inicio": "1979-04"},
}


def fator_percentual_mensal_por_tabela(
    tabela: pd.DataFrame | list[dict[str, Any]],
    competencia_inicio: str,
    competencia_fim: str,
    coluna_preferida: str,
) -> Decimal:
    """Acumula uma tabela mensal de percentuais.

    Entrada:
        ``tabela``: ``DataFrame`` ou ``list[dict]`` com ``mes`` e coluna de
        percentual; ``competencia_inicio``/``competencia_fim``: ``AAAA-MM``;
        ``coluna_preferida``: nome esperado da coluna de percentual.

    Saída:
        Fator ``Decimal`` composto. Ex.: 1% por dois meses retorna ``1.0201``.
    """
    df = pd.DataFrame(tabela).copy()
    coluna = coluna_preferida if coluna_preferida in df.columns else "indice"
    if "mes" not in df.columns or coluna not in df.columns:
        raise ValueError(f"Tabela percentual precisa ter colunas 'mes' e '{coluna_preferida}' ou 'indice'.")
    df["mes"] = df["mes"].astype(str).str[:7]
    df[coluna] = df[coluna].apply(D)
    mapa = dict(zip(df["mes"], df[coluna]))
    fator = Decimal("1")
    for comp in iter_competencias(competencia_inicio, competencia_fim):
        if comp not in mapa:
            raise ValueError(f"Tabela percentual sem valor para {comp}.")
        fator *= Decimal("1") + mapa[comp] / Decimal("100")
    return fator


def fator_percentual_mensal(indice: str, competencia_inicio: str, competencia_fim: str) -> Decimal:
    """Baixa e acumula um índice percentual mensal do SGS.

    Entrada:
        ``indice``: chave em ``INDICES_SGS``; ``competencia_inicio`` e
        ``competencia_fim``: competências ``AAAA-MM``.

    Saída:
        Fator ``Decimal`` composto.
    """
    meta = INDICES_SGS[indice]
    tabela = baixar_sgs(meta["codigo"], meta["nome"], competencia_inicio, competencia_fim)
    return fator_percentual_mensal_por_tabela(tabela, competencia_inicio, competencia_fim, meta["nome"])


class SGSPercentageCorrectionIndex(CorrectionIndexStrategy):
    """Estratégia de correção por série percentual mensal SGS.

    Entrada de construção:
        ``key``: chave pública; ``codigo``: código SGS; ``value_column``:
        coluna usada após o download.

    Saída:
        ``factor`` retorna fator ``Decimal`` composto pela série mensal.
    """

    def __init__(self, key: str, codigo: int, value_column: str) -> None:
        """Inicializa os metadados da série SGS.

        Exemplo:
            ``SGSPercentageCorrectionIndex("ipca_ibge", 433, "ipca_ibge")``.
        """
        self.key = key
        self.codigo = codigo
        self.value_column = value_column

    def final_competence(self, competencia_atualizacao: str) -> str:
        """Usa a competência anterior ao mês de atualização.

        Entrada:
            ``competencia_atualizacao``: mês-alvo ``AAAA-MM``.

        Saída:
            ``AAAA-MM`` do mês anterior.
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
        """Calcula o fator de correção pela série SGS.

        Entrada:
            ``data_parcela``: data original; ``competencia_atualizacao``:
            mês-alvo; ``tabela_indices``: tabela opcional já baixada;
            ``deflacionar_valor_nominal``: permite fator abaixo de um.

        Saída:
            Fator ``Decimal`` aplicado ao valor da parcela.
        """
        inicio = competencia_data(data_parcela)
        fim = self.final_competence(competencia_atualizacao)
        if fim < inicio:
            return Decimal("1")
        if tabela_indices is None:
            tabela_indices = baixar_sgs(self.codigo, self.value_column, inicio, fim)
        fator = fator_percentual_mensal_por_tabela(tabela_indices, inicio, fim, self.value_column)
        return self._apply_floor(fator, deflacionar_valor_nominal)
