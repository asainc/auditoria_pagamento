"""Normalização de texto, números, períodos e URLs da fonte DrCalc."""
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from html import unescape
import re
import pandas as pd
from typing import Any, Iterable
from urllib.parse import urlencode, urlparse, urlunparse, parse_qs
from judicial_calc.core.numbers import D
from judicial_calc.data_sources.local_excel import normalize_key
from .models import DrCalcRecord, DRCALC_BASE_URL

def _normalize_text(value: Any) -> str:
    """Normaliza texto HTML para comparação de títulos e cabeçalhos de séries."""
    return normalize_key(str(value or ""))


def _decimal_from_ptbr(value: Any) -> Decimal | None:
    """Converte números em formatos PT-BR/EN para Decimal."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return D(value)
        except Exception:
            return None

    text = unescape(str(value)).strip()
    if not text or text in {"-", "–", "—", "nan", "NaN", "None"}:
        return None
    text = re.sub(r"[^0-9,\.\-]", "", text)
    if not text or text in {"-", ".", ","}:
        return None

    # Se há vírgula e ponto, assume o último separador como decimal.
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")

    try:
        return D(text)
    except (InvalidOperation, ValueError):
        return None


def _parse_date_like(value: Any) -> date | str | None:
    """Normaliza datas/competências extraídas do HTML."""
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = unescape(str(value)).strip()
    if not text or text.lower() in {"nan", "none"}:
        return None
    text = re.sub(r"\s+", " ", text)

    month_names = {
        "jan": 1,
        "janeiro": 1,
        "fev": 2,
        "fevereiro": 2,
        "mar": 3,
        "marco": 3,
        "março": 3,
        "abr": 4,
        "abril": 4,
        "mai": 5,
        "maio": 5,
        "jun": 6,
        "junho": 6,
        "jul": 7,
        "julho": 7,
        "ago": 8,
        "agosto": 8,
        "set": 9,
        "setembro": 9,
        "out": 10,
        "outubro": 10,
        "nov": 11,
        "novembro": 11,
        "dez": 12,
        "dezembro": 12,
    }

    patterns = [
        (r"^(\d{4})-(\d{2})-(\d{2})$", "%Y-%m-%d"),
        (r"^(\d{2})/(\d{2})/(\d{4})$", "%d/%m/%Y"),
        (r"^(\d{4})-(\d{2})$", "%Y-%m"),
        (r"^(\d{2})/(\d{4})$", "%m/%Y"),
    ]
    for regex, fmt in patterns:
        if re.match(regex, text):
            dt = datetime.strptime(text, fmt)
            if fmt in {"%Y-%m", "%m/%Y"}:
                return f"{dt.year:04d}-{dt.month:02d}"
            return dt.date()

    m = re.match(r"^([A-Za-zÀ-ÿ]{3,9})/?\s*(\d{2,4})$", text, flags=re.I)
    if m:
        month_key = _normalize_text(m.group(1))
        year = int(m.group(2))
        if year < 100:
            year += 2000 if year < 50 else 1900
        month = month_names.get(month_key)
        if month:
            return f"{year:04d}-{month:02d}"

    return None


def _periodicity(records: Iterable[DrCalcRecord]) -> str:
    """Infere a periodicidade de uma série a partir dos períodos observados."""
    for record in records:
        if isinstance(record.periodo, date):
            return "diaria"
    return "mensal"


def _competencia_from_period(periodo: date | str) -> str:
    """Converte um período mensal para a competência canônica AAAA-MM."""
    if isinstance(periodo, date):
        return f"{periodo.year:04d}-{periodo.month:02d}"
    return str(periodo)[:7]


def _build_category_url(category_id: int) -> str:
    """Monta a URL inicial de uma categoria do DrCalc.

    O site usa ``categoria`` e ``it`` em conjunto na navegação principal. Manter
    os dois valores sincronizados evita abrir uma categoria com o identificador
    de navegação de outra seção, comportamento que pode devolver um formulário
    válido visualmente, porém sem os indexadores esperados.
    """
    parsed = urlparse(DRCALC_BASE_URL)
    query = parse_qs(parsed.query)
    query["categoria"] = [str(category_id)]
    query["it"] = [str(category_id)]
    query["ml"] = ["Series"]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))
