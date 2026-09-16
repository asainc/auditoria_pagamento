"""Funções utilitárias para datas e competências mensais."""
from __future__ import annotations

import re
from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Iterable

from judicial_calc.core.constants import MESES_PT


def _int_flex(valor: str | int, nome: str) -> int:
    """Converte inteiros que podem chegar como 2026.0/"2026.0"."""
    if isinstance(valor, bool):
        return 1 if valor else 0
    texto = str(valor).strip()
    try:
        dec = Decimal(texto.replace(",", "."))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{nome} deve ser um número inteiro.") from exc
    if dec != dec.to_integral_value():
        raise ValueError(f"{nome} deve ser um número inteiro.")
    return int(dec)


def parse_mes_ano(mes: str | int, ano: str | int) -> str:
    """Converte mês e ano em competência ``AAAA-MM``.

    Entrada:
        ``mes``: inteiro ``1`` a ``12`` ou texto em português, como
        ``"Agosto"``; ``ano``: inteiro ou texto com quatro dígitos.

    Saída:
        ``str`` no formato ``AAAA-MM``.

    Exemplo:
        ``parse_mes_ano("Agosto", 2024)`` retorna ``"2024-08"``.
    """
    if isinstance(mes, str):
        chave = mes.strip().lower()
        mes_num = _int_flex(chave, "mes") if chave.replace(",", ".").replace(".", "", 1).isdigit() else MESES_PT[chave]
    else:
        mes_num = _int_flex(mes, "mes")
    return f"{_int_flex(ano, 'ano'):04d}-{mes_num:02d}"


def parse_data(valor: str | date | datetime) -> date:
    """Converte uma entrada de data para ``datetime.date``.

    Entrada:
        ``valor``: ``date``, ``datetime`` ou texto ``YYYY-MM-DD``/``DD/MM/YYYY``.

    Saída:
        ``datetime.date``.

    Exemplo:
        ``parse_data("31/01/2024")`` retorna ``date(2024, 1, 31)``.
    """
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor).strip()
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", texto):
        return datetime.strptime(texto, "%d/%m/%Y").date()
    return datetime.strptime(texto[:10], "%Y-%m-%d").date()


def competencia_data(d: date) -> str:
    """Extrai a competência mensal de uma data.

    Entrada:
        ``d``: ``datetime.date``.

    Saída:
        ``str`` ``AAAA-MM``.

    Exemplo:
        ``competencia_data(date(2024, 8, 27))`` retorna ``"2024-08"``.
    """
    return f"{d.year:04d}-{d.month:02d}"


def data_primeiro_dia(comp: str) -> date:
    """Retorna o primeiro dia de uma competência.

    Entrada:
        ``comp``: competência ``AAAA-MM``.

    Saída:
        ``datetime.date`` no primeiro dia do mês.
    """
    return date(int(comp[:4]), int(comp[5:7]), 1)


def ultimo_dia_mes(comp: str) -> date:
    """Retorna o último dia de uma competência.

    Entrada:
        ``comp``: competência ``AAAA-MM``.

    Saída:
        ``datetime.date`` no último dia do mês, respeitando ano bissexto.
    """
    d = data_primeiro_dia(comp)
    return date(d.year, d.month, monthrange(d.year, d.month)[1])


def somar_meses(comp: str, meses: int) -> str:
    """Soma ou subtrai meses de uma competência.

    Entrada:
        ``comp``: competência ``AAAA-MM``; ``meses``: inteiro positivo,
        zero ou negativo.

    Saída:
        ``str`` ``AAAA-MM``.

    Exemplo:
        ``somar_meses("2024-01", -1)`` retorna ``"2023-12"``.
    """
    ano = int(comp[:4])
    mes = int(comp[5:7]) + meses
    ano += (mes - 1) // 12
    mes = (mes - 1) % 12 + 1
    return f"{ano:04d}-{mes:02d}"


def iter_competencias(inicio: str, fim: str) -> Iterable[str]:
    """Itera competências mensais em intervalo fechado.

    Entrada:
        ``inicio`` e ``fim``: competências ``AAAA-MM``.

    Saída:
        Iterável de ``str``. Ex.: ``2024-01`` a ``2024-03`` gera três valores.
    """
    atual = inicio
    while atual <= fim:
        yield atual
        atual = somar_meses(atual, 1)


def competencias_entre(inicio: str, fim: str) -> int:
    """Conta a diferença em meses entre duas competências.

    Entrada:
        ``inicio`` e ``fim``: competências ``AAAA-MM``.

    Saída:
        ``int``. Ex.: de ``2024-01`` a ``2024-04`` retorna ``3``.
    """
    return (int(fim[:4]) - int(inicio[:4])) * 12 + int(fim[5:7]) - int(inicio[5:7])
