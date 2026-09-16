"""Download de séries mensais e diárias do SGS/Bacen."""
from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache

import pandas as pd

from judicial_calc.core.constants import BCB_SGS_URL
from judicial_calc.core.dates import competencias_entre, data_primeiro_dia, somar_meses, ultimo_dia_mes
from judicial_calc.core.numbers import D
from judicial_calc.data_sources.http_client import HTTP
from judicial_calc.extraction.base import MonthlyTableExtractor


@lru_cache(maxsize=512)
def _baixar_sgs_curto(codigo: int, nome: str, inicio: str, fim: str) -> pd.DataFrame:
    """Baixa um bloco mensal curto do SGS e consolida por competência.

    Entrada:
        ``codigo``: código SGS; ``nome``: nome da coluna de saída;
        ``inicio`` e ``fim``: competências ``AAAA-MM``.

    Saída:
        ``DataFrame`` com ``mes`` e a coluna ``nome`` em ``Decimal``.
    """
    inicio_data = data_primeiro_dia(inicio)
    fim_data = ultimo_dia_mes(fim)
    params = {
        "formato": "json",
        "dataInicial": inicio_data.strftime("%d/%m/%Y"),
        "dataFinal": fim_data.strftime("%d/%m/%Y"),
    }
    url = BCB_SGS_URL.format(codigo=codigo)
    resposta = HTTP.get(url, params=params, timeout=60)
    resposta.raise_for_status()
    dados = resposta.json()
    if not dados:
        raise ValueError(f"SGS {codigo} não retornou dados entre {inicio} e {fim}.")

    df = pd.DataFrame(dados)
    df["data"] = pd.to_datetime(df["data"], dayfirst=True, errors="raise")
    df["mes"] = df["data"].dt.to_period("M").astype(str)
    df[nome] = df["valor"].apply(D)
    return df.sort_values("data").drop_duplicates("mes", keep="last")[["mes", nome]].reset_index(drop=True)


def baixar_sgs(codigo: int, nome: str, inicio: str, fim: str) -> pd.DataFrame:
    """Baixa série mensal do SGS/Bacen em blocos seguros.

    Entrada:
        ``codigo``: código da série SGS; ``nome``: coluna de saída;
        ``inicio`` e ``fim``: competências ``AAAA-MM``.

    Saída:
        ``DataFrame`` com ``mes`` e ``nome``. Ex.: SGS 433 retorna IPCA mensal.
    """
    if competencias_entre(inicio, fim) <= 108:
        return _baixar_sgs_curto(codigo, nome, inicio, fim).copy()

    partes = []
    cursor = inicio
    while cursor <= fim:
        fim_bloco = min(somar_meses(cursor, 107), fim)
        partes.append(_baixar_sgs_curto(codigo, nome, cursor, fim_bloco))
        cursor = somar_meses(fim_bloco, 1)
    return pd.concat(partes, ignore_index=True).drop_duplicates("mes", keep="last").reset_index(drop=True)


@lru_cache(maxsize=256)
def _baixar_sgs_diario_curto(codigo: int, nome: str, data_inicio: date, data_fim: date) -> pd.DataFrame:
    """Baixa um bloco diário curto do SGS/Bacen.

    Entrada:
        ``codigo``: código SGS; ``nome``: coluna de saída;
        ``data_inicio`` e ``data_fim``: datas inclusivas.

    Saída:
        ``DataFrame`` com ``data`` e a coluna ``nome`` em ``Decimal``.
    """
    params = {
        "formato": "json",
        "dataInicial": data_inicio.strftime("%d/%m/%Y"),
        "dataFinal": data_fim.strftime("%d/%m/%Y"),
    }
    url = BCB_SGS_URL.format(codigo=codigo)
    resposta = HTTP.get(url, params=params, timeout=60)
    resposta.raise_for_status()
    dados = resposta.json()
    if not dados:
        raise ValueError(f"SGS {codigo} não retornou dados entre {data_inicio:%d/%m/%Y} e {data_fim:%d/%m/%Y}.")

    df = pd.DataFrame(dados)
    df["data"] = pd.to_datetime(df["data"], dayfirst=True, errors="raise").dt.date
    df[nome] = df["valor"].apply(D)
    return df.sort_values("data")[["data", nome]].reset_index(drop=True)


def baixar_sgs_diario(codigo: int, nome: str, data_inicio: date, data_fim: date) -> pd.DataFrame:
    """Baixa uma série diária do SGS preservando cada data observada.

    Entrada:
        ``codigo``: código SGS; ``nome``: coluna de saída;
        ``data_inicio`` e ``data_fim``: datas inclusivas.

    Saída:
        ``DataFrame`` com ``data`` e ``nome``. Retorna tabela vazia quando
        ``data_fim`` é anterior a ``data_inicio``.
    """
    if data_fim < data_inicio:
        return pd.DataFrame(columns=["data", nome])

    partes = []
    cursor = data_inicio
    while cursor <= data_fim:
        fim_bloco = min(cursor + timedelta(days=365 * 9), data_fim)
        partes.append(_baixar_sgs_diario_curto(codigo, nome, cursor, fim_bloco))
        cursor = fim_bloco + timedelta(days=1)
    return pd.concat(partes, ignore_index=True).drop_duplicates("data", keep="last").reset_index(drop=True)


class SGSMonthlyExtractor(MonthlyTableExtractor):
    """Extrator mensal para uma série SGS/Bacen.

    Entrada de construção:
        ``codigo``: código SGS; ``nome``: nome da coluna de valor.

    Saída:
        ``extract`` retorna ``DataFrame`` mensal no intervalo solicitado.
    """

    def __init__(self, codigo: int, nome: str) -> None:
        """Armazena metadados da série SGS.

        Exemplo:
            ``SGSMonthlyExtractor(433, "ipca_ibge")`` configura IPCA.
        """
        self.codigo = codigo
        self.source_name = f"sgs_{codigo}"
        self.value_column = nome

    def extract(self, inicio: str, fim: str) -> pd.DataFrame:
        """Baixa a janela mensal configurada no extrator.

        Entrada:
            ``inicio`` e ``fim``: competências ``AAAA-MM``.

        Saída:
            ``DataFrame`` com ``mes`` e ``value_column``.
        """
        return baixar_sgs(self.codigo, self.value_column, inicio, fim)
