"""Compensação e abatimentos de eventos financeiros aplicados ao resultado.

O módulo recebe valores já calculados pelo motor e apenas distribui os ajustes
monetários de forma auditável, preservando a soma exata em centavos.
"""
from __future__ import annotations

from decimal import Decimal

import pandas as pd

from judicial_calc.core.numbers import D, moeda
from judicial_calc.services.calculation_parameters import CalculoParams
from judicial_calc.services.calculation_penalties import _rateio_monetario

def _calcular_valor_compensacao(cfg: CalculoParams, total_geral_bruto: Decimal) -> Decimal:
    """Calcula o valor a descontar por compensação sobre o total final bruto."""
    if not cfg.tem_compensacao:
        return Decimal("0.00")
    if cfg.compensacao_tipo_calculo == "fixo":
        return moeda(cfg.compensacao_valor)
    return moeda(total_geral_bruto * cfg.compensacao_valor / Decimal("100"))


def _aplicar_compensacao_na_memoria(memoria: pd.DataFrame, valor_compensacao: Decimal) -> pd.DataFrame:
    """Rateia a compensação final entre parcelas para manter memória auditável."""
    memoria = memoria.copy()
    pesos = [D(v) for v in memoria["total_com_honorarios_e_art_523"]]
    memoria["compensacao_linha"] = _rateio_monetario(valor_compensacao, pesos)
    memoria["total_liquido_apos_compensacao"] = [
        moeda(D(total) - D(desconto))
        for total, desconto in zip(memoria["total_com_honorarios_e_art_523"], memoria["compensacao_linha"])
    ]
    return memoria


def _total_eventos_financeiros(eventos_df: pd.DataFrame) -> Decimal:
    """Soma eventos financeiros que impactam o total."""
    if eventos_df.empty or "afeta_total" not in eventos_df.columns:
        return Decimal("0.00")
    total = Decimal("0.00")
    for _, row in eventos_df.loc[eventos_df["afeta_total"].astype(bool)].iterrows():
        total += D(row.get("valor_atualizado_para_abatimento", "0"))
    return moeda(total)


def _aplicar_eventos_financeiros_na_memoria(memoria: pd.DataFrame, total_eventos: Decimal) -> pd.DataFrame:
    """Rateia abatimentos cronológicos finais na memória."""
    memoria = memoria.copy()
    base_col = "total_liquido_apos_compensacao" if "total_liquido_apos_compensacao" in memoria.columns else "total_com_honorarios_e_art_523"
    pesos = [D(v) for v in memoria[base_col]]
    memoria["eventos_financeiros_linha"] = _rateio_monetario(total_eventos, pesos)
    memoria["total_liquido_apos_eventos_financeiros"] = [
        moeda(D(total) - D(desconto))
        for total, desconto in zip(memoria[base_col], memoria["eventos_financeiros_linha"])
    ]
    return memoria


def _ajustar_resumo_por_eventos(resumo: pd.DataFrame, eventos_df: pd.DataFrame) -> pd.DataFrame:
    """Inclui abatimentos por eventos financeiros no resumo final."""
    total_eventos = _total_eventos_financeiros(eventos_df)
    if total_eventos == 0:
        if "eventos_financeiros_total_atualizado" not in set(resumo["campo"]):
            resumo = pd.concat([resumo, pd.DataFrame([{
                "campo": "eventos_financeiros_total_atualizado",
                "valor": Decimal("0.00"),
            }])], ignore_index=True)
        return resumo
    resumo = resumo.copy()
    total_atual = D(resumo.loc[resumo["campo"] == "total_geral", "valor"].iloc[0])
    total_final = moeda(total_atual - total_eventos)
    resumo.loc[resumo["campo"] == "total_geral", "valor"] = total_final
    linhas = pd.DataFrame([
        {"campo": "eventos_financeiros_total_atualizado", "valor": total_eventos},
        {"campo": "total_apos_eventos_financeiros", "valor": total_final},
    ])
    resumo = pd.concat([resumo, linhas], ignore_index=True)
    return resumo
