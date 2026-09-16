"""Multas, rateios monetários e art. 523 do CPC usados pelo motor.

As funções deste módulo foram separadas da orquestração principal para tornar a
regra de encargos localizável e testável sem alterar nenhuma fórmula financeira.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import pandas as pd

from judicial_calc.core.dates import ultimo_dia_mes
from judicial_calc.core.numbers import D, moeda
from judicial_calc.services.calculation_parameters import (
    ART_523_APLICAR_MULTA_HONORARIOS,
    ART_523_NAO_APLICAR,
    PERCENTUAL_ART_523,
    CalculoParams,
    _moeda_art_523,
)

@dataclass(frozen=True)
class MultaLinha:
    """Detalhamento da multa percentual informada pelo usuário.

    Importante:
        a multa do art. 523, §1º, do CPC NÃO é calculada aqui. No critério de referência,
        essa multa aparece depois do subtotal e depois dos honorários
        informados pelo usuário. Por isso, ela é calculada em uma etapa
        posterior, quando o resumo já conhece o valor dos honorários.

    Atributos:
        ``base_manual``: base da multa digitada no campo "percentual da
        multa (%)". Por padrão é o valor atualizado, podendo incluir juros
        conforme os checkboxes da tela.

        ``manual``: valor da multa percentual informada pelo usuário.

        ``total``: mantido para compatibilidade; neste ponto é igual a
        ``manual``.
    """

    base_manual: Decimal
    manual: Decimal
    total: Decimal


def _parcela_a_vencer(data_parcela, competencia_atualizacao: str) -> bool:
    """Indica se a parcela vence depois da competência de atualização.

    Entrada:
        ``data_parcela``: data original da parcela.
        ``competencia_atualizacao``: competência ``AAAA-MM``.

    Resultado:
        ``True`` quando a data da parcela é posterior ao último dia do mês de
        atualização. Esse critério controla a opção de tela "Incidir multa
        sobre parcelas a vencer".
    """
    return data_parcela > ultimo_dia_mes(competencia_atualizacao)


def _multa_pode_incidir(data_parcela, cfg: CalculoParams) -> bool:
    """Aplica a opção 'incidir multa sobre parcelas a vencer'."""
    return cfg.incidir_multa_sobre_parcelas_a_vencer or not _parcela_a_vencer(data_parcela, cfg.competencia_atualizacao)


def _base_multa_manual(
    *,
    valor_atualizado: Decimal,
    juros_comp: Decimal,
    juros_mora: Decimal,
    params: dict[str, Any],
) -> Decimal:
    """Calcula a base da multa percentual informada pelo usuário.

    Por padrão, a base é apenas o valor atualizado. As opções da tela permitem
    incluir juros compensatórios e/ou juros moratórios na mesma base.
    """
    base = valor_atualizado
    if params.get("incidir_multa_sobre_juros_compensatorios", False):
        base += juros_comp
    if params.get("incidir_multa_sobre_juros_moratorios", False):
        base += juros_mora
    return moeda(base)


def _calcular_multa_linha(
    *,
    data_parcela,
    valor_atualizado: Decimal,
    juros_comp: Decimal,
    juros_mora: Decimal,
    cfg: CalculoParams,
    params: dict[str, Any],
) -> MultaLinha:
    """Calcula somente a multa percentual comum de uma parcela.

    Entradas principais:
        ``valor_atualizado``, ``juros_comp`` e ``juros_mora`` já devem estar
        arredondados em moeda.

    Resultado:
        ``MultaLinha`` com a base e o valor da multa digitada no campo
        ``multa_percentual``. Quando a parcela está a vencer e a opção
        correspondente está desligada, o valor da multa fica zerado.

    Observação:
        a multa legal de 10% do art. 523 é calculada depois dos honorários
        informados, porque é assim que o critério de referência monta o resumo:

        débito atualizado -> honorários informados -> subtotal -> art. 523.
    """
    base_manual = _base_multa_manual(
        valor_atualizado=valor_atualizado,
        juros_comp=juros_comp,
        juros_mora=juros_mora,
        params=params,
    )

    if not _multa_pode_incidir(data_parcela, cfg):
        return MultaLinha(base_manual=base_manual, manual=Decimal("0.00"), total=Decimal("0.00"))

    multa_manual = moeda(base_manual * D(params.get("multa_percentual", "0")) / Decimal("100"))
    return MultaLinha(base_manual=base_manual, manual=multa_manual, total=multa_manual)


def _rateio_monetario(total: Decimal, pesos: list[Decimal]) -> list[Decimal]:
    """Distribui um valor monetário entre linhas preservando a soma exata.

    O critério de referência apresenta totais arredondados em centavos. Quando há mais de uma
    parcela, calcular 10% linha a linha pode gerar diferença de centavos em
    relação a calcular 10% sobre o subtotal. Esta função rateia o total usando
    os pesos informados e ajusta o último item não zerado pela diferença de
    arredondamento, garantindo que ``sum(resultado) == total``.
    """
    total = moeda(total)
    if not pesos:
        return []
    soma_pesos = sum((D(p) for p in pesos), Decimal("0"))
    if soma_pesos == 0 or total == 0:
        return [Decimal("0.00") for _ in pesos]

    valores = [moeda(total * D(p) / soma_pesos) for p in pesos]
    diferenca = moeda(total - sum(valores, Decimal("0.00")))
    if diferenca:
        for i in range(len(valores) - 1, -1, -1):
            if pesos[i] != 0:
                valores[i] = moeda(valores[i] + diferenca)
                break
    return valores


def _total_art_523(cfg: CalculoParams, base_art_523: Decimal) -> tuple[Decimal, Decimal]:
    """Calcula multa e honorários legais do art. 523 sobre a base final.

    Entrada:
        ``cfg.art_523`` controla a opção marcada na tela:

        * ``nao_aplicar``: não acrescenta nada;
        * ``aplicar_multa``: acrescenta multa legal de 10%;
        * ``aplicar_multa_honorarios``: acrescenta multa legal de 10% e
          honorários legais de 10%.

    Resultado:
        tupla ``(multa_art_523, honorarios_art_523)``.
    """
    if cfg.art_523 == ART_523_NAO_APLICAR:
        return Decimal("0.00"), Decimal("0.00")

    multa = _moeda_art_523(base_art_523 * PERCENTUAL_ART_523 / Decimal("100"))
    honorarios = Decimal("0.00")
    if cfg.art_523 == ART_523_APLICAR_MULTA_HONORARIOS:
        honorarios = _moeda_art_523(base_art_523 * PERCENTUAL_ART_523 / Decimal("100"))
    return multa, honorarios


def _aplicar_art_523_na_memoria(
    *,
    memoria: pd.DataFrame,
    cfg: CalculoParams,
    honorarios_informados: Decimal,
) -> pd.DataFrame:
    """Inclui na memória de cálculo os campos do art. 523.

    O critério de referência aplica o art. 523 depois dos honorários informados pelo usuário.
    Portanto, a base do art. 523 é:

        subtotal das parcelas + honorários informados

    Para a memória linha a linha, os honorários informados são rateados entre
    as parcelas proporcionalmente ao total da própria parcela. Depois, a multa
    e os honorários legais do art. 523 também são rateados para que a soma das
    linhas bata exatamente com o resumo.
    """
    memoria = memoria.copy()
    pesos_honorarios = [D(v) for v in memoria["total"]]
    memoria["honorarios_informados_linha"] = _rateio_monetario(honorarios_informados, pesos_honorarios)

    bases = []
    for _, row in memoria.iterrows():
        if bool(row.get("incide_art_523", True)):
            bases.append(moeda(D(row["total"]) + D(row["honorarios_informados_linha"])))
        else:
            bases.append(Decimal("0.00"))
    memoria["base_art_523"] = bases

    base_total_art_523 = moeda(sum(bases, Decimal("0.00")))
    multa_total_art_523, honorarios_total_art_523 = _total_art_523(cfg, base_total_art_523)

    memoria["multa_art_523"] = _rateio_monetario(multa_total_art_523, bases)
    memoria["honorarios_art_523"] = _rateio_monetario(honorarios_total_art_523, bases)
    memoria["total_art_523"] = [
        moeda(D(multa) + D(honorarios))
        for multa, honorarios in zip(memoria["multa_art_523"], memoria["honorarios_art_523"])
    ]
    memoria["total_com_honorarios_e_art_523"] = [
        moeda(D(total) + D(hon) + D(art))
        for total, hon, art in zip(memoria["total"], memoria["honorarios_informados_linha"], memoria["total_art_523"])
    ]
    return memoria
