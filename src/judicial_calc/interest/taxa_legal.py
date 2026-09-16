"""Juros legais especiais usados para replicar opções do critério de referência.

Este módulo concentra os cálculos que não são juros simples/compostos comuns:

1. Taxa Legal oficial da Lei 14.905/2024, divulgada mensalmente pelo
   Bacen na série SGS 29543.
2. Opção critério de referência "Taxa Legal + STJ Tema 1368 (SELIC - IPCA)".
3. Opção histórica alternativa "6% a.a. / 12% a.a. + Taxa Legal".

Todas as taxas vêm de APIs oficiais do Bacen/SGS ou de tabelas passadas pelo
usuário. Não há fatores ou percentuais fixados para reproduzir casos isolados.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Iterable

import pandas as pd

from judicial_calc.core.constants import INICIO_SERIE_OFICIAL_TAXA_LEGAL, SGS_TAXA_LEGAL
from judicial_calc.core.dates import (
    competencia_data,
    competencias_entre,
    iter_competencias,
    parse_data,
    somar_meses,
    ultimo_dia_mes,
)
from judicial_calc.core.numbers import D, moeda, percentual_taxa_legal
from judicial_calc.core.tables import normalizar_tabela_mensal
from judicial_calc.extraction.sgs import baixar_sgs, baixar_sgs_diario

# ---------------------------------------------------------------------------
# Séries oficiais Bacen/SGS usadas pelo projeto
# ---------------------------------------------------------------------------
SGS_SELIC_DIARIA = 11          # Taxa de juros Selic diária, em % a.d.
SGS_SELIC_MENSAL = 4390        # Selic acumulada no mês, em % a.m.
SGS_IPCA = 433                 # IPCA mensal, em % a.m.
SGS_IPCA_15 = 7478             # IPCA-15 mensal, em % a.m.
SGS_INPC = 188                 # INPC mensal, em % a.m.

# ---------------------------------------------------------------------------
# Marcos jurídicos e competências de transição
# ---------------------------------------------------------------------------
COMPETENCIA_INICIO_CC_2002 = "2003-01"
COMPETENCIA_INICIO_TAXA_LEGAL = INICIO_SERIE_OFICIAL_TAXA_LEGAL  # 2024-08
COMPETENCIA_FIM_STJ1368_DEDUCAO_CORRECAO = somar_meses(COMPETENCIA_INICIO_TAXA_LEGAL, -1)  # 2024-07

# Para índices com dedução de correção, o trecho de Selic pré-Lei encerra em
# 30/08/2024. Para IGP-M, o comportamento observado no critério de referência usa a Selic
# mensal até 09/2024 e limita a Taxa Legal à janela transitória 08-09/2024.
DATA_FIM_STJ1368_SELIC_COM_DEDUCAO = date(2024, 8, 30)
DATA_FIM_STJ1368_SELIC_SEM_DEDUCAO = date(2024, 9, 30)
COMPETENCIA_FIM_TAXA_LEGAL_STJ1368_SEM_DEDUCAO = "2024-09"

TAXA_CC_1916_MENSAL = Decimal("0.005")   # 6% ao ano / 12
TAXA_CC_2002_CTN_MENSAL = Decimal("0.01")  # 12% ao ano / 12

# ---------------------------------------------------------------------------
# Tipos aceitos na API pública do projeto
# ---------------------------------------------------------------------------
TIPOS_TAXA_LEGAL_OFICIAL = {
    "taxa_legal_14905",
    "taxa_legal_14905_bcb",
    "taxa_legal_14905_oficial",
}

TIPOS_JUROS_MORATORIOS_STJ1368 = {
    "taxa_legal_14905_stj1368",
    "taxa_legal_14905_tema_1368",
    "juros_moratorios_stj1368_lei_14905",
    "juros_moratorios_stj1368_lei_14905",
    "mora_stj1368_lei_14905",
}

TIPOS_JUROS_MORATORIOS_CTN_LEI_14905 = {
    "juros_moratorios_ctn_lei_14905",
    "taxa_legal_14905_ctn_1pct",
    "mora_ctn_lei_14905",
}

TIPOS_QUE_USAM_TAXA_LEGAL = (
    TIPOS_TAXA_LEGAL_OFICIAL
    | TIPOS_JUROS_MORATORIOS_STJ1368
    | TIPOS_JUROS_MORATORIOS_CTN_LEI_14905
)

# Índices que, no seletor STJ 1368 do critério de referência, deduzem correção no trecho
# pré-Lei. O valor é o código SGS da correção a deduzir. Quando o valor é
# None, a opção observada no critério de referência usa Selic integral no trecho pré-Lei.
INDICE_SGS_DEDUCAO_TAXA_LEGAL = {
    "ipca_ibge": SGS_IPCA,
    "ipca_15_ibge": SGS_IPCA_15,
    "inpc_ibge": SGS_INPC,
    "igp_m_fgv": None,
}

INDICES_STJ1368_SEM_DEDUCAO_CORRECAO = {
    indice for indice, codigo_sgs in INDICE_SGS_DEDUCAO_TAXA_LEGAL.items() if codigo_sgs is None
}

Tabela = pd.DataFrame | list[dict[str, Any]] | None


# ---------------------------------------------------------------------------
# Helpers de normalização e acumulação
# ---------------------------------------------------------------------------
def _normalizar_percentual_mensal(tabela: pd.DataFrame | list[dict[str, Any]], coluna: str) -> pd.DataFrame:
    """Normaliza uma tabela mensal percentual.

    Entrada aceita:
        DataFrame ou lista de dicionários com coluna ``mes`` no formato
        ``AAAA-MM`` e coluna de valor percentual informada em ``coluna``.
        Se a coluna preferida não existir, a função aceita ``valor``.

    Saída:
        DataFrame com ``mes`` e ``coluna`` ordenado e sem duplicidade mensal.
    """
    df = pd.DataFrame(tabela).copy()
    coluna_origem = coluna if coluna in df.columns else "valor"
    if "mes" not in df.columns or coluna_origem not in df.columns:
        raise ValueError(f"Tabela precisa ter coluna 'mes' e '{coluna}' ou 'valor'.")
    df["mes"] = df["mes"].astype(str).str[:7]
    df[coluna] = df[coluna_origem].apply(D)
    return df[["mes", coluna]].drop_duplicates("mes", keep="last").sort_values("mes").reset_index(drop=True)


def _normalizar_selic_diaria(tabela: pd.DataFrame | list[dict[str, Any]]) -> pd.DataFrame:
    """Normaliza tabela diária da Selic.

    Entrada aceita:
        DataFrame/lista com ``data`` em ``YYYY-MM-DD`` ou ``DD/MM/YYYY`` e
        coluna ``selic_diaria`` ou ``valor`` em percentual ao dia.

    Saída:
        DataFrame com ``data`` como ``datetime.date`` e ``selic_diaria`` como
        Decimal percentual ao dia.
    """
    df = pd.DataFrame(tabela).copy()
    coluna = "selic_diaria" if "selic_diaria" in df.columns else "valor"
    if "data" not in df.columns or coluna not in df.columns:
        raise ValueError("Tabela Selic diária precisa ter colunas 'data' e 'selic_diaria' ou 'valor'.")
    df["data"] = df["data"].apply(parse_data)
    df["selic_diaria"] = df[coluna].apply(D)
    return df[["data", "selic_diaria"]].drop_duplicates("data", keep="last").sort_values("data").reset_index(drop=True)


def _mapa_mensal(tabela: pd.DataFrame, coluna: str) -> dict[str, Decimal]:
    """Converte tabela mensal normalizada em dicionário ``{AAAA-MM: Decimal}``."""
    return dict(zip(tabela["mes"], tabela[coluna]))


def _acumular_percentuais_mensais(comps: Iterable[str], mapa: dict[str, Decimal], nome: str) -> Decimal:
    """Acumula percentuais mensais em fator composto.

    Cada valor da tabela é percentual, por exemplo ``0.83`` para 0,83%.
    Retorna um fator, por exemplo ``1.0083``.
    """
    fator = Decimal("1")
    for comp in comps:
        if comp not in mapa:
            raise ValueError(f"Tabela {nome} sem competência {comp}.")
        fator *= Decimal("1") + mapa[comp] / Decimal("100")
    return fator


# ---------------------------------------------------------------------------
# Download/geração das tabelas oficiais
# ---------------------------------------------------------------------------
def baixar_tabela_taxa_legal_oficial(inicio: str, fim: str) -> pd.DataFrame:
    """Baixa a Taxa Legal oficial do Bacen/SGS 29543.

    Parâmetros:
        inicio, fim: competências no formato ``AAAA-MM``.

    Resultado:
        DataFrame com ``mes`` e ``taxa_legal_percentual``.
    """
    inicio = max(inicio[:7], INICIO_SERIE_OFICIAL_TAXA_LEGAL)
    fim = fim[:7]
    if fim < inicio:
        return pd.DataFrame(columns=["mes", "taxa_legal_percentual"])
    return baixar_sgs(SGS_TAXA_LEGAL, "taxa_legal_percentual", inicio, fim)


def gerar_tabela_taxa_legal(inicio: str, fim: str) -> pd.DataFrame:
    """Gera tabela mensal da Taxa Legal usando exclusivamente SGS 29543."""
    tabela = baixar_tabela_taxa_legal_oficial(inicio, fim)
    return tabela if tabela.empty else normalizar_tabela_mensal(tabela, "taxa_legal_percentual")


def baixar_tabela_selic_mensal(inicio: str, fim: str) -> pd.DataFrame:
    """Baixa Selic mensal acumulada no mês, SGS 4390."""
    if fim < inicio:
        return pd.DataFrame(columns=["mes", "selic_mensal"])
    return baixar_sgs(SGS_SELIC_MENSAL, "selic_mensal", inicio, fim)


def baixar_tabela_selic_diaria(data_inicio: date, data_fim: date) -> pd.DataFrame:
    """Baixa Selic diária, SGS 11, preservando todas as datas da série."""
    if data_fim < data_inicio:
        return pd.DataFrame(columns=["data", "selic_diaria"])
    return baixar_sgs_diario(SGS_SELIC_DIARIA, "selic_diaria", data_inicio, data_fim)


def baixar_tabela_ipca_deducao(inicio: str, fim: str, codigo_sgs: int = SGS_IPCA_15) -> pd.DataFrame:
    """Baixa a inflação usada como dedução no modo STJ 1368.

    ``codigo_sgs`` permite usar IPCA, IPCA-15 ou INPC conforme o índice de
    correção principal. Para IGP-M, esta função não é chamada pelo serviço de
    cálculo porque o critério de referência usa Selic integral no trecho pré-Lei.
    """
    if fim < inicio:
        return pd.DataFrame(columns=["mes", "ipca_deducao"])
    return baixar_sgs(codigo_sgs, "ipca_deducao", inicio, fim)


# ---------------------------------------------------------------------------
# Funções de acumulação de fatores
# ---------------------------------------------------------------------------
def resolver_competencia_final_taxa_legal(
    competencia_atualizacao: str,
    competencia_final_taxa_legal: str | None,
) -> str:
    """Resolve a última competência usada em juros/Taxa Legal.

    Por padrão, atualização em ``2026-03`` usa índices conhecidos até
    ``2026-02``. O parâmetro ``competencia_final_taxa_legal`` pode limitar
    manualmente esse fim, útil para testes ou reprodução de telas específicas.
    """
    return competencia_final_taxa_legal[:7] if competencia_final_taxa_legal else somar_meses(competencia_atualizacao, -1)


def _tabela_taxa_legal(inicio: str, fim: str, tabela_taxa_legal: Tabela) -> pd.DataFrame:
    """Obtém tabela mensal da Taxa Legal para o intervalo solicitado.

    Entrada:
        ``inicio`` e ``fim``: competências ``AAAA-MM``; ``tabela_taxa_legal``:
        tabela opcional com ``mes`` e ``taxa_legal_percentual``.

    Saída:
        ``DataFrame`` com ``mes`` e ``taxa_legal_percentual`` filtrado.
    """
    if tabela_taxa_legal is not None:
        tabela = normalizar_tabela_mensal(tabela_taxa_legal, "taxa_legal_percentual")
        return tabela[(tabela["mes"] >= inicio) & (tabela["mes"] <= fim)].reset_index(drop=True)
    return gerar_tabela_taxa_legal(inicio, fim)


def _somar_taxa_legal_percentual(inicio: str, fim: str, tabela_taxa_legal: Tabela) -> Decimal:
    """Soma percentuais mensais da Taxa Legal em regime simples."""
    if fim < inicio:
        return Decimal("0")
    tabela = _tabela_taxa_legal(inicio, fim, tabela_taxa_legal)
    mapa = _mapa_mensal(tabela, "taxa_legal_percentual")
    return sum((mapa[comp] / Decimal("100") for comp in iter_competencias(inicio, fim)), Decimal("0"))


def soma_taxa_legal(
    *,
    valor_base: Decimal,
    data_inicio: date,
    competencia_atualizacao: str,
    tabela_taxa_legal: Tabela,
    competencia_final_taxa_legal: str | None,
) -> tuple[Decimal, Decimal]:
    """Calcula juros usando somente a Taxa Legal oficial.

    Entrada:
        ``valor_base`` já deve ser o valor sobre o qual a Taxa Legal incide.
        ``data_inicio`` é a data da parcela ou da mora.

    Saída:
        ``(valor_juros, percentual_decimal)``. Ex.: 2% retorna percentual
        ``Decimal('0.02')``.
    """
    inicio = max(competencia_data(data_inicio), COMPETENCIA_INICIO_TAXA_LEGAL)
    fim = resolver_competencia_final_taxa_legal(competencia_atualizacao, competencia_final_taxa_legal)
    percentual = percentual_taxa_legal(_somar_taxa_legal_percentual(inicio, fim, tabela_taxa_legal))
    return moeda(valor_base * percentual), percentual


def fator_selic_mensal(inicio: str, fim: str, tabela_selic: Tabela) -> Decimal:
    """Acumula a Selic mensal SGS 4390 entre duas competências."""
    if fim < inicio:
        return Decimal("1")
    tabela = _normalizar_percentual_mensal(tabela_selic, "selic_mensal") if tabela_selic is not None else baixar_tabela_selic_mensal(inicio, fim)
    return _acumular_percentuais_mensais(iter_competencias(inicio, fim), _mapa_mensal(tabela, "selic_mensal"), "Selic")


def fator_selic_mensal_local_sem_deducao(inicio: str, fim: str, tabela_selic: Tabela) -> Decimal:
    """Acumula Selic mensal no padrão observado para IGP-M no critério de referência.

    O fator acumulado é arredondado a 4 casas nas competências intermediárias,
    preservando a última competência para o arredondamento monetário final.
    """
    if fim < inicio:
        return Decimal("1")
    tabela = _normalizar_percentual_mensal(tabela_selic, "selic_mensal") if tabela_selic is not None else baixar_tabela_selic_mensal(inicio, fim)
    mapa = _mapa_mensal(tabela, "selic_mensal")
    comps = list(iter_competencias(inicio, fim))
    fator = Decimal("1")
    for i, comp in enumerate(comps):
        if comp not in mapa:
            raise ValueError(f"Tabela Selic sem competência {comp}.")
        fator *= Decimal("1") + mapa[comp] / Decimal("100")
        if i < len(comps) - 1:
            fator = fator.quantize(Decimal("0.0001"))
    return fator


def fator_selic_diaria(data_inicio: date, data_fim: date, tabela_selic_diaria: Tabela) -> Decimal:
    """Acumula Selic diária SGS 11 entre duas datas, inclusive."""
    if data_fim < data_inicio:
        return Decimal("1")
    tabela = _normalizar_selic_diaria(tabela_selic_diaria) if tabela_selic_diaria is not None else baixar_tabela_selic_diaria(data_inicio, data_fim)
    tabela = tabela[(tabela["data"] >= data_inicio) & (tabela["data"] <= data_fim)]
    if tabela.empty:
        raise ValueError(f"Tabela Selic diária sem dados entre {data_inicio} e {data_fim}.")
    fator = Decimal("1")
    for taxa in tabela["selic_diaria"]:
        fator *= Decimal("1") + D(taxa) / Decimal("100")
    return fator


def fator_ipca_deducao(inicio: str, fim: str, tabela_ipca_deducao: Tabela) -> Decimal:
    """Acumula a inflação mensal deduzida no modo SELIC - correção."""
    if fim < inicio:
        return Decimal("1")
    tabela = _normalizar_percentual_mensal(tabela_ipca_deducao, "ipca_deducao") if tabela_ipca_deducao is not None else baixar_tabela_ipca_deducao(inicio, fim)
    return _acumular_percentuais_mensais(iter_competencias(inicio, fim), _mapa_mensal(tabela, "ipca_deducao"), "IPCA dedução")


# ---------------------------------------------------------------------------
# Cálculo STJ 1368 / critério de referência
# ---------------------------------------------------------------------------
def _fator_selic_pre_lei(
    *,
    data_inicio: date,
    data_fim_selic: date,
    tabela_selic: Tabela,
    tabela_selic_diaria: Tabela,
    usar_selic_mensal_sem_deducao: bool,
) -> Decimal:
    """Escolhe a série Selic correta para o trecho pré-Lei."""
    if usar_selic_mensal_sem_deducao:
        inicio = somar_meses(competencia_data(data_inicio), 1)
        fim = competencia_data(data_fim_selic)
        return fator_selic_mensal_local_sem_deducao(inicio, fim, tabela_selic)
    if tabela_selic_diaria is not None or tabela_selic is None:
        return fator_selic_diaria(data_inicio, data_fim_selic, tabela_selic_diaria)
    # Fallback offline: usado apenas se o chamador fornecer Selic mensal e não
    # fornecer Selic diária. Em produção, o serviço pré-carrega SGS 11.
    return fator_selic_mensal(competencia_data(data_inicio), competencia_data(data_fim_selic), tabela_selic)


def _juros_pre_lei_stj1368(
    *,
    valor_nominal: Decimal,
    data_inicio: date,
    data_fim_selic: date,
    fim_deducao_correcao: str,
    tabela_selic: Tabela,
    tabela_selic_diaria: Tabela,
    tabela_ipca_deducao: Tabela,
    deduzir_correcao_pre_lei: bool,
    usar_selic_mensal_sem_deducao: bool,
) -> Decimal:
    """Calcula o trecho pré-Lei como diferença de montantes.

    Resultado:
        ``valor_nominal * (fator_selic - fator_correcao)``.
        Quando não há dedução de correção, ``fator_correcao = 1``.
    """
    if data_fim_selic < data_inicio:
        return Decimal("0")
    fator_selic = _fator_selic_pre_lei(
        data_inicio=data_inicio,
        data_fim_selic=data_fim_selic,
        tabela_selic=tabela_selic,
        tabela_selic_diaria=tabela_selic_diaria,
        usar_selic_mensal_sem_deducao=usar_selic_mensal_sem_deducao,
    )
    inicio_deducao = competencia_data(data_inicio)
    fator_correcao = (
        fator_ipca_deducao(inicio_deducao, fim_deducao_correcao, tabela_ipca_deducao)
        if deduzir_correcao_pre_lei and fim_deducao_correcao >= inicio_deducao
        else Decimal("1")
    )
    return max(valor_nominal * (fator_selic - fator_correcao), Decimal("0"))


def calcular_juros_stj1368_selic_menos_correcao(
    *,
    valor_nominal: Decimal,
    valor_corrigido: Decimal,
    data_inicio: date,
    competencia_atualizacao: str,
    tabela_selic: Tabela,
    tabela_selic_diaria: Tabela,
    tabela_ipca_deducao: Tabela,
    tabela_taxa_legal: Tabela,
    competencia_final_taxa_legal: str | None,
    deduzir_correcao_pre_lei: bool = True,
    aplicar_taxa_legal_pos_lei: bool = True,
    data_fim_selic_stj1368: date | None = None,
    competencia_final_taxa_legal_stj1368: str | None = None,
    usar_selic_mensal_sem_deducao: bool = False,
    valor_referencia_percentual: Decimal | None = None,
    valor_incidencia: Decimal | None = None,
) -> tuple[Decimal, Decimal, Decimal]:
    """Replica o seletor critério de referência "Taxa Legal + STJ Tema 1368".

    Entrada principal:
        ``valor_nominal``: valor histórico da parcela.
        ``valor_corrigido``: valor após correção monetária do principal, usado
        como referência padrão para transformar o montante SELIC/IPCA em
        percentual equivalente.
        ``valor_referencia_percentual``: referência opcional para calcular o
        percentual equivalente. O serviço usa esta entrada quando os juros
        moratórios devem incidir também sobre juros compensatórios: o percentual
        do Tema 1368 é apurado sobre o principal corrigido, mas aplicado sobre
        a base ampliada.
        ``valor_incidencia``: base opcional sobre a qual o percentual
        equivalente será aplicado.
        ``data_inicio``: data da parcela ou da mora.
        ``competencia_atualizacao``: mês-alvo ``AAAA-MM``.

    Resultado:
        ``(juros, percentual_equivalente, n_competencias)``.

    Regras implementadas:
        * índices com dedução: Selic diária SGS 11 menos inflação mensal de
          dedução até 2024-07, depois Taxa Legal SGS 29543;
        * IGP-M: Selic mensal SGS 4390 até 2024-09, sem dedução de inflação,
          e Taxa Legal limitada às competências 2024-08 e 2024-09.
    """
    fim = resolver_competencia_final_taxa_legal(competencia_atualizacao, competencia_final_taxa_legal)
    if fim < competencia_data(data_inicio):
        return Decimal("0.00"), Decimal("0"), Decimal("0")

    data_fim_selic = min(ultimo_dia_mes(fim), data_fim_selic_stj1368 or DATA_FIM_STJ1368_SELIC_COM_DEDUCAO)
    fim_deducao = min(fim, COMPETENCIA_FIM_STJ1368_DEDUCAO_CORRECAO)

    juros_pre_lei = _juros_pre_lei_stj1368(
        valor_nominal=valor_nominal,
        data_inicio=data_inicio,
        data_fim_selic=data_fim_selic,
        fim_deducao_correcao=fim_deducao,
        tabela_selic=tabela_selic,
        tabela_selic_diaria=tabela_selic_diaria,
        tabela_ipca_deducao=tabela_ipca_deducao,
        deduzir_correcao_pre_lei=deduzir_correcao_pre_lei,
        usar_selic_mensal_sem_deducao=usar_selic_mensal_sem_deducao,
    )
    n_pre = Decimal(competencias_entre(competencia_data(data_inicio), somar_meses(competencia_data(data_fim_selic), 1))) if data_fim_selic >= data_inicio else Decimal("0")

    pos_inicio = max(competencia_data(data_inicio), COMPETENCIA_INICIO_TAXA_LEGAL)
    pos_fim = fim if competencia_final_taxa_legal_stj1368 is None else min(fim, competencia_final_taxa_legal_stj1368[:7])
    percentual_pos = _somar_taxa_legal_percentual(pos_inicio, pos_fim, tabela_taxa_legal) if aplicar_taxa_legal_pos_lei else Decimal("0")
    juros_pos_lei = valor_nominal * percentual_taxa_legal(percentual_pos)
    n_pos = Decimal(competencias_entre(pos_inicio, somar_meses(pos_fim, 1))) if aplicar_taxa_legal_pos_lei and pos_fim >= pos_inicio else Decimal("0")

    # O montante bruto é calculado uma única vez com base nas séries oficiais.
    # Em seguida ele é convertido em percentual equivalente. Isso permite
    # reproduzir o checkbox do critério de referência "juros moratórios sobre compensatórios":
    # o percentual legal continua sendo apurado sobre o principal corrigido,
    # mas pode incidir sobre uma base maior, composta por principal corrigido +
    # juros compensatórios.
    juros_brutos = juros_pre_lei + juros_pos_lei
    referencia = D(valor_referencia_percentual) if valor_referencia_percentual is not None else D(valor_corrigido)
    base_incidencia = D(valor_incidencia) if valor_incidencia is not None else D(valor_corrigido)
    percentual = Decimal("0") if referencia == 0 else percentual_taxa_legal(juros_brutos / referencia)
    juros = moeda(base_incidencia * percentual)
    return juros, percentual, n_pre + n_pos


# ---------------------------------------------------------------------------
# Critério histórico alternativo: 6% a.a. / 12% a.a. + Taxa Legal
# ---------------------------------------------------------------------------
def _percentual_juros_fixos_legais(data_inicio: date, competencia_atualizacao: str) -> tuple[Decimal, Decimal]:
    """Calcula o trecho fixo histórico anterior à Taxa Legal.

    Retorna ``(percentual_decimal, numero_de_competencias)`` em juros simples.
    """
    inicio = competencia_data(data_inicio)
    fim_pre_tl = min(somar_meses(competencia_atualizacao, -1), somar_meses(COMPETENCIA_INICIO_TAXA_LEGAL, -1))
    if fim_pre_tl < inicio:
        return Decimal("0"), Decimal("0")

    percentual = Decimal("0")
    n_total = Decimal("0")

    fim_cc_1916 = min(fim_pre_tl, somar_meses(COMPETENCIA_INICIO_CC_2002, -1))
    if fim_cc_1916 >= inicio:
        n = Decimal(competencias_entre(inicio, somar_meses(fim_cc_1916, 1)))
        percentual += TAXA_CC_1916_MENSAL * n
        n_total += n

    inicio_cc_2002 = max(inicio, COMPETENCIA_INICIO_CC_2002)
    if fim_pre_tl >= inicio_cc_2002:
        n = Decimal(competencias_entre(inicio_cc_2002, somar_meses(fim_pre_tl, 1)))
        percentual += TAXA_CC_2002_CTN_MENSAL * n
        n_total += n

    return percentual, n_total


def soma_juros_moratorios_ctn_lei_14905(
    *,
    valor_base: Decimal,
    data_inicio: date,
    competencia_atualizacao: str,
    tabela_taxa_legal: Tabela,
    competencia_final_taxa_legal: str | None,
) -> tuple[Decimal, Decimal, Decimal]:
    """Calcula a opção histórica 6%/12% a.a. + Taxa Legal.

    ``valor_base`` normalmente é o valor já corrigido da parcela.
    """
    percentual_fixo, n_fixo = _percentual_juros_fixos_legais(data_inicio, competencia_atualizacao)
    inicio_tl = max(competencia_data(data_inicio), COMPETENCIA_INICIO_TAXA_LEGAL)
    fim_tl = resolver_competencia_final_taxa_legal(competencia_atualizacao, competencia_final_taxa_legal)
    percentual_tl = _somar_taxa_legal_percentual(inicio_tl, fim_tl, tabela_taxa_legal)
    n_tl = Decimal(competencias_entre(inicio_tl, somar_meses(fim_tl, 1))) if fim_tl >= inicio_tl else Decimal("0")
    percentual = percentual_taxa_legal(percentual_fixo + percentual_tl)
    return moeda(valor_base * percentual), percentual, n_fixo + n_tl


def soma_juros_moratorios_stj1368_lei_14905(**kwargs: Any) -> tuple[Decimal, Decimal, Decimal]:
    """Atalho para o cálculo STJ 1368 com SELIC menos correção.

    Entrada:
        ``kwargs``: mesmos argumentos de
        ``calcular_juros_stj1368_selic_menos_correcao``.

    Saída:
        Tupla ``(juros, percentual_decimal, n_competencias)``.
    """
    return calcular_juros_stj1368_selic_menos_correcao(**kwargs)
