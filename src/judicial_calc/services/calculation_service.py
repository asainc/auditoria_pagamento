"""Orquestração do cálculo de atualização de débitos judiciais.

Este módulo é a camada de serviço: recebe parcelas e parâmetros, carrega as
séries oficiais necessárias uma única vez e calcula cada linha da memória de
cálculo. A regra de negócio específica de juros fica nos módulos de ``interest``;
aqui ficam a preparação dos dados e a composição do resultado final.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import os
from decimal import Decimal
from typing import Any

import pandas as pd

from judicial_calc.core.dates import competencia_data, parse_data, somar_meses
from judicial_calc.core.errors import CalculationValidationError
from judicial_calc.core.numbers import D, moeda
from judicial_calc.core.types import ResultadoCalculo
from judicial_calc.extraction.sgs import baixar_sgs
from judicial_calc.indices.registry import resolve_index_strategy
from judicial_calc.indices.sgs_percentage import INDICES_SGS, SGSPercentageCorrectionIndex
from judicial_calc.data_sources.local_excel import load_taxa_legal_mensal_percentual
from judicial_calc.data_sources.drcalc_updater import atualizar_planilhas_drcalc_se_necessario
from judicial_calc.interest.service import calcular_juros
from judicial_calc.interest.taxa_legal import (
    COMPETENCIA_FIM_TAXA_LEGAL_STJ1368_SEM_DEDUCAO,
    DATA_FIM_STJ1368_SELIC_COM_DEDUCAO,
    DATA_FIM_STJ1368_SELIC_SEM_DEDUCAO,
    INDICE_SGS_DEDUCAO_TAXA_LEGAL,
    TIPOS_JUROS_MORATORIOS_CTN_LEI_14905,
    TIPOS_JUROS_MORATORIOS_STJ1368,
    TIPOS_TAXA_LEGAL_OFICIAL,
    baixar_tabela_ipca_deducao,
    baixar_tabela_selic_diaria,
    baixar_tabela_selic_mensal,
    resolver_competencia_final_taxa_legal,
)

from judicial_calc.services.calculation_parameters import CalculoParams, FaixaDuploIndice, _normalizar_inteiro_flexivel
from judicial_calc.services.calculation_adjustments import (
    _aplicar_compensacao_na_memoria,
)
from judicial_calc.services.calculation_penalties import _aplicar_art_523_na_memoria, _calcular_multa_linha, _multa_pode_incidir
from judicial_calc.services.calculation_prescription import _aplicar_prescricao
from judicial_calc.services.calculation_summary import (
    _calcular_honorarios_informados,
    _montar_resumo,
    _total_multa_resumo,
)

Tabela = pd.DataFrame | list[dict[str, Any]] | None

@dataclass
class TabelasCalculo:
    """Conjunto de tabelas pré-carregadas para evitar chamadas repetidas.

    Todas as tabelas são opcionais porque o usuário pode fornecê-las
    manualmente para uso offline ou testes. Quando ausentes, o serviço baixa
    apenas o intervalo necessário das APIs oficiais.
    """

    indices: Tabela = None
    taxa_legal: Tabela = None
    selic: Tabela = None
    selic_diaria: Tabela = None
    ipca_deducao: Tabela = None
    taxa_legal_diaria_selic_ipcae: Tabela = None
    taxa_legal_diaria_12_6: Tabela = None
    indices_por_indice: dict[str, Tabela] | None = None


# ---------------------------------------------------------------------------
# Correção monetária
# ---------------------------------------------------------------------------
def competencia_final_correcao(indice: str, competencia_atualizacao: str) -> str:
    """Retorna a competência final usada pelo índice de correção.

    Exemplo: para índices SGS mensais, atualização em ``2026-03`` usa a
    competência ``2026-02``.
    """
    try:
        return resolve_index_strategy(indice, tabela_indices_informada=True).final_competence(competencia_atualizacao)
    except ValueError as exc:
        raise CalculationValidationError(
            "invalid_correction_index", ["indice"], "Índice de correção incompatível com o cálculo."
        ) from exc


def obter_fator_correcao(
    *,
    indice: str,
    data_parcela,
    competencia_atualizacao: str,
    tabela_indices: Tabela,
    deflacionar_valor_nominal: bool,
):
    """Obtém o fator de correção monetária de uma parcela.

    Entrada:
        ``data_parcela`` pode ser ``date`` ou texto aceito por ``parse_data``.
        ``tabela_indices`` pode ser omitida para índices oficiais SGS.

    Resultado:
        Decimal multiplicativo. Ex.: fator ``1.796392`` transforma
        ``10000`` em ``17963.92`` após arredondamento monetário.
    """
    try:
        strategy = resolve_index_strategy(indice, tabela_indices_informada=tabela_indices is not None)
    except ValueError as exc:
        raise CalculationValidationError(
            "invalid_correction_index", ["indice"], "Índice de correção incompatível com o cálculo."
        ) from exc
    try:
        return strategy.factor(
            data_parcela=data_parcela,
            competencia_atualizacao=competencia_atualizacao,
            tabela_indices=tabela_indices,
            deflacionar_valor_nominal=deflacionar_valor_nominal,
        )
    except CalculationValidationError:
        raise
    except (ValueError, KeyError, ArithmeticError) as exc:
        raise CalculationValidationError(
            "invalid_correction_period",
            ["indice", "mes_atualizacao", "ano_atualizacao"],
            "Revise o índice e a competência da atualização monetária.",
        ) from exc




def _tabela_indices_para(indice: str, tabelas: TabelasCalculo) -> Tabela:
    """Retorna a tabela de índices pré-carregada para uma chave específica."""
    if tabelas.indices_por_indice and indice in tabelas.indices_por_indice:
        return tabelas.indices_por_indice[indice]
    return tabelas.indices


def _indice_correcao_linha(data_parcela: date, cfg: CalculoParams) -> tuple[str, Decimal | None, FaixaDuploIndice | None]:
    """Resolve o índice e eventual valor base específico de uma linha."""
    faixa = cfg.faixa_duplo_indice_para_data(data_parcela)
    if faixa is None:
        return cfg.indice, None, None
    return faixa.indice, faixa.valor_parcela, faixa


# ---------------------------------------------------------------------------
# Pré-carga de tabelas oficiais
# ---------------------------------------------------------------------------
def _data_inicio_com_prescricao(data_inicio: date, cfg: CalculoParams) -> date:
    """Aplica a data de corte prescricional ao termo inicial de juros."""
    if cfg.data_inicio_prescricao is None:
        return data_inicio
    return max(data_inicio, cfg.data_inicio_prescricao)


def _data_inicio_juros_efetiva(params: dict[str, Any], cfg: CalculoParams, prefixo: str, data_parcela: date) -> date:
    """Calcula a data inicial efetivamente usada nos juros de uma linha."""
    data_manual = params.get(f"{prefixo}_data_inicio")
    inicio = parse_data(data_manual) if data_manual else data_parcela
    return _data_inicio_com_prescricao(inicio, cfg)


def _datas_inicio_juros(df: pd.DataFrame, cfg: CalculoParams, tipos: set[str]) -> list:
    """Obtém as datas iniciais dos juros que usam determinado conjunto de tipos."""
    datas = []
    menor_data_parcela = min(df["_data_parcela"])
    if cfg.tipo_juros_compensatorios in tipos:
        inicio = parse_data(cfg.data_inicio_compensatorios) if cfg.data_inicio_compensatorios else menor_data_parcela
        datas.append(_data_inicio_com_prescricao(inicio, cfg))
    if cfg.tipo_juros_moratorios in tipos:
        inicio = parse_data(cfg.data_inicio_moratorios) if cfg.data_inicio_moratorios else menor_data_parcela
        datas.append(_data_inicio_com_prescricao(inicio, cfg))
    return datas


def _precarregar_indices(df: pd.DataFrame, cfg: CalculoParams, tabelas: TabelasCalculo) -> None:
    """Pré-carrega somente os índices que ainda dependem de SGS.

    Em cálculos com duplo índice, mantém um cache por chave de índice para que
    cada parcela use a série correta sem misturar IGP-M, IPCA, INPC etc. As
    chaves presentes em taxas_mensais.xlsx continuam sendo carregadas sob
    demanda pelo próprio ``LocalExcelCorrectionIndex``.
    """
    indices_por_indice: dict[str, Tabela] = {}
    if isinstance(tabelas.indices_por_indice, dict):
        indices_por_indice.update(tabelas.indices_por_indice)

    for indice in sorted(cfg.indices_correcao_usados):
        if indice in indices_por_indice:
            continue
        if not cfg.tem_duplo_indice and tabelas.indices is not None:
            indices_por_indice[indice] = tabelas.indices
            continue
        try:
            strategy = resolve_index_strategy(indice, tabela_indices_informada=False)
        except ValueError as exc:
            raise CalculationValidationError(
                "invalid_correction_index", ["indice"], "Índice de correção incompatível com o cálculo."
            ) from exc
        if not isinstance(strategy, SGSPercentageCorrectionIndex):
            continue
        datas_indice = []
        for data_parcela in df["_data_parcela"]:
            indice_linha, _, _ = _indice_correcao_linha(data_parcela, cfg)
            if indice_linha == indice:
                datas_indice.append(data_parcela)
        if not datas_indice:
            continue
        inicio = min(competencia_data(d) for d in datas_indice)
        fim = competencia_final_correcao(indice, cfg.competencia_atualizacao)
        if fim >= inicio:
            meta = INDICES_SGS[indice]
            indices_por_indice[indice] = baixar_sgs(meta["codigo"], meta["nome"], inicio, fim)

    if cfg.tem_duplo_indice:
        tabelas.indices_por_indice = indices_por_indice
    elif indices_por_indice and tabelas.indices is None:
        tabelas.indices = next(iter(indices_por_indice.values()))

def _precarregar_taxa_legal(df: pd.DataFrame, cfg: CalculoParams, tabelas: TabelasCalculo) -> None:
    """Carrega a Taxa Legal mensal a partir da planilha critério de referência anexada."""
    if tabelas.taxa_legal is not None or not cfg.usa_taxa_legal:
        return
    datas = _datas_inicio_juros(df, cfg, TIPOS_TAXA_LEGAL_OFICIAL | TIPOS_JUROS_MORATORIOS_CTN_LEI_14905 | TIPOS_JUROS_MORATORIOS_STJ1368)
    if not datas:
        return
    # Preferimos o arquivo anexado. A função converte a coluna mensal decimal
    # para percentual, que é o formato esperado pelas funções de cálculo de juros.
    tabelas.taxa_legal = load_taxa_legal_mensal_percentual()


def _precarregar_selic(df: pd.DataFrame, cfg: CalculoParams, tabelas: TabelasCalculo) -> None:
    """Baixa Selic mensal ou diária para o modo STJ 1368.

    Para IGP-M, o critério de referência usa a Selic mensal SGS 4390. Para os índices com
    dedução de correção, usa a Selic diária SGS 11.
    """
    if not cfg.usa_stj1368:
        return
    datas = _datas_inicio_juros(df, cfg, TIPOS_JUROS_MORATORIOS_STJ1368)
    if not datas:
        return

    fim_usuario = resolver_competencia_final_taxa_legal(cfg.competencia_atualizacao, cfg.competencia_final_taxa_legal)
    if cfg.stj1368_deduz_correcao:
        if tabelas.selic_diaria is None:
            data_inicio = min(datas)
            data_fim = min(DATA_FIM_STJ1368_SELIC_COM_DEDUCAO, ultimo_dia_mes(fim_usuario))
            if data_fim >= data_inicio:
                tabelas.selic_diaria = baixar_tabela_selic_diaria(data_inicio, data_fim)
    else:
        if tabelas.selic is None:
            inicio = min(somar_meses(competencia_data(d), 1) for d in datas)
            fim = min(competencia_data(DATA_FIM_STJ1368_SELIC_SEM_DEDUCAO), fim_usuario)
            if fim >= inicio:
                tabelas.selic = baixar_tabela_selic_mensal(inicio, fim)


def _precarregar_ipca_deducao(df: pd.DataFrame, cfg: CalculoParams, tabelas: TabelasCalculo) -> None:
    """Baixa a série de correção deduzida no modo STJ 1368.

    A tabela do índice principal nunca é reutilizada aqui. A dedução do modo
    STJ 1368 deve vir da série definida em ``INDICE_SGS_DEDUCAO_TAXA_LEGAL``
    ou de ``tabela_ipca_deducao`` fornecida explicitamente pelo usuário.
    """
    if tabelas.ipca_deducao is not None or not cfg.usa_stj1368 or not cfg.stj1368_deduz_correcao:
        return
    datas = _datas_inicio_juros(df, cfg, TIPOS_JUROS_MORATORIOS_STJ1368)
    if not datas:
        return
    inicio = min(competencia_data(d) for d in datas)
    fim_usuario = resolver_competencia_final_taxa_legal(cfg.competencia_atualizacao, cfg.competencia_final_taxa_legal)
    fim = min(fim_usuario, "2024-07")
    codigo_sgs = INDICE_SGS_DEDUCAO_TAXA_LEGAL.get(cfg.indice)
    if codigo_sgs is not None and fim >= inicio:
        tabelas.ipca_deducao = baixar_tabela_ipca_deducao(inicio, fim, codigo_sgs=codigo_sgs)


def _precarregar_tabelas(df: pd.DataFrame, cfg: CalculoParams, params: dict[str, Any]) -> TabelasCalculo:
    """Centraliza a pré-carga das fontes externas.

    Ordem da pré-carga:
        1. índice principal;
        2. Taxa Legal;
        3. Selic;
        4. dedução de inflação do STJ 1368.
    """
    tabelas = TabelasCalculo(
        indices=params.get("tabela_indices"),
        taxa_legal=params.get("tabela_taxa_legal"),
        selic=params.get("tabela_selic"),
        selic_diaria=params.get("tabela_selic_diaria"),
        ipca_deducao=params.get("tabela_ipca_deducao"),
        taxa_legal_diaria_selic_ipcae=params.get("tabela_taxa_legal_diaria_selic_ipcae"),
        taxa_legal_diaria_12_6=params.get("tabela_taxa_legal_diaria_12_6"),
        indices_por_indice=params.get("tabelas_indices_por_indice"),
    )
    _precarregar_indices(df, cfg, tabelas)
    _precarregar_taxa_legal(df, cfg, tabelas)
    _precarregar_selic(df, cfg, tabelas)
    _precarregar_ipca_deducao(df, cfg, tabelas)
    return tabelas


# ---------------------------------------------------------------------------
# Cálculo linha a linha
# ---------------------------------------------------------------------------
def _parametros_stj1368(cfg: CalculoParams) -> dict[str, Any]:
    """Monta os ajustes de transição do modo critério de referência/STJ 1368."""
    sem_deducao = not cfg.stj1368_deduz_correcao
    return {
        "deduzir_correcao_pre_lei": not sem_deducao,
        "aplicar_taxa_legal_pos_lei": True,
        "data_fim_selic_stj1368": DATA_FIM_STJ1368_SELIC_SEM_DEDUCAO if sem_deducao else DATA_FIM_STJ1368_SELIC_COM_DEDUCAO,
        "competencia_final_taxa_legal_stj1368": COMPETENCIA_FIM_TAXA_LEGAL_STJ1368_SEM_DEDUCAO if sem_deducao else None,
        "usar_selic_mensal_sem_deducao": sem_deducao,
    }


def _calcular_juros_da_linha(
    *,
    params: dict[str, Any],
    cfg: CalculoParams,
    tabelas: TabelasCalculo,
    valor_base: Decimal,
    valor_nominal: Decimal,
    data_parcela,
    prefixo: str,
    valor_referencia_percentual_stj1368: Decimal | None = None,
    valor_incidencia_stj1368: Decimal | None = None,
) -> tuple[Decimal, Decimal, Decimal]:
    """Calcula juros compensatórios ou moratórios de uma linha.

    ``prefixo`` deve ser ``juros_compensatorios`` ou ``juros_moratorios``.
    """
    data_inicio_efetiva = _data_inicio_juros_efetiva(params, cfg, prefixo, data_parcela)
    try:
        return calcular_juros(
            valor_base=valor_base,
            valor_nominal=valor_nominal,
            data_parcela=data_parcela,
            competencia_atualizacao=cfg.competencia_atualizacao,
            taxa=params.get(f"{prefixo}_taxa", "0"),
            periodicidade=params.get(f"{prefixo}_periodicidade", "mensal"),
            pro_rata=bool(params.get(f"{prefixo}_pro_rata", False)),
            tipo=params.get(f"{prefixo}_tipo", "capitalizacao_simples"),
            data_inicio=data_inicio_efetiva,
            tabela_taxa_legal=tabelas.taxa_legal,
            tabela_selic=tabelas.selic,
            tabela_selic_diaria=tabelas.selic_diaria,
            tabela_ipca_deducao=tabelas.ipca_deducao,
            tabela_taxa_legal_diaria_selic_ipcae=tabelas.taxa_legal_diaria_selic_ipcae,
            tabela_taxa_legal_diaria_12_6=tabelas.taxa_legal_diaria_12_6,
            competencia_final_taxa_legal=cfg.competencia_final_taxa_legal,
            valor_referencia_percentual_stj1368=valor_referencia_percentual_stj1368,
            valor_incidencia_stj1368=valor_incidencia_stj1368,
            **_parametros_stj1368(cfg),
        )
    except CalculationValidationError:
        raise
    except (ValueError, KeyError, ArithmeticError) as exc:
        raise CalculationValidationError(
            "invalid_interest_configuration",
            [f"{prefixo}_tipo", f"{prefixo}_taxa", f"{prefixo}_periodicidade", f"{prefixo}_data_inicio"],
            "Revise o tipo, a taxa, a periodicidade e a data inicial dos juros.",
        ) from exc









def _linha_memoria(row: dict[str, Any], cfg: CalculoParams, params: dict[str, Any], tabelas: TabelasCalculo) -> dict[str, Any]:
    """Calcula uma parcela e devolve uma linha da memória de cálculo."""
    data_parcela = row["_data_parcela"]
    indice_linha, valor_duplo_indice, faixa_duplo_indice = _indice_correcao_linha(data_parcela, cfg)
    valor_original = moeda(valor_duplo_indice if valor_duplo_indice is not None else row["valor_singelo"])
    verba_tipo = str(row.get("verba_tipo", "dano_material"))
    aplica_valor_dobrado = cfg.valor_dobrado_flag and verba_tipo == "dano_material"
    valor_singelo = moeda(valor_original * Decimal("2")) if aplica_valor_dobrado else valor_original

    fator = obter_fator_correcao(
        indice=indice_linha,
        data_parcela=data_parcela,
        competencia_atualizacao=cfg.competencia_atualizacao,
        tabela_indices=_tabela_indices_para(indice_linha, tabelas),
        deflacionar_valor_nominal=cfg.deflacionar,
    )
    valor_atualizado = moeda(valor_singelo * fator)

    data_inicio_comp_efetiva = _data_inicio_juros_efetiva(params, cfg, "juros_compensatorios", data_parcela)
    data_inicio_mora_efetiva = _data_inicio_juros_efetiva(params, cfg, "juros_moratorios", data_parcela)

    juros_comp, pct_comp, n_comp = _calcular_juros_da_linha(
        params=params,
        cfg=cfg,
        tabelas=tabelas,
        valor_base=valor_atualizado,
        valor_nominal=valor_singelo,
        data_parcela=data_parcela,
        prefixo="juros_compensatorios",
    )

    base_mora = valor_atualizado + juros_comp if cfg.juros_mora_sobre_compensatorios else valor_atualizado
    juros_mora, pct_mora, n_mora = _calcular_juros_da_linha(
        params=params,
        cfg=cfg,
        tabelas=tabelas,
        valor_base=base_mora,
        valor_nominal=valor_singelo,
        data_parcela=data_parcela,
        prefixo="juros_moratorios",
        valor_referencia_percentual_stj1368=valor_atualizado,
        valor_incidencia_stj1368=base_mora,
    )

    multa_detalhe = _calcular_multa_linha(
        data_parcela=data_parcela,
        valor_atualizado=valor_atualizado,
        juros_comp=juros_comp,
        juros_mora=juros_mora,
        cfg=cfg,
        params=params,
    )
    total = moeda(valor_atualizado + juros_comp + juros_mora + multa_detalhe.total)

    linha = {
        "item": _normalizar_inteiro_flexivel(row["item"], "parcelas.item"),
        "descricao": row.get("descricao", ""),
        "verba_tipo": verba_tipo,
        "data": data_parcela.isoformat(),
        "valor_singelo": valor_singelo,
        "competencia_inicio_correcao": competencia_data(data_parcela),
        "competencia_final_correcao": competencia_final_correcao(indice_linha, cfg.competencia_atualizacao),
        "indice_correcao": indice_linha,
        "duplo_indice_flag": cfg.duplo_indice_flag,
        "duplo_indice_faixa": faixa_duplo_indice.ordem if faixa_duplo_indice else None,
        "duplo_indice_data_inicio": faixa_duplo_indice.data_inicio.isoformat() if faixa_duplo_indice else None,
        "duplo_indice_data_fim": faixa_duplo_indice.data_fim.isoformat() if faixa_duplo_indice else None,
        "duplo_indice_valor_parcela": faixa_duplo_indice.valor_parcela if faixa_duplo_indice else None,
        "prescricao_flag": cfg.prescricao_flag,
        "data_inicio_prescricao": cfg.data_inicio_prescricao.isoformat() if cfg.data_inicio_prescricao else None,
        "prescricao_data_referencia_tipo": cfg.prescricao_data_referencia_tipo,
        "prescricao_data_referencia": cfg.prescricao_data_referencia.isoformat() if cfg.prescricao_data_referencia else None,
        "data_inicio_juros_compensatorios_efetiva": data_inicio_comp_efetiva.isoformat(),
        "data_inicio_juros_moratorios_efetiva": data_inicio_mora_efetiva.isoformat(),
        "fator_correcao": fator,
        "valor_atualizado": valor_atualizado,
        "base_juros_moratorios": base_mora,
        "n_juros_compensatorios": n_comp,
        "percentual_juros_compensatorios": pct_comp * Decimal("100"),
        "juros_compensatorios": juros_comp,
        "n_juros_moratorios": n_mora,
        "percentual_juros_moratorios": pct_mora * Decimal("100"),
        "juros_moratorios": juros_mora,
        "base_multa_manual": multa_detalhe.base_manual,
        "multa_manual": multa_detalhe.manual,
        "multa": multa_detalhe.total,
        "total": total,
        "incide_multa_manual": _multa_pode_incidir(data_parcela, cfg),
        # Campos preenchidos após o cálculo dos honorários informados.
        # O art. 523 é aplicado depois desses honorários, conforme o critério de referência.
        "incide_art_523": _multa_pode_incidir(data_parcela, cfg),
        "honorarios_informados_linha": Decimal("0.00"),
        "base_art_523": Decimal("0.00"),
        "multa_art_523": Decimal("0.00"),
        "honorarios_art_523": Decimal("0.00"),
        "total_art_523": Decimal("0.00"),
        "total_com_honorarios_e_art_523": total,
        "compensacao_linha": Decimal("0.00"),
        "total_liquido_apos_compensacao": total,
    }
    if cfg.valor_dobrado_flag:
        # A repetição em dobro incide apenas sobre parcelas de dano material.
        # Dano moral, custas e honorários permanecem com o valor nominal próprio.
        linha["valor_original"] = valor_original
        linha["valor_dobrado_flag"] = aplica_valor_dobrado
    return linha










# ---------------------------------------------------------------------------
# API principal
# ---------------------------------------------------------------------------



def _bool_param(valor: Any, default: bool = False) -> bool:
    """Normaliza parâmetros booleanos vindos de UI/JSON/ambiente."""
    if valor is None:
        return default
    if isinstance(valor, bool):
        return valor
    texto = str(valor).strip().lower()
    if texto in {"1", "true", "sim", "s", "yes", "y", "on"}:
        return True
    if texto in {"0", "false", "nao", "não", "n", "no", "off", ""}:
        return False
    return default


def _executar_atualizacao_indices_se_necessario(params: dict[str, Any]) -> dict[str, Any]:
    """Executa a atualização diária das planilhas antes do cálculo.

    O fluxo padrão tenta atualizar uma vez por dia, mas não bloqueia o cálculo
    se o site estiver indisponível. Para bloquear o cálculo em caso de falha,
    informe ``falhar_se_atualizacao_indices_falhar=True``.
    """
    # Evita internet involuntária na suíte de testes local.
    if os.getenv("PYTEST_CURRENT_TEST"):
        return {
            "executed": False,
            "skipped": True,
            "success": True,
            "message": "Atualização de planilhas ignorada durante testes automatizados.",
        }

    auto_default = os.getenv("JUDICIAL_CALC_AUTO_UPDATE_RATES", "1")
    auto_update = _bool_param(params.get("auto_atualizar_planilhas_indices", auto_default), default=True)
    if not auto_update:
        return {
            "executed": False,
            "skipped": True,
            "success": True,
            "message": "Atualização automática das planilhas desativada neste cálculo.",
        }

    strict = _bool_param(params.get("falhar_se_atualizacao_indices_falhar"), default=False)
    force = _bool_param(params.get("forcar_atualizacao_planilhas_indices"), default=False)
    try:
        timeout = int(params.get("drcalc_timeout", os.getenv("JUDICIAL_CALC_DRCALC_TIMEOUT", "30")))
    except Exception:
        timeout = 30

    result = atualizar_planilhas_drcalc_se_necessario(force=force, timeout=timeout, strict=strict)
    payload = result.to_dict()
    if strict and not payload.get("success", False):
        raise CalculationValidationError(
            "index_update_failed", ["indice"], "Não foi possível validar as planilhas do índice selecionado."
        )
    return payload

def calcular_debitos(parcelas: pd.DataFrame | list[dict[str, Any]], **params: Any) -> ResultadoCalculo:
    """Calcula a atualização completa de um conjunto de parcelas.

    Entrada:
        ``parcelas``: DataFrame ou lista de dicionários com, no mínimo,
        ``item``, ``data`` e ``valor_singelo``. A data pode estar em
        ``YYYY-MM-DD`` ou ``DD/MM/YYYY``.

        ``params``: parâmetros de índice, juros, multa e honorários. O exemplo
        do README mostra o conjunto completo usado para replicar o critério de referência.

    Resultado:
        ``ResultadoCalculo`` com:
        * ``memoria``: DataFrame detalhado por parcela;
        * ``resumo``: DataFrame com totais;
        * ``parametros``: parâmetros originais acrescidos da competência
          normalizada ``AAAA-MM``.
    """
    atualizacao_indices = _executar_atualizacao_indices_se_necessario(params)

    df = pd.DataFrame(parcelas).copy()
    faltantes = {"item", "data", "valor_singelo"} - set(df.columns)
    if faltantes:
        raise CalculationValidationError(
            "missing_installment_columns", [], "As parcelas não possuem todos os campos obrigatórios."
        )
    if "descricao" not in df.columns:
        df["descricao"] = ""
    df["_data_parcela"] = df["data"].apply(parse_data)

    cfg = CalculoParams.from_raw(params)
    df = _aplicar_prescricao(df, cfg)
    tabelas = _precarregar_tabelas(df, cfg, params)

    memoria = pd.DataFrame([_linha_memoria(row, cfg, params, tabelas) for row in df.to_dict("records")])
    memoria = memoria.sort_values("item").reset_index(drop=True)

    # O art. 523 precisa ser calculado depois dos honorários informados,
    # porque o critério de referência aplica a multa/honorários legais sobre o subtotal já
    # acrescido desses honorários. Por isso, primeiro obtemos os honorários
    # comuns e só então enriquecemos a memória com os campos do art. 523.
    total_atualizado = moeda(memoria["valor_atualizado"].sum())
    total_comp = moeda(memoria["juros_compensatorios"].sum())
    total_mora = moeda(memoria["juros_moratorios"].sum())
    total_multa = _total_multa_resumo(memoria, params)
    _, honorarios_informados = _calcular_honorarios_informados(
        total_atualizado=total_atualizado,
        total_comp=total_comp,
        total_mora=total_mora,
        total_multa=total_multa,
        params=params,
    )
    memoria = _aplicar_art_523_na_memoria(
        memoria=memoria,
        cfg=cfg,
        honorarios_informados=honorarios_informados,
    )

    resumo = _montar_resumo(memoria, params, cfg)
    valor_compensacao_resumo = D(resumo.loc[resumo["campo"] == "valor_compensacao", "valor"].iloc[0])
    memoria = _aplicar_compensacao_na_memoria(memoria, valor_compensacao_resumo)
    parametros_resultado = {
        **params,
        "competencia_atualizacao": cfg.competencia_atualizacao,
        "prescricao_flag": cfg.prescricao_flag,
        "prescricao_anos": cfg.prescricao_anos,
        "prescricao_data_referencia_tipo": cfg.prescricao_data_referencia_tipo,
        "prescricao_data_referencia": cfg.prescricao_data_referencia.isoformat() if cfg.prescricao_data_referencia else None,
        "prescricao_data_inicio_calculo": cfg.data_inicio_prescricao.isoformat() if cfg.data_inicio_prescricao else None,
        "compensacao_flag": cfg.compensacao_flag,
        "compensacao_tipo_calculo": cfg.compensacao_tipo_calculo,
        "compensacao_valor": cfg.compensacao_valor,
        "duplo_indice_flag": cfg.duplo_indice_flag,
        "duplo_indice_primeiro_indice": cfg.duplo_indice_primeiro.indice if cfg.duplo_indice_primeiro else None,
        "duplo_indice_primeiro_data_inicio": cfg.duplo_indice_primeiro.data_inicio.isoformat() if cfg.duplo_indice_primeiro else None,
        "duplo_indice_primeiro_data_fim": cfg.duplo_indice_primeiro.data_fim.isoformat() if cfg.duplo_indice_primeiro else None,
        "duplo_indice_primeiro_valor_parcela": cfg.duplo_indice_primeiro.valor_parcela if cfg.duplo_indice_primeiro else None,
        "duplo_indice_segundo_indice": cfg.duplo_indice_segundo.indice if cfg.duplo_indice_segundo else None,
        "duplo_indice_segundo_data_inicio": cfg.duplo_indice_segundo.data_inicio.isoformat() if cfg.duplo_indice_segundo else None,
        "duplo_indice_segundo_data_fim": cfg.duplo_indice_segundo.data_fim.isoformat() if cfg.duplo_indice_segundo else None,
        "duplo_indice_segundo_valor_parcela": cfg.duplo_indice_segundo.valor_parcela if cfg.duplo_indice_segundo else None,
        "valor_dobrado_flag": cfg.valor_dobrado_flag,
        "evidence_map": params.get("evidence_map", {}),
        "extraction_audit": params.get("extraction_audit", []),
        "document_roles": params.get("document_roles", []),
        "document_conflicts": params.get("document_conflicts", []),
        "ignored_jurisprudence_audit": params.get("ignored_jurisprudence_audit", []),
        "validation_issues": params.get("validation_issues", []),
        "verbas": params.get("verbas", []),
        "human_review_checklist": params.get("human_review_checklist", []),
        "atualizacao_planilhas_indices": atualizacao_indices,
    }
    return ResultadoCalculo(memoria=memoria, resumo=resumo, parametros=parametros_resultado)
