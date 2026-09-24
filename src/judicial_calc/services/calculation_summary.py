"""Composição do resumo final e dos honorários do cálculo.

O resumo não recalcula correção ou juros: agrega somente os valores produzidos
pelas etapas anteriores na mesma ordem financeira usada pelo motor.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import pandas as pd

from judicial_calc.core.numbers import D, moeda
from judicial_calc.services.calculation_adjustments import _calcular_valor_compensacao
from judicial_calc.services.calculation_parameters import ART_523_NAO_APLICAR, CalculoParams
from judicial_calc.services.calculation_penalties import _total_art_523

@dataclass(frozen=True)
class HonorariosResumo:
    """Detalhamento dos honorários e acréscimos finais.

    ``manual`` representa os honorários informados pelo usuário na tela.
    ``multa_art_523`` e ``honorarios_art_523`` representam os acréscimos
    legais selecionados no bloco "Art. 523 §1º - CPC".
    """

    base_manual: Decimal
    manual: Decimal
    base_art_523: Decimal
    multa_art_523: Decimal
    honorarios_art_523: Decimal

    @property
    def total_honorarios(self) -> Decimal:
        """Honorários totais: informados + legais do art. 523."""
        return moeda(self.manual + self.honorarios_art_523)

    @property
    def total_art_523(self) -> Decimal:
        """Acréscimo total do art. 523: multa + honorários legais."""
        return moeda(self.multa_art_523 + self.honorarios_art_523)


def _calcular_honorarios_informados(
    *,
    total_atualizado: Decimal,
    total_comp: Decimal,
    total_mora: Decimal,
    total_multa: Decimal,
    params: dict[str, Any],
) -> tuple[Decimal, Decimal]:
    """Calcula apenas os honorários informados pelo usuário.

    Entradas:
        totais monetários já arredondados da memória de cálculo.

    Regras:
        * ``honorarios_tipo='percentual'``: aplica o percentual sobre a base;
        * ``honorarios_tipo='fixo'``: usa o valor informado diretamente;
        * ``incidir_honorarios_sobre_multa=True``: inclui a multa comum
          informada pelo usuário na base.

    Resultado:
        tupla ``(base_honorarios, honorarios_informados)``.
    """
    base_manual = total_atualizado + total_comp + total_mora
    if params.get("incidir_honorarios_sobre_multa", False):
        base_manual += total_multa
    base_manual = moeda(base_manual)

    honorarios = D(params.get("honorarios", "0"))
    if params.get("honorarios_tipo", "percentual") == "fixo":
        return base_manual, moeda(honorarios)
    return base_manual, moeda(base_manual * honorarios / Decimal("100"))


def _calcular_honorarios_resumo(
    *,
    total_atualizado: Decimal,
    total_comp: Decimal,
    total_mora: Decimal,
    total_multa: Decimal,
    memoria: pd.DataFrame,
    params: dict[str, Any],
) -> HonorariosResumo:
    """Consolida honorários informados e acréscimos do art. 523.

    A memória já deve conter os campos ``base_art_523``, ``multa_art_523`` e
    ``honorarios_art_523``. Eles são criados por
    ``_aplicar_art_523_na_memoria`` após o cálculo dos honorários informados.
    """
    base_manual, honorarios_manual = _calcular_honorarios_informados(
        total_atualizado=total_atualizado,
        total_comp=total_comp,
        total_mora=total_mora,
        total_multa=total_multa,
        params=params,
    )

    return HonorariosResumo(
        base_manual=base_manual,
        manual=honorarios_manual,
        base_art_523=moeda(memoria["base_art_523"].sum()),
        multa_art_523=moeda(memoria["multa_art_523"].sum()),
        honorarios_art_523=moeda(memoria["honorarios_art_523"].sum()),
    )


def _total_multa_resumo(memoria: pd.DataFrame, params: dict[str, Any]) -> Decimal:
    """Calcula o total de multa como o critério de referência exibe na linha de totais.

    O critério de referência mostra a multa linha a linha arredondada, mas a linha ``TOTAIS``
    é calculada sobre a soma das bases das parcelas. Em conjuntos com várias
    parcelas isso pode diferir em 1 centavo da soma das multas já arredondadas.
    """
    raw = params.get("multa_valor")
    if raw in (None, ""):
        raw = params.get("multa_percentual", "0")
    valor = D(raw or "0")
    if valor == 0:
        return Decimal("0.00")

    if str(params.get("multa_tipo") or "percentual").strip().lower() == "fixo":
        # A memória já contém o rateio exato do valor único entre as parcelas
        # elegíveis, portanto a soma é a fonte auditável do total fixo aplicado.
        return moeda(memoria["multa"].sum())

    if "incide_multa_manual" in memoria.columns:
        mask = memoria["incide_multa_manual"].astype(bool)
        base_total = sum((D(v) for v in memoria.loc[mask, "base_multa_manual"]), Decimal("0"))
        return moeda(base_total * valor / Decimal("100"))

    return moeda(memoria["multa"].sum())


def _montar_resumo(memoria: pd.DataFrame, params: dict[str, Any], cfg: CalculoParams) -> pd.DataFrame:
    """Agrega os totais finais no mesmo encadeamento visual do critério de referência.

    Sequência de cálculo do resumo:
        1. soma as parcelas atualizadas, juros e multa comum;
        2. calcula o subtotal das parcelas;
        3. soma os honorários informados pelo usuário;
        4. aplica, se selecionado, multa/honorários do art. 523 sobre esse
           subtotal já acrescido dos honorários informados;
        5. calcula o total geral bruto;
        6. desconta a compensação, se aplicável, chegando ao total geral líquido.
    """
    total_atualizado = moeda(memoria["valor_atualizado"].sum())
    total_comp = moeda(memoria["juros_compensatorios"].sum())
    total_mora = moeda(memoria["juros_moratorios"].sum())
    total_multa = _total_multa_resumo(memoria, params)
    subtotal = moeda(total_atualizado + total_comp + total_mora + total_multa)

    base_honorarios, honorarios_informados = _calcular_honorarios_informados(
        total_atualizado=total_atualizado,
        total_comp=total_comp,
        total_mora=total_mora,
        total_multa=total_multa,
        params=params,
    )
    subtotal_com_honorarios = moeda(subtotal + honorarios_informados)
    base_art_523 = subtotal_com_honorarios if cfg.art_523 != ART_523_NAO_APLICAR else Decimal("0.00")
    multa_art_523, honorarios_art_523 = _total_art_523(cfg, base_art_523)
    total_art_523 = moeda(multa_art_523 + honorarios_art_523)
    valor_honorarios = moeda(honorarios_informados + honorarios_art_523)
    total_geral_bruto = moeda(subtotal_com_honorarios + total_art_523)
    valor_compensacao = _calcular_valor_compensacao(cfg, total_geral_bruto)
    total_geral = moeda(total_geral_bruto - valor_compensacao)

    return pd.DataFrame([
        {"campo": "competencia_atualizacao", "valor": cfg.competencia_atualizacao},
        {"campo": "indice", "valor": cfg.indice},
        {"campo": "duplo_indice_flag", "valor": cfg.duplo_indice_flag},
        {"campo": "duplo_indice_primeiro_indice", "valor": cfg.duplo_indice_primeiro.indice if cfg.duplo_indice_primeiro else None},
        {"campo": "duplo_indice_primeiro_data_inicio", "valor": cfg.duplo_indice_primeiro.data_inicio.isoformat() if cfg.duplo_indice_primeiro else None},
        {"campo": "duplo_indice_primeiro_data_fim", "valor": cfg.duplo_indice_primeiro.data_fim.isoformat() if cfg.duplo_indice_primeiro else None},
        {"campo": "duplo_indice_primeiro_valor_parcela", "valor": cfg.duplo_indice_primeiro.valor_parcela if cfg.duplo_indice_primeiro else None},
        {"campo": "duplo_indice_segundo_indice", "valor": cfg.duplo_indice_segundo.indice if cfg.duplo_indice_segundo else None},
        {"campo": "duplo_indice_segundo_data_inicio", "valor": cfg.duplo_indice_segundo.data_inicio.isoformat() if cfg.duplo_indice_segundo else None},
        {"campo": "duplo_indice_segundo_data_fim", "valor": cfg.duplo_indice_segundo.data_fim.isoformat() if cfg.duplo_indice_segundo else None},
        {"campo": "duplo_indice_segundo_valor_parcela", "valor": cfg.duplo_indice_segundo.valor_parcela if cfg.duplo_indice_segundo else None},
        {"campo": "prescricao_flag", "valor": cfg.prescricao_flag},
        {"campo": "prescricao_anos", "valor": cfg.prescricao_anos},
        {"campo": "prescricao_data_referencia_tipo", "valor": cfg.prescricao_data_referencia_tipo},
        {"campo": "prescricao_data_referencia", "valor": cfg.prescricao_data_referencia.isoformat() if cfg.prescricao_data_referencia else None},
        {"campo": "prescricao_data_inicio_calculo", "valor": cfg.data_inicio_prescricao.isoformat() if cfg.data_inicio_prescricao else None},
        {"campo": "total_singelo", "valor": moeda(memoria["valor_singelo"].sum())},
        {"campo": "total_atualizado", "valor": total_atualizado},
        {"campo": "total_juros_compensatorios", "valor": total_comp},
        {"campo": "total_juros_moratorios", "valor": total_mora},
        {"campo": "total_multa", "valor": total_multa},
        {"campo": "subtotal", "valor": subtotal},
        {"campo": "base_honorarios", "valor": base_honorarios},
        {"campo": "honorarios_informados", "valor": honorarios_informados},
        {"campo": "subtotal_com_honorarios", "valor": subtotal_com_honorarios},
        {"campo": "base_art_523", "valor": base_art_523},
        {"campo": "multa_art_523", "valor": multa_art_523},
        {"campo": "honorarios_art_523", "valor": honorarios_art_523},
        {"campo": "total_art_523", "valor": total_art_523},
        {"campo": "honorarios", "valor": valor_honorarios},
        {"campo": "total_geral_bruto", "valor": total_geral_bruto},
        {"campo": "compensacao_flag", "valor": cfg.compensacao_flag},
        {"campo": "compensacao_tipo_calculo", "valor": cfg.compensacao_tipo_calculo},
        {"campo": "compensacao_valor_parametro", "valor": cfg.compensacao_valor},
        {"campo": "valor_compensacao", "valor": valor_compensacao},
        {"campo": "total_geral", "valor": total_geral},
    ])
