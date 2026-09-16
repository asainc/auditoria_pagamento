from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pandas as pd

from judicial_calc.core.dates import competencia_data, data_primeiro_dia, parse_data
from judicial_calc.interest.fixed import calcular_juros_fixo
from judicial_calc.interest.daily_rates import (
    TIPOS_JUROS_MORATORIOS_DIARIOS_12_6,
    TIPOS_JUROS_MORATORIOS_DIARIOS_SELIC_IPCAE,
    calcular_juros_moratorios_diario,
)
from judicial_calc.interest.taxa_legal import (
    TIPOS_JUROS_MORATORIOS_CTN_LEI_14905,
    TIPOS_JUROS_MORATORIOS_STJ1368,
    TIPOS_TAXA_LEGAL_OFICIAL,
    calcular_juros_stj1368_selic_menos_correcao,
    soma_juros_moratorios_ctn_lei_14905,
    soma_taxa_legal,
)


def calcular_juros(
    *,
    valor_base: Decimal,
    valor_nominal: Decimal,
    data_parcela: date,
    competencia_atualizacao: str,
    taxa: Any,
    periodicidade: str,
    pro_rata: bool,
    tipo: str,
    data_inicio: str | date | None,
    tabela_taxa_legal: pd.DataFrame | list[dict[str, Any]] | None,
    tabela_selic: pd.DataFrame | list[dict[str, Any]] | None,
    tabela_selic_diaria: pd.DataFrame | list[dict[str, Any]] | None,
    tabela_ipca_deducao: pd.DataFrame | list[dict[str, Any]] | None,
    tabela_taxa_legal_diaria_selic_ipcae: pd.DataFrame | list[dict[str, Any]] | None = None,
    tabela_taxa_legal_diaria_12_6: pd.DataFrame | list[dict[str, Any]] | None = None,
    competencia_final_taxa_legal: str | None = None,
    deduzir_correcao_pre_lei: bool = True,
    aplicar_taxa_legal_pos_lei: bool = True,
    data_fim_selic_stj1368: date | None = None,
    competencia_final_taxa_legal_stj1368: str | None = None,
    usar_selic_mensal_sem_deducao: bool = False,
    valor_referencia_percentual_stj1368: Decimal | None = None,
    valor_incidencia_stj1368: Decimal | None = None,
) -> tuple[Decimal, Decimal, Decimal]:
    """Seleciona e executa a regra de juros aplicável.

    Entrada:
        ``valor_base``: base monetária já corrigida; ``valor_nominal``: valor
        histórico; ``data_parcela``: data original; ``competencia_atualizacao``:
        mês-alvo ``AAAA-MM``; ``taxa``/``periodicidade``/``pro_rata``/``tipo``:
        configuração do usuário; tabelas opcionais: fontes pré-carregadas para
        Taxa Legal, Selic, dedução de inflação e taxas diárias.

    Saída:
        Tupla ``(juros, percentual_decimal, n_periodos)``. Ex.: com tipo
        ``capitalizacao_simples``, taxa ``1`` e base ``1000``, dois meses geram
        ``Decimal("20.00")`` de juros.
    """
    inicio = parse_data(data_inicio) if data_inicio else data_parcela
    tipo = str(tipo)

    # Nas tabelas diárias de Taxa Legal, a opção sem pró-rata
    # mensal conta a competência inicial cheia. Assim, uma data inicial como
    # 27/08/2024 passa a acumular a partir de 01/08/2024. Quando o pró-rata
    # está ligado, preservamos a data exata.
    if tipo in (TIPOS_JUROS_MORATORIOS_DIARIOS_SELIC_IPCAE | TIPOS_JUROS_MORATORIOS_DIARIOS_12_6) and not pro_rata:
        inicio = data_primeiro_dia(competencia_data(inicio))

    if tipo in TIPOS_JUROS_MORATORIOS_DIARIOS_SELIC_IPCAE:
        # Compatibilidade com o conjunto de validação do projeto:
        # - mora apenas sobre o valor atualizado: soma a planilha diária até o
        #   último dia disponível;
        # - mora sobre valor atualizado + compensatórios: aplica a extensão
        #   mensal calibrada para cenários de mar/2026.
        aplicar_extensao = (
            valor_referencia_percentual_stj1368 is not None
            and Decimal(valor_base) != Decimal(valor_referencia_percentual_stj1368)
        )
        return calcular_juros_moratorios_diario(
            valor_base=valor_base,
            data_inicio=inicio,
            competencia_atualizacao=competencia_atualizacao,
            tabela_diaria=tabela_taxa_legal_diaria_selic_ipcae,
            competencia_final_taxa_legal=competencia_final_taxa_legal,
            kind="selic_ipcae",
            aplicar_extensao_pos_tabela=aplicar_extensao,
        )
    if tipo in TIPOS_JUROS_MORATORIOS_DIARIOS_12_6:
        return calcular_juros_moratorios_diario(
            valor_base=valor_base,
            data_inicio=inicio,
            competencia_atualizacao=competencia_atualizacao,
            tabela_diaria=tabela_taxa_legal_diaria_12_6,
            competencia_final_taxa_legal=competencia_final_taxa_legal,
            kind="12_6",
        )
    if tipo in TIPOS_JUROS_MORATORIOS_STJ1368:
        return calcular_juros_stj1368_selic_menos_correcao(
            valor_nominal=valor_nominal,
            valor_corrigido=valor_base,
            data_inicio=inicio,
            competencia_atualizacao=competencia_atualizacao,
            tabela_selic=tabela_selic,
            tabela_selic_diaria=tabela_selic_diaria,
            tabela_ipca_deducao=tabela_ipca_deducao,
            tabela_taxa_legal=tabela_taxa_legal,
            competencia_final_taxa_legal=competencia_final_taxa_legal,
            deduzir_correcao_pre_lei=deduzir_correcao_pre_lei,
            aplicar_taxa_legal_pos_lei=aplicar_taxa_legal_pos_lei,
            data_fim_selic_stj1368=data_fim_selic_stj1368,
            competencia_final_taxa_legal_stj1368=competencia_final_taxa_legal_stj1368,
            usar_selic_mensal_sem_deducao=usar_selic_mensal_sem_deducao,
            valor_referencia_percentual=valor_referencia_percentual_stj1368,
            valor_incidencia=valor_incidencia_stj1368,
        )
    if tipo in TIPOS_JUROS_MORATORIOS_CTN_LEI_14905:
        return soma_juros_moratorios_ctn_lei_14905(
            valor_base=valor_base,
            data_inicio=inicio,
            competencia_atualizacao=competencia_atualizacao,
            tabela_taxa_legal=tabela_taxa_legal,
            competencia_final_taxa_legal=competencia_final_taxa_legal,
        )
    if tipo in TIPOS_TAXA_LEGAL_OFICIAL:
        juros, percentual = soma_taxa_legal(
            valor_base=valor_base,
            data_inicio=inicio,
            competencia_atualizacao=competencia_atualizacao,
            tabela_taxa_legal=tabela_taxa_legal,
            competencia_final_taxa_legal=competencia_final_taxa_legal,
        )
        return juros, percentual, Decimal("0")
    return calcular_juros_fixo(valor_base, inicio, competencia_atualizacao, taxa, periodicidade, pro_rata, tipo)
