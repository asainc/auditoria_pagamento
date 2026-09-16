"""Cálculo de juros fixos simples ou compostos."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from judicial_calc.core.dates import competencias_entre, competencia_data, somar_meses
from judicial_calc.core.numbers import D, moeda


def meses_juros_simples(data_inicio: date, competencia_atualizacao: str, pro_rata: bool = False) -> Decimal:
    """Conta meses de juros simples até a competência de atualização.

    Entrada:
        ``data_inicio``: data inicial dos juros; ``competencia_atualizacao``:
        mês-alvo ``AAAA-MM``; ``pro_rata``: quando ``True``, considera fração
        diária do mês inicial com base de 30 dias.

    Saída:
        ``Decimal`` com número de meses. Ex.: jan/2024 até mar/2024 retorna ``2``.
    """
    comp_inicio = competencia_data(data_inicio)
    comp_fim_exclusivo = competencia_atualizacao
    meses = Decimal(competencias_entre(comp_inicio, comp_fim_exclusivo))
    if pro_rata:
        dias_restantes = max(Decimal(30 - min(data_inicio.day, 30) + 1), Decimal(0))
        meses = max(meses - Decimal(1) + dias_restantes / Decimal(30), Decimal(0))
    return max(meses, Decimal(0))


def _periodos_compostos(data_inicio: date, competencia_atualizacao: str, periodicidade: str) -> Decimal:
    """Conta períodos inteiros usados na capitalização composta.

    Entrada:
        ``data_inicio``: termo inicial; ``competencia_atualizacao``: ``AAAA-MM``;
        ``periodicidade``: ``mensal``, ``anual`` ou ``diaria``.

    Saída:
        ``Decimal`` com número de períodos inteiros.
    """
    meses = Decimal(competencias_entre(competencia_data(data_inicio), competencia_atualizacao))
    if periodicidade == "anual":
        return (meses // Decimal(12))
    if periodicidade == "diaria":
        return Decimal((date(int(competencia_atualizacao[:4]), int(competencia_atualizacao[5:7]), 1) - data_inicio).days)
    return meses


def calcular_juros_fixo(
    valor_base: Decimal,
    data_inicio: date,
    competencia_atualizacao: str,
    taxa: str | Decimal | int | float,
    periodicidade: str = "mensal",
    pro_rata: bool = False,
    tipo: str = "capitalizacao_simples",
) -> tuple[Decimal, Decimal, Decimal]:
    """Calcula juros fixos simples ou compostos.

    Entrada:
        ``valor_base``: base monetária em ``Decimal``; ``data_inicio``: termo
        inicial; ``competencia_atualizacao``: ``AAAA-MM``; ``taxa``: percentual
        por período; ``periodicidade``: ``mensal``, ``anual`` ou ``diaria``;
        ``pro_rata``: fração diária para juros simples mensais; ``tipo``:
        ``capitalizacao_simples`` ou ``capitalizacao_composta``.

    Saída:
        Tupla ``(juros, percentual_decimal, n_periodos)``. Ex.: base ``1000``,
        taxa ``1`` e 2 meses retornam juros ``20.00`` e percentual ``0.02``.
    """
    taxa_decimal = D(taxa) / Decimal("100")
    if taxa_decimal == 0:
        return Decimal("0.00"), Decimal("0"), Decimal("0")

    if tipo == "capitalizacao_composta":
        n = _periodos_compostos(data_inicio, competencia_atualizacao, periodicidade)
        percentual = (Decimal("1") + taxa_decimal) ** int(n) - Decimal("1")
        return moeda(valor_base * percentual), percentual, n

    n = meses_juros_simples(data_inicio, competencia_atualizacao, pro_rata)
    if periodicidade == "anual":
        percentual = taxa_decimal * n / Decimal(12)
    elif periodicidade == "diaria":
        dias = Decimal((date(int(competencia_atualizacao[:4]), int(competencia_atualizacao[5:7]), 1) - data_inicio).days)
        n = max(dias, Decimal(0))
        percentual = taxa_decimal * n
    else:
        percentual = taxa_decimal * n
    return moeda(valor_base * percentual), percentual, n
