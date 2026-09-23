"""Compensação aplicada ao resultado final do cálculo.

Este módulo recebe valores já calculados pelo motor e distribui somente a
compensação parametrizada, preservando a soma exata em centavos e a memória
auditable por parcela.
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
