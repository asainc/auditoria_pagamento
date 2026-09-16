from __future__ import annotations

from judicial_calc.core.dates import (
    competencia_data,
    competencias_entre,
    data_primeiro_dia,
    iter_competencias,
    parse_data,
    parse_mes_ano,
    somar_meses,
    ultimo_dia_mes,
)
from judicial_calc.core.numbers import D, moeda, percentual_taxa_legal
from judicial_calc.core.tables import normalizar_tabela_mensal
from judicial_calc.core.types import ResultadoCalculo
from judicial_calc.extraction.sgs import baixar_sgs
from judicial_calc.indices.base import fator_tabela_valor_mensal
from judicial_calc.indices.sgs_percentage import INDICES_SGS, fator_percentual_mensal, fator_percentual_mensal_por_tabela
from judicial_calc.interest.fixed import calcular_juros_fixo, meses_juros_simples
from judicial_calc.interest.service import calcular_juros
from judicial_calc.interest.taxa_legal import (
    TIPOS_JUROS_MORATORIOS_STJ1368,
    TIPOS_JUROS_MORATORIOS_CTN_LEI_14905,
    TIPOS_TAXA_LEGAL_OFICIAL,
    baixar_tabela_taxa_legal_oficial,
    gerar_tabela_taxa_legal,
    resolver_competencia_final_taxa_legal,
    soma_juros_moratorios_stj1368_lei_14905,
    soma_taxa_legal,
)
from judicial_calc.io.excel import salvar_resultado_excel
from judicial_calc.io.pdf import salvar_resultado_pdf
from judicial_calc.services.calculation_service import calcular_debitos, competencia_final_correcao, obter_fator_correcao

__all__ = [
    "D",
    "INDICES_SGS",
    "ResultadoCalculo",
    "TIPOS_JUROS_MORATORIOS_STJ1368",
    "TIPOS_JUROS_MORATORIOS_CTN_LEI_14905",
    "TIPOS_TAXA_LEGAL_OFICIAL",
    "baixar_sgs",
    "baixar_tabela_taxa_legal_oficial",
    "calcular_debitos",
    "calcular_juros",
    "calcular_juros_fixo",
    "competencia_data",
    "competencia_final_correcao",
    "competencias_entre",
    "data_primeiro_dia",
    "fator_percentual_mensal",
    "fator_percentual_mensal_por_tabela",
    "fator_tabela_valor_mensal",
    "gerar_tabela_taxa_legal",
    "iter_competencias",
    "meses_juros_simples",
    "moeda",
    "normalizar_tabela_mensal",
    "obter_fator_correcao",
    "parse_data",
    "parse_mes_ano",
    "percentual_taxa_legal",
    "resolver_competencia_final_taxa_legal",
    "salvar_resultado_excel",
    "salvar_resultado_pdf",
    "soma_juros_moratorios_stj1368_lei_14905",
    "soma_taxa_legal",
    "somar_meses",
    "ultimo_dia_mes",
]
