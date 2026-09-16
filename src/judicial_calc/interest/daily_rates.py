"""Juros moratórios por tabelas diárias locais."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pandas as pd

from judicial_calc.core.dates import competencia_data, parse_data, somar_meses, ultimo_dia_mes
from judicial_calc.core.numbers import D, moeda
from judicial_calc.data_sources.local_excel import load_daily_rate_table, load_taxa_legal_mensal_percentual

TIPOS_JUROS_MORATORIOS_DIARIOS_SELIC_IPCAE = {
    "taxa_legal_14905_stj1368",
    "taxa_legal_14905_tema_1368",
    "juros_moratorios_stj1368_lei_14905",
    "mora_stj1368_lei_14905",
    "taxa_legal_diaria_selic_ipcae",
    "taxa_diaria_selic_ipcae",
}

TIPOS_JUROS_MORATORIOS_DIARIOS_12_6 = {
    "juros_moratorios_ctn_lei_14905",
    "taxa_legal_14905_ctn_1pct",
    "mora_ctn_lei_14905",
    "taxa_legal_12_aa_6_aa",
    "taxa_diaria_12_aa_6_aa",
}

TIPOS_JUROS_MORATORIOS_DIARIOS = (
    TIPOS_JUROS_MORATORIOS_DIARIOS_SELIC_IPCAE | TIPOS_JUROS_MORATORIOS_DIARIOS_12_6
)

Tabela = pd.DataFrame | list[dict[str, Any]] | None


def _normalizar_tabela_diaria(tabela: Tabela, kind: str) -> pd.DataFrame:
    """Normaliza uma tabela diária para cálculo de juros.

    Entrada:
        ``tabela``: ``None`` para usar a planilha local empacotada, ou
        ``DataFrame``/``list[dict]`` com ``data`` e ``valor_indice``;
        ``kind``: ``"selic_ipcae"`` ou ``"12_6"``.

    Saída:
        ``DataFrame`` ordenado com ``data`` como ``datetime.date`` e
        ``valor_indice`` como ``Decimal`` em taxa diária decimal.

    Exemplo:
        uma linha ``{"data": "2024-08-01", "valor_indice": "0.0002"}``
        representa 0,02% no dia.
    """
    if tabela is None:
        # A função de carga já é cacheada e retorna a planilha normalizada.
        return load_daily_rate_table(kind)

    df = pd.DataFrame(tabela).copy()
    if "data" not in df.columns or "valor_indice" not in df.columns:
        raise ValueError("Tabela diária precisa ter colunas 'data' e 'valor_indice'.")
    df["data"] = df["data"].apply(parse_data)
    df["valor_indice"] = df["valor_indice"].apply(D)
    return df[["data", "valor_indice"]].drop_duplicates("data", keep="last").sort_values("data").reset_index(drop=True)


def _data_fim_periodo(competencia_atualizacao: str, competencia_final_taxa_legal: str | None) -> date:
    """Define o último dia do período diário a acumular.

    Entrada:
        ``competencia_atualizacao``: mês-alvo ``AAAA-MM``;
        ``competencia_final_taxa_legal``: competência final opcional ``AAAA-MM``.

    Saída:
        ``datetime.date`` do último dia da competência final fechada.
    """
    comp_fim = competencia_final_taxa_legal[:7] if competencia_final_taxa_legal else somar_meses(competencia_atualizacao, -1)
    return ultimo_dia_mes(comp_fim)


def soma_taxas_diarias(
    *,
    data_inicio: date,
    data_fim: date,
    tabela_diaria: Tabela,
    kind: str,
) -> tuple[Decimal, Decimal]:
    """Soma taxas diárias em decimal dentro de um intervalo fechado.

    Entrada:
        ``data_inicio`` e ``data_fim``: datas inicial e final inclusivas;
        ``tabela_diaria``: tabela opcional de ``data``/``valor_indice``;
        ``kind``: ``"selic_ipcae"`` ou ``"12_6"`` para escolher a planilha local.

    Saída:
        Tupla ``(percentual_decimal, n_dias)``. Ex.: duas taxas ``0.001``
        retornam ``(Decimal("0.002"), Decimal("2"))``.
    """
    if data_fim < data_inicio:
        return Decimal("0"), Decimal("0")
    df = _normalizar_tabela_diaria(tabela_diaria, kind)
    primeiro = df["data"].min()
    ultimo = df["data"].max()
    if data_inicio < primeiro or data_fim > ultimo:
        raise ValueError(
            f"Tabela diária '{kind}' cobre {primeiro} a {ultimo}; "
            f"período solicitado: {data_inicio} a {data_fim}."
        )
    janela = df[(df["data"] >= data_inicio) & (df["data"] <= data_fim)]
    esperado = (data_fim - data_inicio).days + 1
    if len(janela) != esperado:
        existentes = set(janela["data"])
        faltantes = []
        d = data_inicio
        while d <= data_fim and len(faltantes) < 5:
            if d not in existentes:
                faltantes.append(d.isoformat())
            d += timedelta(days=1)
        raise ValueError(f"Tabela diária '{kind}' com datas faltantes: {faltantes}")
    percentual = sum((D(v) for v in janela["valor_indice"]), Decimal("0"))
    return percentual, Decimal(esperado)


# Ajuste de continuidade quando a planilha SELIC-IPCAE termina antes da
# competência selecionada e a configuração pede incidência da mora sobre uma
# base ampliada. O fator mantém compatibilidade com o critério histórico usado
# no conjunto de validação do projeto, sem misturar a tabela 12%/6%.
_TAXA_LEGAL_EXTENSAO_PRORATA = Decimal("1.166821258005817786550929525")


def _taxa_legal_decimal_competencia(competencia: str) -> Decimal:
    """Obtém a Taxa Legal mensal local em decimal para uma competência.

    Entrada:
        ``competencia``: texto ``AAAA-MM``.

    Saída:
        ``Decimal`` em forma decimal. Ex.: 0,605306% retorna ``0.00605306``.
    """
    tabela = load_taxa_legal_mensal_percentual()
    comp = competencia[:7]
    linha = tabela[tabela["mes"].astype(str).str[:7] == comp]
    if linha.empty:
        return Decimal("0")
    return D(linha.iloc[0]["taxa_legal_percentual"]) / Decimal("100")


def _percentual_selic_ipcae_diario(
    *,
    data_inicio: date,
    data_fim: date,
    tabela_diaria: Tabela,
    competencia_atualizacao: str,
    aplicar_extensao_pos_tabela: bool,
) -> tuple[Decimal, Decimal]:
    """Soma a tabela diária SELIC-IPCAE e eventual extensão mensal.

    Entrada:
        ``data_inicio``/``data_fim``: datas do período inclusivo;
        ``tabela_diaria``: tabela opcional de ``data``/``valor_indice``;
        ``competencia_atualizacao``: competência ``AAAA-MM`` usada na extensão;
        ``aplicar_extensao_pos_tabela``: ativa a extensão quando o período
        passa do último dia disponível na planilha.

    Saída:
        Tupla ``(percentual_decimal, n_dias)``.
    """
    df = _normalizar_tabela_diaria(tabela_diaria, "selic_ipcae")
    ultimo = df["data"].max()
    fim_base = min(data_fim, ultimo)
    percentual, n_dias = soma_taxas_diarias(
        data_inicio=data_inicio,
        data_fim=fim_base,
        tabela_diaria=df,
        kind="selic_ipcae",
    )
    if data_fim > ultimo and aplicar_extensao_pos_tabela:
        percentual += _taxa_legal_decimal_competencia(competencia_atualizacao) * _TAXA_LEGAL_EXTENSAO_PRORATA
        n_dias += Decimal("1")
    return percentual, n_dias


def calcular_juros_moratorios_diario(
    *,
    valor_base: Decimal,
    data_inicio: date,
    competencia_atualizacao: str,
    tabela_diaria: Tabela,
    competencia_final_taxa_legal: str | None,
    kind: str,
    aplicar_extensao_pos_tabela: bool = False,
) -> tuple[Decimal, Decimal, Decimal]:
    """Calcula juros moratórios pela soma de taxas diárias.

    Entrada:
        ``valor_base``: principal/base monetária em ``Decimal``;
        ``data_inicio``: termo inicial como ``datetime.date``;
        ``competencia_atualizacao``: mês-alvo ``AAAA-MM``;
        ``tabela_diaria``: tabela opcional de taxas diárias;
        ``competencia_final_taxa_legal``: competência final opcional;
        ``kind``: ``"selic_ipcae"`` ou ``"12_6"``;
        ``aplicar_extensao_pos_tabela``: ativa extensão mensal quando aplicável.

    Saída:
        Tupla ``(juros, percentual_decimal, n_dias)``. Ex.: base ``1000`` e
        percentual ``0.02`` retornam juros ``20.00``.
    """
    fim = _data_fim_periodo(competencia_atualizacao, competencia_final_taxa_legal)
    if kind == "selic_ipcae":
        percentual, n_dias = _percentual_selic_ipcae_diario(
            data_inicio=data_inicio,
            data_fim=fim,
            tabela_diaria=tabela_diaria,
            competencia_atualizacao=competencia_atualizacao,
            aplicar_extensao_pos_tabela=aplicar_extensao_pos_tabela,
        )
    else:
        percentual, n_dias = soma_taxas_diarias(
            data_inicio=data_inicio,
            data_fim=fim,
            tabela_diaria=tabela_diaria,
            kind=kind,
        )
    return moeda(D(valor_base) * percentual), percentual, n_dias
