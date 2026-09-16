"""Filtro de parcelas alcançadas pela configuração de prescrição.

Este módulo não define prazo jurídico. Ele apenas executa o corte temporal já
validado em ``CalculoParams`` e informa erro estruturado quando nenhuma parcela
permanece para cálculo.
"""
from __future__ import annotations

import pandas as pd

from judicial_calc.core.errors import CalculationValidationError
from judicial_calc.services.calculation_parameters import CalculoParams

def _aplicar_prescricao(df: pd.DataFrame, cfg: CalculoParams) -> pd.DataFrame:
    """Filtra as parcelas prescritas e mantém apenas valores a partir do corte.

    Quando ``prescricao_flag`` é 1, a data inicial do cálculo é obtida por:

        ``prescricao_data_referencia - prescricao_anos``

    As parcelas com data anterior a esse corte não entram na memória nem no
    resumo. Além disso, os juros de parcelas remanescentes nunca começam antes
    dessa mesma data de corte.
    """
    if not cfg.tem_prescricao:
        return df

    assert cfg.data_inicio_prescricao is not None
    filtrado = df.loc[df["_data_parcela"] >= cfg.data_inicio_prescricao].copy()
    if filtrado.empty:
        raise CalculationValidationError(
            "prescription_removed_all_installments",
            ["prescricao_anos", "prescricao_data_referencia_tipo", "prescricao_data_referencia"],
            "Nenhuma parcela permaneceu após a aplicação da prescrição.",
        )
    return filtrado
