"""Atualização diária das planilhas locais de índices a partir do DrCalc.

Este módulo foi desenhado para ser chamado no início do primeiro cálculo do dia.
Ele é conservador por padrão:

- baixa as séries do DrCalc em uma área temporária;
- valida o conteúdo antes de tocar nas planilhas do projeto;
- cria backup/cópia das planilhas atuais;
- só então sobrescreve os arquivos mantendo os mesmos nomes ``.xlsx``;
- registra a data da atualização para evitar nova execução no mesmo dia.

A extração HTML do DrCalc pode mudar ao longo do tempo. Por isso, o módulo
mantém as planilhas antigas quando uma série não é encontrada ou quando a nova
extração não passa pelas validações mínimas. Se a atualização inteira falhar, o
cálculo pode continuar com as planilhas locais anteriores, salvo quando o modo
``strict=True`` for solicitado.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from html import unescape
from io import StringIO
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
from typing import Any, Iterable
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

import pandas as pd
import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook, load_workbook

from judicial_calc.core.numbers import D
from judicial_calc.data_sources.local_excel import (
    DIARIA_12_6_XLSX,
    DIARIA_SELIC_IPCAE_XLSX,
    INDEX_SPECS,
    MENSAL_XLSX,
    RATE_DECIMAL,
    VALUE_INDEX,
    _resource_path,
    load_daily_rate_table,
    load_index_series,
    load_monthly_indices,
    load_taxa_legal_mensal_percentual,
    local_index_specs,
    normalize_key,
)

DRCALC_BASE_URL = "https://drcalc.net/consultaindices.asp?categoria=1&it=1&ml=Series"
DRCALC_HISTORY_START_YEAR = 2000
# IDs usados apenas como fallback. O cliente tenta descobrir os identificadores
# diretamente na navegação do DrCalc antes de montar as URLs. Isso evita que uma
# mudança de categoria no site quebre silenciosamente a atualização.
DRCALC_CATEGORIES: dict[str, int] = {
    "Índices de Preços e Custos": 1,
    "Índices do Mercado Financeiro": 2,
    "Índices de Cálculos Judiciais": 4,
}

_DRCALC_CATEGORY_MATCHERS: dict[str, tuple[str, ...]] = {
    "Índices de Preços e Custos": ("indices de precos e custos", "precos e custos"),
    "Índices do Mercado Financeiro": ("indices do mercado financeiro", "mercado financeiro"),
    "Índices de Cálculos Judiciais": ("indices de calculos judiciais", "calculos judiciais"),
}

PLANILHAS_OBRIGATORIAS = (MENSAL_XLSX, DIARIA_SELIC_IPCAE_XLSX, DIARIA_12_6_XLSX)
STATE_FILENAME = ".drcalc_update_state.json"
LOCK_FILENAME = ".drcalc_update.lock"
BACKUP_DIRNAME = "backups_indices"


@dataclass(frozen=True)
class DrCalcRecord:
    """Uma observação extraída de uma série do DrCalc."""

    periodo: date | str
    valor: Decimal


@dataclass
class DrCalcSeries:
    """Série histórica extraída de uma página do DrCalc."""

    name: str
    url: str
    category: str
    records: list[DrCalcRecord]
    periodicity: str  # "mensal" ou "diaria"
    raw_columns: list[str] = field(default_factory=list)
    metric: str = "unknown"  # "rate_percent", "index_value" ou "unknown"


@dataclass
class DrCalcUpdateResult:
    """Resultado auditável da tentativa de atualização."""

    executed: bool
    skipped: bool
    success: bool
    date: str
    message: str
    backup_dir: str | None = None
    updated_files: list[str] = field(default_factory=list)
    updated_series: list[str] = field(default_factory=list)
    preserved_columns: list[str] = field(default_factory=list)
    source_url: str = DRCALC_BASE_URL
    categories: list[str] = field(default_factory=lambda: list(DRCALC_CATEGORIES.keys()))
    row_counts: dict[str, int] = field(default_factory=dict)
    previous_row_counts: dict[str, int] = field(default_factory=dict)
    diff_summary: list[dict[str, Any]] = field(default_factory=list)
    consistency_checks: list[dict[str, Any]] = field(default_factory=list)
    restored_backup: str | None = None
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serializa o resultado da atualização do DrCalc para um dicionário simples e auditável."""
        return asdict(self)


class DrCalcUpdateError(RuntimeError):
    """Falha controlada da atualização das planilhas locais."""


def _today_str() -> str:
    """Retorna a data corrente em formato ISO para gravação do estado do atualizador."""
    return date.today().isoformat()


def _data_dir(path: str | Path | None = None) -> Path:
    """Resolve a pasta que contém as planilhas locais de índices."""
    if path is not None:
        return Path(path)
    return _resource_path(MENSAL_XLSX).parent


def _state_path(data_dir: Path) -> Path:
    """Resolve o arquivo JSON usado para persistir o estado do atualizador."""
    return data_dir / STATE_FILENAME


def _lock_path(data_dir: Path) -> Path:
    """Resolve o arquivo de lock que impede duas atualizações simultâneas."""
    return data_dir / LOCK_FILENAME


def _load_state(data_dir: Path) -> dict[str, Any]:
    """Lê o estado persistido do atualizador e retorna uma estrutura vazia quando não existe estado válido."""
    path = _state_path(data_dir)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_state(data_dir: Path, result: DrCalcUpdateResult) -> None:
    """Persiste o estado da atualização preservando o último sucesso.

    Quando uma tentativa falha, não apagamos ``last_success_date``. Isso evita
    a mensagem enganosa "sem sucesso registrado" depois de uma falha pontual de
    rede ou de indisponibilidade do DrCalc, desde que já tenha havido uma
    atualização válida anteriormente.
    """
    previous = _load_state(data_dir)
    previous_success = previous.get("last_success_date")
    previous_success_at = previous.get("last_success_at")
    payload = {
        "last_success_date": result.date if result.success else previous_success,
        "last_success_at": datetime.now().isoformat(timespec="seconds") if result.success else previous_success_at,
        "last_attempt_at": datetime.now().isoformat(timespec="seconds"),
        "result": result.to_dict(),
    }
    _state_path(data_dir).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _already_updated_today(data_dir: Path) -> bool:
    """Verifica se já existe atualização bem-sucedida registrada para a data corrente."""
    state = _load_state(data_dir)
    if state.get("last_success_date") != _today_str():
        return False
    # O marcador só vale quando os três arquivos esperados existem.
    return all((data_dir / filename).exists() for filename in PLANILHAS_OBRIGATORIAS)


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


class DrCalcClient:
    """Cliente simples para descobrir e baixar séries do DrCalc."""

    def __init__(self, session: requests.Session | None = None, timeout: int = 30) -> None:
        """Inicializa a instância com as dependências e configurações necessárias ao componente."""
        self.session = session or requests.Session()
        self.timeout = timeout
        self.session.headers.setdefault(
            "User-Agent",
            "Mozilla/5.0 judicial-calculator/1.0 (+https://drcalc.net/consultaindices.asp)",
        )

    def get(self, url: str) -> str:
        """Executa uma requisição HTTP com timeout e tratamento de falhas do cliente."""
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or response.encoding
        return response.text

    def _request_form(self, *, method: str, url: str, payload: dict[str, str]) -> tuple[str, str]:
        """Submete o formulário histórico do DrCalc preservando o método informado pela página.

        O DrCalc é uma aplicação ASP antiga e o formulário de séries históricas
        pode trabalhar por GET ou POST. Em vez de presumir nomes fixos de campos
        ou transformar cada opção do ``select`` em uma URL artificial, esta
        rotina reproduz o formulário efetivamente publicado pela fonte.

        Retorna o HTML e a URL final da resposta para auditoria da origem.
        """
        method_normalized = (method or "get").strip().lower()
        if method_normalized == "post":
            response = self.session.post(url, data=payload, timeout=self.timeout)
        else:
            # ``requests`` adiciona ``params`` ao query string já existente.
            # Como a landing page do DrCalc carrega ``categoria``/``it`` na URL,
            # isso poderia gerar chaves duplicadas (ex.: ``it=1&it=9``). Fazemos
            # merge com sobrescrita para reproduzir uma submissão determinística.
            parsed = urlparse(url)
            merged = {key: values[-1] for key, values in parse_qs(parsed.query).items() if values}
            merged.update(payload)
            request_url = urlunparse(parsed._replace(query=urlencode(merged)))
            response = self.session.get(request_url, timeout=self.timeout)
        response.raise_for_status()
        response.encoding = response.apparent_encoding or response.encoding
        return response.text, str(response.url)

    def discover_series_urls(self) -> list[tuple[str, str, str]]:
        """Retorna tuplas ``(categoria, nome, url)`` encontradas nas categorias alvo.

        A identificação das categorias é feita primeiro a partir dos links da
        própria página do DrCalc. Os IDs fixos ficam somente como fallback para
        manter o atualizador funcional quando a navegação não puder ser lida.
        """
        candidates: dict[str, tuple[str, str, str]] = {}
        for category_name, category_id in self._discover_category_ids():
            category_url = _build_category_url(category_id)
            html = self.get(category_url)
            for name, url in self._extract_links_from_category(html, category_url):
                candidates[url] = (category_name, name, url)
        return list(candidates.values())

    def fetch_historical_series(self) -> list[DrCalcSeries]:
        """Baixa as séries pela consulta histórica oficial do DrCalc.

        A tela ``consultaindices.asp`` não expõe cada indexador como uma página
        histórica independente. O usuário escolhe categoria, período e
        indexador e então submete um formulário. A implementação anterior
        tentava converter os valores do ``select`` em URLs ``it=<id>``; isso
        podia devolver novamente a tela vazia, sem série alguma.

        Aqui o formulário real é identificado e submetido para cada indexador.
        Quando a estrutura não puder ser reconhecida, o chamador ainda pode
        recorrer ao mecanismo legado de descoberta de URLs como fallback.
        """
        series_list: list[DrCalcSeries] = []
        errors: list[str] = []
        for category_name, category_id in self._discover_category_ids():
            category_url = _build_category_url(category_id)
            try:
                html = self.get(category_url)
                category_series = self._fetch_category_form_series(
                    category_name=category_name,
                    category_id=category_id,
                    category_url=category_url,
                    html=html,
                )
                series_list.extend(category_series)
            except Exception as exc:
                errors.append(f"{category_name}: {type(exc).__name__}: {exc}")
        if series_list:
            return series_list
        detail = "; ".join(errors[:3])
        if detail:
            raise DrCalcUpdateError(
                "O formulário de séries históricas do DrCalc foi acessado, "
                f"mas nenhuma série válida foi extraída. Detalhes: {detail}"
            )
        return []

    @staticmethod
    def _select_signature(select: Any) -> str:
        """Produz uma assinatura textual estável para classificar campos do formulário."""
        parts = [str(select.get(attr, "")) for attr in ("name", "id", "class", "title", "aria-label")]
        return _normalize_text(" ".join(parts))

    @staticmethod
    def _numeric_option_values(select: Any) -> list[int]:
        """Retorna valores inteiros das opções quando o campo é predominantemente numérico."""
        values: list[int] = []
        for option in select.find_all("option"):
            raw = str(option.get("value") or "").strip()
            if re.fullmatch(r"\d+", raw):
                values.append(int(raw))
        return values

    def _select_role(self, select: Any) -> str:
        """Classifica ``select`` como categoria, mês, ano, série ou outro.

        Além do nome/id, usa a distribuição dos valores. Isso torna o parser
        tolerante a nomes como ``m1/a1`` ou a pequenas mudanças do HTML.
        """
        signature = self._select_signature(select)
        if any(token in signature for token in ("indice", "indexador", "serie", "series", "subcategoria")):
            return "series"
        if "categoria" in signature:
            return "category"
        if "mes" in signature:
            return "month"
        if "ano" in signature:
            return "year"

        numeric_values = self._numeric_option_values(select)
        if numeric_values:
            if len(numeric_values) >= 6 and all(1 <= value <= 12 for value in numeric_values):
                return "month"
            year_like = [value for value in numeric_values if 1900 <= value <= 2200]
            if len(year_like) >= max(2, int(len(numeric_values) * 0.7)):
                return "year"

        if self._is_series_select(select):
            return "series"
        return "other"

    @staticmethod
    def _field_boundary(signature: str) -> str | None:
        """Infere se o campo representa o início ou o fim do intervalo pesquisado."""
        if any(token in signature for token in ("ini", "inicio", "inicial", "desde", "de_")):
            return "start"
        if any(token in signature for token in ("fim", "final", "ate", "termino")):
            return "end"
        return None

    @staticmethod
    def _option_value_for_number(select: Any, number: int, *, nearest: str) -> str | None:
        """Escolhe a opção numérica desejada respeitando os valores efetivamente publicados."""
        options: list[tuple[int, str]] = []
        for option in select.find_all("option"):
            raw = str(option.get("value") or "").strip()
            if not re.fullmatch(r"\d+", raw):
                continue
            options.append((int(raw), raw))
        if not options:
            return None
        exact = next((raw for value, raw in options if value == number), None)
        if exact is not None:
            return exact
        if nearest == "up":
            higher = sorted((value, raw) for value, raw in options if value >= number)
            if higher:
                return higher[0][1]
            return max(options, key=lambda item: item[0])[1]
        lower = sorted(((value, raw) for value, raw in options if value <= number), reverse=True)
        if lower:
            return lower[0][1]
        return min(options, key=lambda item: item[0])[1]

    @staticmethod
    def _selected_or_first_value(select: Any) -> str | None:
        """Lê a opção selecionada do formulário ou usa a primeira opção com valor."""
        options = select.find_all("option")
        for option in options:
            if option.has_attr("selected"):
                value = str(option.get("value") or "").strip()
                if value:
                    return value
        for option in options:
            value = str(option.get("value") or "").strip()
            if value:
                return value
        return None

    def _find_history_form(self, soup: BeautifulSoup) -> tuple[Any, Any, list[Any], list[Any]] | None:
        """Localiza o formulário de consulta e seus campos de série, mês e ano."""
        for form in soup.find_all("form"):
            selects = [select for select in form.find_all("select") if select.get("name")]
            if not selects:
                continue
            series_candidates = [select for select in selects if self._select_role(select) == "series"]
            month_selects = [select for select in selects if self._select_role(select) == "month"]
            year_selects = [select for select in selects if self._select_role(select) == "year"]
            if series_candidates and len(month_selects) >= 2 and len(year_selects) >= 2:
                # Prefere o campo com mais opções textuais, normalmente o de indexadores.
                series_select = max(series_candidates, key=lambda item: len(item.find_all("option")))
                return form, series_select, month_selects, year_selects
        return None

    def _split_interval_selects(self, selects: list[Any]) -> tuple[Any, Any]:
        """Separa os dois campos equivalentes em início/fim usando nome e ordem do DOM."""
        start = None
        end = None
        for select in selects:
            boundary = self._field_boundary(self._select_signature(select))
            if boundary == "start" and start is None:
                start = select
            elif boundary == "end" and end is None:
                end = select
        if start is None:
            start = selects[0]
        if end is None:
            end = next((select for select in selects if select is not start), selects[-1])
        return start, end

    def _base_form_payload(self, form: Any) -> dict[str, str]:
        """Copia campos ocultos e defaults necessários para reproduzir a submissão do formulário."""
        payload: dict[str, str] = {}
        for input_tag in form.find_all("input"):
            name = str(input_tag.get("name") or "").strip()
            input_type = str(input_tag.get("type") or "text").strip().lower()
            if not name:
                continue
            if input_type in {"hidden", "text"}:
                payload[name] = str(input_tag.get("value") or "")

        for select in form.find_all("select"):
            name = str(select.get("name") or "").strip()
            if not name:
                continue
            default_value = self._selected_or_first_value(select)
            if default_value is not None:
                payload[name] = default_value

        # Alguns formulários ASP dependem do nome/valor do botão de submissão.
        for submit in form.find_all(["input", "button"]):
            submit_type = str(submit.get("type") or "").strip().lower()
            if submit_type not in {"submit", "image"}:
                continue
            name = str(submit.get("name") or "").strip()
            if not name:
                continue
            value = str(submit.get("value") or submit.get_text(" ", strip=True) or "Consultar")
            payload[name] = value
            break
        return payload

    def _fetch_category_form_series(
        self,
        *,
        category_name: str,
        category_id: int,
        category_url: str,
        html: str,
    ) -> list[DrCalcSeries]:
        """Submete o formulário histórico para todos os indexadores de uma categoria."""
        soup = BeautifulSoup(html, "html.parser")
        located = self._find_history_form(soup)
        if located is None:
            raise DrCalcUpdateError("Formulário histórico com período e indexador não foi reconhecido.")
        form, series_select, month_selects, year_selects = located
        series_name = str(series_select.get("name") or "").strip()
        if not series_name:
            raise DrCalcUpdateError("Campo de indexador sem nome no formulário histórico.")

        start_month_select, end_month_select = self._split_interval_selects(month_selects)
        start_year_select, end_year_select = self._split_interval_selects(year_selects)
        start_month_name = str(start_month_select.get("name") or "").strip()
        end_month_name = str(end_month_select.get("name") or "").strip()
        start_year_name = str(start_year_select.get("name") or "").strip()
        end_year_name = str(end_year_select.get("name") or "").strip()

        current = date.today()
        start_year_value = self._option_value_for_number(
            start_year_select, DRCALC_HISTORY_START_YEAR, nearest="up"
        )
        end_year_value = self._option_value_for_number(end_year_select, current.year, nearest="down")
        if start_year_value is None or end_year_value is None:
            raise DrCalcUpdateError("Período histórico do formulário não pôde ser determinado.")
        end_year_number = int(end_year_value)
        end_month_target = current.month if end_year_number == current.year else 12
        start_month_value = self._option_value_for_number(start_month_select, 1, nearest="up")
        end_month_value = self._option_value_for_number(end_month_select, end_month_target, nearest="down")
        if start_month_value is None or end_month_value is None:
            raise DrCalcUpdateError("Meses inicial/final do formulário não puderam ser determinados.")

        base_payload = self._base_form_payload(form)
        base_payload[start_month_name] = start_month_value
        base_payload[end_month_name] = end_month_value
        base_payload[start_year_name] = start_year_value
        base_payload[end_year_name] = end_year_value

        # Garante a categoria correta quando o formulário possui seletor próprio.
        for select in form.find_all("select"):
            if self._select_role(select) != "category":
                continue
            name = str(select.get("name") or "").strip()
            if name:
                base_payload[name] = str(category_id)

        action = str(form.get("action") or category_url).strip()
        action_url = urljoin(category_url, action)
        method = str(form.get("method") or "get").strip().lower()

        result: list[DrCalcSeries] = []
        seen_values: set[str] = set()
        for option in series_select.find_all("option"):
            value = str(option.get("value") or "").strip()
            label = option.get_text(" ", strip=True)
            if not value or not label or len(label) <= 2 or value in seen_values:
                continue
            seen_values.add(value)
            normalized_label = _normalize_text(label)
            if normalized_label in {"selecione", "selecione_o_indexador", "selecione_o_indice"}:
                continue

            payload = dict(base_payload)
            payload[series_name] = value
            try:
                response_html, response_url = self._request_form(method=method, url=action_url, payload=payload)
                response_soup = BeautifulSoup(response_html, "html.parser")
                rate_records, rate_columns = self._extract_records_from_html(
                    response_html, response_soup, preferred_metric="rate"
                )
                index_records, index_columns = self._extract_records_from_html(
                    response_html, response_soup, preferred_metric="index"
                )
            except Exception:
                # Uma série específica pode estar temporariamente indisponível
                # ou ter faixa de datas diferente. As demais séries da categoria
                # continuam sendo processadas e a etapa de merge decide o que é
                # seguro atualizar/preservar.
                continue
            if not rate_records and not index_records:
                continue
            variants: list[tuple[str, list[DrCalcRecord]]] = []
            if rate_records:
                variants.append(("rate_percent", rate_records))
            if index_records and index_records != rate_records:
                variants.append(("index_value", index_records))
            elif index_records and not variants:
                variants.append(("index_value", index_records))
            elif index_records and rate_records:
                # Quando as duas preferências retornam exatamente a mesma
                # coluna, classifica a unidade pelo cabeçalho da tabela. Se o
                # cabeçalho também for genérico, preserva ``unknown`` e o merge
                # mensal será conservador para não trocar número-índice por taxa.
                inferred = self._infer_metric_from_columns(rate_columns or index_columns)
                variants = [(inferred, rate_records)]

            for metric, records in variants:
                result.append(
                    DrCalcSeries(
                        name=label,
                        url=response_url,
                        category=category_name,
                        records=records,
                        periodicity=_periodicity(records),
                        raw_columns=rate_columns if metric != "index_value" else index_columns,
                        metric=metric,
                    )
                )
        return result

    @staticmethod
    def _infer_metric_from_columns(columns: Iterable[str]) -> str:
        """Infere a natureza da métrica pela semântica dos cabeçalhos."""
        norms = {_normalize_text(column) for column in columns}
        if any(any(token in norm for token in ("variacao", "percentual", "taxa")) for norm in norms):
            return "rate_percent"
        if any(any(token in norm for token in ("numero_indice", "valor_indice", "indice", "fator")) for norm in norms):
            return "index_value"
        return "unknown"

    def _discover_category_ids(self) -> list[tuple[str, int]]:
        """Descobre os IDs das três categorias relevantes sem depender de posição fixa.

        O DrCalc já alterou o identificador de categorias ao longo do tempo. A
        rotina compara os rótulos visíveis da navegação e só substitui o fallback
        quando encontra um ID numérico inequívoco no parâmetro ``categoria``.
        """
        resolved = dict(DRCALC_CATEGORIES)
        try:
            html = self.get(DRCALC_BASE_URL)
        except Exception:
            return list(resolved.items())

        soup = BeautifulSoup(html, "html.parser")
        for anchor in soup.find_all("a"):
            href = anchor.get("href")
            label = anchor.get_text(" ", strip=True)
            if not href or not label:
                continue
            parsed = urlparse(urljoin(DRCALC_BASE_URL, href))
            query = parse_qs(parsed.query)
            category_values = query.get("categoria") or []
            if not category_values or not str(category_values[0]).isdigit():
                continue
            normalized_label = _normalize_text(label)
            for target_name, aliases in _DRCALC_CATEGORY_MATCHERS.items():
                if any(alias in normalized_label for alias in aliases):
                    resolved[target_name] = int(category_values[0])
                    break
        return list(resolved.items())

    @staticmethod
    def _is_series_select(select: Any) -> bool:
        """Identifica o ``select`` de indexadores e ignora mês, ano e categoria.

        Formulários ASP antigos costumam expor muitos ``option`` numéricos. Ler
        todos eles como séries cria dezenas de URLs inválidas e aumenta muito o
        tempo de atualização. A seleção abaixo usa o nome/id do campo e um
        fallback conservador baseado nos rótulos das opções.
        """
        signature = _normalize_text(" ".join(str(select.get(attr, "")) for attr in ("name", "id", "class")))
        if any(token in signature for token in ("categoria", "mes", "ano", "inicio", "final")):
            return False
        if any(token in signature for token in ("indice", "indexador", "serie", "series", "it")):
            return True

        labels = [_normalize_text(option.get_text(" ", strip=True)) for option in select.find_all("option") if option.get("value")]
        if len(labels) < 3:
            return False
        month_names = {"jan", "janeiro", "fev", "fevereiro", "mar", "marco", "abr", "abril", "mai", "maio", "jun", "junho", "jul", "julho", "ago", "agosto", "set", "setembro", "out", "outubro", "nov", "novembro", "dez", "dezembro"}
        if sum(label in month_names or label.isdigit() for label in labels) >= max(2, int(len(labels) * 0.7)):
            return False
        category_terms = ("precos e custos", "mercado financeiro", "calculos judiciais", "imobiliarios", "fiscais", "internacionais", "moedas")
        if sum(any(term in label for term in category_terms) for label in labels) >= 2:
            return False
        return True

    def _extract_links_from_category(self, html: str, base_url: str) -> list[tuple[str, str]]:
        """Extrai somente links plausíveis de séries da categoria informada."""
        soup = BeautifulSoup(html, "html.parser")
        found: dict[str, str] = {}
        base_query = parse_qs(urlparse(base_url).query)
        base_category = (base_query.get("categoria") or [""])[0]

        for anchor in soup.find_all("a"):
            href = anchor.get("href")
            label = anchor.get_text(" ", strip=True)
            if not href or not label or len(label) <= 2:
                continue
            url = urljoin(base_url, href)
            parsed = urlparse(url)
            if "consultaindices" not in parsed.path.lower():
                continue
            query = parse_qs(parsed.query)
            if (query.get("categoria") or [base_category])[0] != base_category:
                continue
            item = (query.get("it") or [""])[0]
            if not item or item == base_category:
                continue
            found[url] = label

        for select in soup.find_all("select"):
            if not self._is_series_select(select):
                continue
            for option in select.find_all("option"):
                value = str(option.get("value") or "").strip()
                label = option.get_text(" ", strip=True)
                if not value or not label or len(label) <= 2:
                    continue
                if value.isdigit():
                    parsed = urlparse(base_url)
                    query = parse_qs(parsed.query)
                    query["it"] = [value]
                    query["ml"] = ["Series"]
                    url = urlunparse(parsed._replace(query=urlencode(query, doseq=True)))
                else:
                    url = urljoin(base_url, value)
                    parsed = urlparse(url)
                    query = parse_qs(parsed.query)
                    if "consultaindices" not in parsed.path.lower() and "it" not in query:
                        continue
                found[url] = label

        # Fallback para páginas antigas que geram links por JavaScript. Mantemos
        # apenas URLs da mesma categoria e com um ``it`` diferente da landing page.
        for match in re.finditer(r"consultaindices\.asp\?[^'\"<>\s]+", html, flags=re.I):
            url = urljoin(base_url, unescape(match.group(0)))
            parsed = urlparse(url)
            query = parse_qs(parsed.query)
            if (query.get("categoria") or [base_category])[0] != base_category:
                continue
            item = (query.get("it") or [""])[0]
            if not item or item == base_category:
                continue
            found.setdefault(url, url)

        return [(name, url) for url, name in found.items()]

    def fetch_series(self, category: str, name: str, url: str) -> DrCalcSeries | None:
        """Baixa e interpreta uma série do DrCalc em registros estruturados."""
        html = self.get(url)
        soup = BeautifulSoup(html, "html.parser")
        page_title = self._series_title(soup, name)
        records, raw_columns = self._extract_records_from_html(html, soup)
        if not records:
            return None
        return DrCalcSeries(
            name=page_title,
            url=url,
            category=category,
            records=records,
            periodicity=_periodicity(records),
            raw_columns=raw_columns,
            metric=self._infer_metric_from_columns(raw_columns),
        )

    def _series_title(self, soup: BeautifulSoup, fallback: str) -> str:
        """Obtém um título estável para identificar a série baixada."""
        # O <title> do DrCalc é genérico e, se usado como nome da série, impede
        # o casamento com as colunas locais. O rótulo do próprio <option> é a
        # referência mais estável; cabeçalhos específicos só o substituem quando
        # mencionam parte relevante do indexador selecionado.
        fallback_norm = _normalize_text(fallback)
        fallback_tokens = {token for token in fallback_norm.split("_") if len(token) >= 4}
        for selector in ("h1", "h2", "h3", "caption"):
            tag = soup.find(selector)
            if tag:
                text = tag.get_text(" ", strip=True)
                text_norm = _normalize_text(text)
                if text and len(text) > 2 and any(token in text_norm for token in fallback_tokens):
                    return text
        return fallback

    def _extract_records_from_html(
        self,
        html: str,
        soup: BeautifulSoup,
        preferred_metric: str | None = None,
    ) -> tuple[list[DrCalcRecord], list[str]]:
        # Primeiro tenta pandas.read_html, que lida melhor com tabelas antigas.
        """Extrai registros temporais do HTML da série."""
        tables: list[pd.DataFrame] = []
        try:
            tables.extend(pd.read_html(StringIO(html)))
        except Exception:
            pass

        # Fallback manual com BeautifulSoup.
        for table in soup.find_all("table"):
            rows = []
            for tr in table.find_all("tr"):
                cells = [cell.get_text(" ", strip=True) for cell in tr.find_all(["th", "td"])]
                if cells:
                    rows.append(cells)
            if len(rows) >= 2:
                header = rows[0]
                width = max(len(r) for r in rows)
                normalized = [r + [""] * (width - len(r)) for r in rows[1:]]
                try:
                    tables.append(pd.DataFrame(normalized, columns=header + [f"col_{i}" for i in range(len(header), width)]))
                except Exception:
                    continue

        best_records: list[DrCalcRecord] = []
        best_columns: list[str] = []
        for df in tables:
            records = self._records_from_table(df, preferred_metric=preferred_metric)
            if len(records) > len(best_records):
                best_records = records
                best_columns = [str(c) for c in df.columns]
        return best_records, best_columns

    def _records_from_table(self, df: pd.DataFrame, preferred_metric: str | None = None) -> list[DrCalcRecord]:
        """Converte uma tabela HTML em registros de período e valor."""
        if df.empty or len(df.columns) < 2:
            return []
        if isinstance(df.columns, pd.MultiIndex):
            df = df.copy()
            df.columns = [" ".join(str(part) for part in col if str(part) != "nan").strip() for col in df.columns]

        matrix_records = self._records_from_matrix_table(df)
        if matrix_records:
            return matrix_records

        renamed = {col: _normalize_text(col) for col in df.columns}
        date_cols = [
            col
            for col, norm in renamed.items()
            if norm in {"data", "mes", "competencia", "periodo", "mes_ano", "mesano", "referencia", "termo_inicial"}
        ]
        rate_value_names = (
            "variacao_no_mes",
            "variacao_do_mes",
            "variacao_mensal",
            "variacao_mes",
            "variacao_pct",
            "variacao_percentual",
            "variacao",
            "percentual",
            "taxa",
        )
        index_value_names = (
            "valor_indice",
            "valor_do_indice",
            "numero_indice",
            "numero_do_indice",
            "indice",
            "valor",
            "fator",
        )
        if preferred_metric == "index":
            preferred_value_names = index_value_names + rate_value_names
        else:
            preferred_value_names = rate_value_names + index_value_names
        value_cols = [
            col
            for preferred in preferred_value_names
            for col, norm in renamed.items()
            if norm == preferred
        ]

        # Algumas respostas históricas usam colunas separadas para mês e ano.
        # Nesse caso montamos a competência antes de cair nas heurísticas mais
        # genéricas de detecção de data.
        year_col = next((col for col, norm in renamed.items() if norm in {"ano", "year"}), None)
        month_col = next((col for col, norm in renamed.items() if norm in {"mes", "month"}), None)
        if year_col is not None and month_col is not None:
            if not value_cols:
                candidates = []
                for col in df.columns:
                    if col in {year_col, month_col}:
                        continue
                    parsed = df[col].apply(_decimal_from_ptbr)
                    candidates.append((parsed.notna().sum(), col))
                candidates.sort(reverse=True, key=lambda item: item[0])
                if candidates and candidates[0][0] >= max(2, len(df) // 4):
                    value_cols = [candidates[0][1]]
            if value_cols:
                month_names = {
                    "jan": 1, "janeiro": 1, "fev": 2, "fevereiro": 2,
                    "mar": 3, "marco": 3, "abr": 4, "abril": 4,
                    "mai": 5, "maio": 5, "jun": 6, "junho": 6,
                    "jul": 7, "julho": 7, "ago": 8, "agosto": 8,
                    "set": 9, "setembro": 9, "out": 10, "outubro": 10,
                    "nov": 11, "novembro": 11, "dez": 12, "dezembro": 12,
                }
                records: list[DrCalcRecord] = []
                for _, row in df.iterrows():
                    year_text = re.sub(r"\D", "", str(row.get(year_col) or ""))
                    if len(year_text) != 4:
                        continue
                    year = int(year_text)
                    raw_month = str(row.get(month_col) or "").strip()
                    month = None
                    if re.fullmatch(r"\d{1,2}", raw_month):
                        parsed_month = int(raw_month)
                        if 1 <= parsed_month <= 12:
                            month = parsed_month
                    if month is None:
                        month = month_names.get(_normalize_text(raw_month))
                    value = _decimal_from_ptbr(row.get(value_cols[0]))
                    if month is None or value is None:
                        continue
                    records.append(DrCalcRecord(periodo=f"{year:04d}-{month:02d}", valor=value))
                if records:
                    return records

        if not date_cols:
            # Tenta a primeira coluna com muitas datas válidas.
            scores = []
            for col in df.columns:
                parsed = df[col].apply(_parse_date_like)
                scores.append((parsed.notna().sum(), col))
            scores.sort(reverse=True, key=lambda x: x[0])
            if scores and scores[0][0] >= max(2, len(df) // 4):
                date_cols = [scores[0][1]]
        if not value_cols:
            # Tenta coluna numérica com valores parseáveis, evitando a coluna de datas.
            candidates = []
            for col in df.columns:
                if date_cols and col == date_cols[0]:
                    continue
                parsed = df[col].apply(_decimal_from_ptbr)
                candidates.append((parsed.notna().sum(), col))
            candidates.sort(reverse=True, key=lambda x: x[0])
            if candidates and candidates[0][0] >= max(2, len(df) // 4):
                value_cols = [candidates[0][1]]

        if not date_cols or not value_cols:
            return []

        dcol = date_cols[0]
        vcol = value_cols[0]
        records: list[DrCalcRecord] = []
        for _, row in df.iterrows():
            periodo = _parse_date_like(row.get(dcol))
            valor = _decimal_from_ptbr(row.get(vcol))
            if periodo is None or valor is None:
                continue
            records.append(DrCalcRecord(periodo=periodo, valor=valor))

        # Remove duplicatas mantendo a última ocorrência.
        by_period: dict[str, DrCalcRecord] = {}
        for record in records:
            key = record.periodo.isoformat() if isinstance(record.periodo, date) else str(record.periodo)
            by_period[key] = record
        return sorted(by_period.values(), key=lambda r: r.periodo.isoformat() if isinstance(r.periodo, date) else str(r.periodo))

    def _records_from_matrix_table(self, df: pd.DataFrame) -> list[DrCalcRecord]:
        """Interpreta tabelas históricas no formato ano x meses ou mês x anos.

        Algumas páginas antigas exibem uma linha por ano e uma coluna por mês,
        em vez de uma coluna explícita de competência. Esse formato era ignorado
        pelo parser anterior e fazia uma resposta válida parecer vazia.
        """
        month_aliases = {
            "jan": 1,
            "janeiro": 1,
            "fev": 2,
            "fevereiro": 2,
            "mar": 3,
            "marco": 3,
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
        normalized_columns = {col: _normalize_text(col) for col in df.columns}
        month_columns = {
            col: month_aliases[norm]
            for col, norm in normalized_columns.items()
            if norm in month_aliases
        }

        # Formato: ANO | JAN | FEV | ... | DEZ
        if len(month_columns) >= 3:
            year_col = next(
                (col for col, norm in normalized_columns.items() if norm in {"ano", "year"}),
                df.columns[0],
            )
            records: list[DrCalcRecord] = []
            for _, row in df.iterrows():
                year_text = re.sub(r"\D", "", str(row.get(year_col) or ""))
                if len(year_text) != 4:
                    continue
                year = int(year_text)
                if not 1900 <= year <= 2200:
                    continue
                for col, month in month_columns.items():
                    value = _decimal_from_ptbr(row.get(col))
                    if value is not None:
                        records.append(DrCalcRecord(periodo=f"{year:04d}-{month:02d}", valor=value))
            if records:
                return records

        # Formato transposto: MÊS | 2024 | 2025 | 2026
        if len(df.columns) >= 3:
            first_col = df.columns[0]
            year_columns: dict[Any, int] = {}
            for col in df.columns[1:]:
                norm = _normalize_text(col)
                if re.fullmatch(r"\d{4}", norm):
                    year_columns[col] = int(norm)
            if len(year_columns) >= 2:
                records = []
                for _, row in df.iterrows():
                    month_norm = _normalize_text(row.get(first_col))
                    month = month_aliases.get(month_norm)
                    if month is None:
                        continue
                    for col, year in year_columns.items():
                        value = _decimal_from_ptbr(row.get(col))
                        if value is not None:
                            records.append(DrCalcRecord(periodo=f"{year:04d}-{month:02d}", valor=value))
                if records:
                    return records
        return []


def _series_score(series_name: str, target_label: str, extra_aliases: Iterable[str] = ()) -> int:
    """Calcula uma pontuação heurística para escolher a série mais compatível com um destino."""
    series_norm = _normalize_text(series_name)
    target_norm = _normalize_text(target_label)
    aliases = {_normalize_text(target_label), *[_normalize_text(a) for a in extra_aliases if a]}
    score = 0
    for alias in aliases:
        if not alias:
            continue
        if alias == series_norm:
            score = max(score, 100)
        elif alias in series_norm or series_norm in alias:
            score = max(score, 80)
        else:
            tokens = [t for t in alias.split("_") if len(t) >= 3]
            if tokens:
                common = sum(1 for t in tokens if t in series_norm)
                score = max(score, int(60 * common / len(tokens)))
    return score


def _looks_like_rate_percent(series: DrCalcSeries) -> bool:
    """Avalia de forma conservadora se uma série sem unidade parece percentual.

    A heurística só é usada quando o HTML não informa claramente se o valor é
    variação ou número-índice. Evita gravar, por exemplo, um número-índice de
    centenas como se fosse uma taxa mensal em decimal.
    """
    values = sorted(abs(record.valor) for record in series.records if record.valor is not None)
    if not values:
        return False
    median = values[len(values) // 2]
    p95 = values[min(len(values) - 1, int(len(values) * Decimal("0.95")))] if len(values) > 1 else values[0]
    return median <= Decimal("10") and p95 <= Decimal("50")


def _best_series_for_monthly_column(column: str, series_list: list[DrCalcSeries]) -> DrCalcSeries | None:
    """Seleciona a melhor série mensal para alimentar uma coluna da planilha local."""
    spec = None
    for s in local_index_specs():
        if s.column.strip() == column.strip():
            spec = s
            break
    aliases = []
    if spec:
        aliases.extend([spec.key, spec.column, *spec.aliases])
    best: tuple[int, DrCalcSeries] | None = None
    for series in series_list:
        if series.periodicity != "mensal":
            continue
        score = _series_score(series.name, column, aliases)
        if spec is not None:
            expected_metric = "rate_percent" if spec.mode == RATE_DECIMAL else "index_value"
            if series.metric == expected_metric:
                score += 25
            elif series.metric != "unknown":
                score -= 35
            elif spec.mode == VALUE_INDEX:
                # Sem unidade explícita não é seguro substituir número-índice.
                continue
            elif not _looks_like_rate_percent(series):
                continue
        if score >= 55 and (best is None or score > best[0]):
            best = (score, series)
    return best[1] if best else None


def _best_daily_series(kind: str, series_list: list[DrCalcSeries]) -> DrCalcSeries | None:
    """Seleciona a melhor série diária entre as séries descobertas."""
    if kind == "selic_ipcae":
        aliases = [
            "TAXA LEGAL DIARIA SELIC IPCAE",
            "TAXA LEGAL DIÁRIA SELIC IPCA-E",
            "SELIC IPCA-E",
            "SELIC-IPCAE",
            "Lei 14905 STJ Tema 1368 SELIC IPCA",
        ]
    else:
        aliases = [
            "TAXA LEGAL 12% aa 6% aa",
            "TAXA LEGAL 12 aa 6 aa",
            "12% a.a. 6% a.a.",
            "art. 406 CC 12% 6%",
        ]
    best: tuple[int, DrCalcSeries] | None = None
    for series in series_list:
        if series.periodicity != "diaria":
            continue
        score = max(_series_score(series.name, alias, aliases) for alias in aliases)
        if series.metric == "rate_percent":
            score += 15
        elif series.metric == "index_value":
            score -= 30
        if kind == "selic_ipcae":
            norm = _normalize_text(series.name)
            if "selic" in norm and ("ipcae" in norm or "ipca_e" in norm or "ipca" in norm):
                score += 20
        else:
            norm = _normalize_text(series.name)
            if "12" in norm and "6" in norm:
                score += 20
        if score >= 65 and (best is None or score > best[0]):
            best = (score, series)
    return best[1] if best else None


def _convert_monthly_value(column: str, valor: Decimal, *, source_metric: str = "unknown") -> Decimal:
    """Converte o valor mensal da fonte para a unidade esperada pela planilha local.

    Quando o parser identificou explicitamente ``rate_percent``, o valor do
    DrCalc está em percentual e deve ser dividido por 100 inclusive para taxas
    pequenas, como ``0,03%``. O limiar numérico fica somente para fontes legadas
    sem metadado de unidade.
    """
    spec = None
    for s in local_index_specs():
        if s.column.strip() == column.strip():
            spec = s
            break
    if spec and spec.mode == RATE_DECIMAL:
        if source_metric == "rate_percent":
            return valor / Decimal("100")
        if source_metric == "unknown" and abs(valor) > Decimal("0.05"):
            # Compatibilidade com o fallback legado, cuja unidade nem sempre é
            # identificável pelo cabeçalho da tabela.
            return valor / Decimal("100")
    return valor


def _convert_daily_value(valor: Decimal, *, source_metric: str = "unknown") -> Decimal:
    # Taxa diária em percentual, como 0,03, vira decimal 0,0003.
    """Converte o valor diário da fonte para a unidade esperada pela planilha local."""
    if source_metric == "rate_percent":
        return valor / Decimal("100")
    if source_metric == "unknown" and abs(valor) > Decimal("0.01"):
        return valor / Decimal("100")
    return valor


def _monthly_dataframe_from_workbook(path: Path) -> pd.DataFrame:
    """Lê a planilha mensal existente e normaliza seu conteúdo em DataFrame."""
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb["indices"] if "indices" in wb.sheetnames else wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise DrCalcUpdateError(f"Planilha mensal vazia: {path}")
    headers = [str(h).strip() if h is not None else "" for h in rows[0]]
    data = []
    for raw in rows[1:]:
        if not raw or raw[0] is None:
            continue
        row = {headers[i]: raw[i] if i < len(raw) else None for i in range(len(headers))}
        data.append(row)
    return pd.DataFrame(data, columns=headers)


def _daily_dataframe_from_workbook(path: Path) -> pd.DataFrame:
    """Lê a planilha diária existente e normaliza seu conteúdo em DataFrame."""
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise DrCalcUpdateError(f"Planilha diária vazia: {path}")
    headers = [str(h).strip() if h is not None else "" for h in rows[0]]
    return pd.DataFrame([{headers[i]: raw[i] if i < len(raw) else None for i in range(len(headers))} for raw in rows[1:] if raw and raw[0] is not None])


def _write_monthly_workbook(df: pd.DataFrame, path: Path) -> None:
    """Grava a tabela mensal normalizada no arquivo Excel de destino."""
    wb = Workbook()
    ws = wb.active
    ws.title = "indices"
    for c_idx, header in enumerate(df.columns, start=1):
        ws.cell(row=1, column=c_idx, value=header)
    for r_idx, (_, row) in enumerate(df.iterrows(), start=2):
        for c_idx, column in enumerate(df.columns, start=1):
            value = row[column]
            if pd.isna(value):
                value = None
            if isinstance(value, Decimal):
                value = float(value)
            ws.cell(row=r_idx, column=c_idx, value=value)
    ws.freeze_panes = "A2"
    ws.column_dimensions["A"].width = 12
    for col in range(2, min(len(df.columns), 60) + 1):
        ws.column_dimensions[ws.cell(1, col).column_letter].width = 18
    wb.save(path)


def _write_daily_workbook(df: pd.DataFrame, path: Path) -> None:
    """Grava a tabela diária normalizada no arquivo Excel de destino."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["data", "valor_indice"])
    for _, row in df.iterrows():
        data_value = row["data"]
        if isinstance(data_value, pd.Timestamp):
            data_value = data_value.date()
        valor = row["valor_indice"]
        if isinstance(valor, Decimal):
            valor = float(valor)
        ws.append([data_value, valor])
    ws.freeze_panes = "A2"
    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 18
    wb.save(path)


def _merge_monthly(existing_path: Path, series_list: list[DrCalcSeries]) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Combina séries mensais baixadas com a estrutura da planilha local."""
    df = _monthly_dataframe_from_workbook(existing_path)
    if "data" not in df.columns:
        raise DrCalcUpdateError("taxas_mensais.xlsx precisa ter coluna 'data'.")
    df["data"] = df["data"].astype(str).str[:7]
    df = df.drop_duplicates("data", keep="last").sort_values("data").reset_index(drop=True)
    df = df.set_index("data")

    updated: list[str] = []
    preserved: list[str] = []
    for column in list(df.columns):
        series = _best_series_for_monthly_column(column, series_list)
        if series is None:
            preserved.append(column)
            continue
        changed = False
        for record in series.records:
            competencia = _competencia_from_period(record.periodo)
            value = _convert_monthly_value(column, record.valor, source_metric=series.metric)
            if competencia not in df.index:
                df.loc[competencia, :] = pd.NA
            df.loc[competencia, column] = float(value)
            changed = True
        if changed:
            updated.append(f"{column} <= {series.name}")
        else:
            preserved.append(column)

    if not updated:
        raise DrCalcUpdateError("Nenhuma série mensal compatível foi encontrada no DrCalc.")

    df = df.sort_index().reset_index().rename(columns={"index": "data"})
    ordered = ["data"] + [c for c in _monthly_dataframe_from_workbook(existing_path).columns if c != "data"]
    return df[ordered], updated, preserved


def _merge_daily(existing_path: Path, series: DrCalcSeries | None, label: str) -> tuple[pd.DataFrame, list[str]]:
    """Combina a série diária baixada com a estrutura da planilha local."""
    df = _daily_dataframe_from_workbook(existing_path)
    if "data" not in df.columns or "valor_indice" not in df.columns:
        raise DrCalcUpdateError(f"{existing_path.name} precisa ter colunas data e valor_indice.")
    df["data"] = pd.to_datetime(df["data"]).dt.date
    df = df.drop_duplicates("data", keep="last").sort_values("data").reset_index(drop=True)
    if series is None:
        raise DrCalcUpdateError(f"Série diária não encontrada no DrCalc: {label}.")

    by_date = {row["data"]: row["valor_indice"] for _, row in df.iterrows()}
    for record in series.records:
        if not isinstance(record.periodo, date):
            continue
        by_date[record.periodo] = float(_convert_daily_value(record.valor, source_metric=series.metric))
    if not by_date:
        raise DrCalcUpdateError(f"Nenhum dado diário válido para {label}.")
    out = pd.DataFrame([{"data": k, "valor_indice": v} for k, v in sorted(by_date.items())])
    return out, [f"{label} <= {series.name}"]


def _validate_outputs(monthly: pd.DataFrame, daily_selic_ipcae: pd.DataFrame, daily_12_6: pd.DataFrame) -> None:
    """Valida se as planilhas produzidas possuem estrutura e conteúdo mínimos esperados."""
    if monthly.empty or "data" not in monthly.columns:
        raise DrCalcUpdateError("Saída mensal inválida.")
    if len(monthly.columns) < 5:
        raise DrCalcUpdateError("Saída mensal perdeu colunas demais.")
    for label, df in ((DIARIA_SELIC_IPCAE_XLSX, daily_selic_ipcae), (DIARIA_12_6_XLSX, daily_12_6)):
        if df.empty or set(["data", "valor_indice"]) - set(df.columns):
            raise DrCalcUpdateError(f"Saída diária inválida: {label}.")
        if df["valor_indice"].isna().any():
            raise DrCalcUpdateError(f"Saída diária contém valores vazios: {label}.")


def _backup_planilhas(data_dir: Path) -> Path:
    """Cria cópia de segurança das planilhas antes de substituí-las."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = data_dir / BACKUP_DIRNAME / stamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    for filename in PLANILHAS_OBRIGATORIAS:
        src = data_dir / filename
        if src.exists():
            shutil.copy2(src, backup_dir / filename)
    return backup_dir


def _atomic_replace(src: Path, dst: Path) -> None:
    """Substitui um arquivo de destino de forma atômica após gravação temporária."""
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    if tmp.exists():
        tmp.unlink()
    shutil.copy2(src, tmp)
    os.replace(tmp, dst)


def _df_row_count(path: Path, *, daily: bool = False) -> int:
    """Conta linhas úteis de uma planilha local de índices."""
    if not path.exists():
        return 0
    try:
        df = _daily_dataframe_from_workbook(path) if daily else _monthly_dataframe_from_workbook(path)
        return int(len(df))
    except Exception:
        return 0


def _df_date_range(df: pd.DataFrame, date_col: str = "data") -> tuple[str, str]:
    """Retorna intervalo textual mínimo/máximo de datas/competências."""
    if df.empty or date_col not in df.columns:
        return "", ""
    values = df[date_col].dropna().astype(str)
    if values.empty:
        return "", ""
    return str(values.min()), str(values.max())


def _build_diff_row(filename: str, before_rows: int, after_df: pd.DataFrame) -> dict[str, Any]:
    """Resume diferença de linhas e intervalo de datas de uma planilha."""
    date_min, date_max = _df_date_range(after_df)
    after_rows = int(len(after_df))
    return {
        "arquivo": filename,
        "linhas_antes": int(before_rows),
        "linhas_depois": after_rows,
        "linhas_adicionadas_liquidas": after_rows - int(before_rows),
        "data_minima": date_min,
        "data_maxima": date_max,
    }


def _consistency_checks(monthly: pd.DataFrame, daily_selic_ipcae: pd.DataFrame, daily_12_6: pd.DataFrame) -> list[dict[str, Any]]:
    """Gera checagens legíveis para a tela administrativa de índices."""
    checks = [
        {
            "checagem": "taxas_mensais.xlsx contém coluna data",
            "status": "ok" if "data" in monthly.columns else "falha",
            "detalhe": f"{len(monthly)} linhas; {len(monthly.columns)} colunas",
        },
        {
            "checagem": "taxas_mensais.xlsx preserva ao menos 5 colunas",
            "status": "ok" if len(monthly.columns) >= 5 else "falha",
            "detalhe": f"{len(monthly.columns)} colunas encontradas",
        },
        {
            "checagem": f"{DIARIA_SELIC_IPCAE_XLSX} contém data e valor_indice",
            "status": "ok" if {"data", "valor_indice"}.issubset(daily_selic_ipcae.columns) else "falha",
            "detalhe": f"{len(daily_selic_ipcae)} linhas",
        },
        {
            "checagem": f"{DIARIA_12_6_XLSX} contém data e valor_indice",
            "status": "ok" if {"data", "valor_indice"}.issubset(daily_12_6.columns) else "falha",
            "detalhe": f"{len(daily_12_6)} linhas",
        },
        {
            "checagem": "Planilhas diárias sem valores vazios",
            "status": "ok" if not daily_selic_ipcae.get("valor_indice", pd.Series(dtype=float)).isna().any() and not daily_12_6.get("valor_indice", pd.Series(dtype=float)).isna().any() else "falha",
            "detalhe": "Coluna valor_indice validada antes da substituição atômica.",
        },
    ]
    return checks


def list_drcalc_backups(data_dir: str | Path | None = None) -> list[dict[str, Any]]:
    """Lista backups locais das planilhas de índices."""
    base = _data_dir(data_dir) / BACKUP_DIRNAME
    if not base.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted((p for p in base.iterdir() if p.is_dir()), reverse=True):
        files = [filename for filename in PLANILHAS_OBRIGATORIAS if (path / filename).exists()]
        rows.append(
            {
                "backup_id": path.name,
                "created_at": path.name,
                "path": str(path),
                "arquivos": ", ".join(files),
                "completo": len(files) == len(PLANILHAS_OBRIGATORIAS),
            }
        )
    return rows


def restaurar_backup_drcalc(
    backup_id_or_path: str,
    *,
    data_dir: str | Path | None = None,
) -> DrCalcUpdateResult:
    """Restaura as planilhas a partir de um backup criado pelo atualizador.

    Antes da restauração, cria um novo backup do estado atual, permitindo
    desfazer a restauração caso necessário.
    """
    target_dir = _data_dir(data_dir)
    candidate = Path(backup_id_or_path)
    if not candidate.exists():
        candidate = target_dir / BACKUP_DIRNAME / str(backup_id_or_path)
    if not candidate.exists() or not candidate.is_dir():
        raise DrCalcUpdateError(f"Backup não encontrado: {backup_id_or_path}")
    missing = [filename for filename in PLANILHAS_OBRIGATORIAS if not (candidate / filename).exists()]
    if missing:
        raise DrCalcUpdateError("Backup incompleto. Arquivos ausentes: " + ", ".join(missing))

    safety_backup = _backup_planilhas(target_dir)
    for filename in PLANILHAS_OBRIGATORIAS:
        _atomic_replace(candidate / filename, target_dir / filename)
    _clear_local_caches()
    result = DrCalcUpdateResult(
        executed=True,
        skipped=False,
        success=True,
        date=_today_str(),
        message="Backup de índices restaurado com sucesso.",
        backup_dir=str(safety_backup),
        updated_files=list(PLANILHAS_OBRIGATORIAS),
        restored_backup=str(candidate),
        consistency_checks=[{"checagem": "Backup completo", "status": "ok", "detalhe": str(candidate)}],
    )
    _write_state(target_dir, result)
    return result


def _clear_local_caches() -> None:
    """Limpa caches de leitura de índices para que os próximos cálculos usem os arquivos atuais."""
    for func in (load_monthly_indices, load_index_series, load_daily_rate_table):
        try:
            func.cache_clear()  # type: ignore[attr-defined]
        except Exception:
            pass
    try:
        load_taxa_legal_mensal_percentual.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass
    try:
        from judicial_calc.indices.local_excel import _default_series_map

        _default_series_map.cache_clear()
    except Exception:
        pass
    try:
        from judicial_calc.indices.registry import create_default_index_registry

        create_default_index_registry.cache_clear()
    except Exception:
        pass


def _acquire_lock(data_dir: Path, wait_seconds: int = 20) -> bool:
    """Adquire o lock de atualização e retorna o recurso usado para liberação posterior."""
    lock = _lock_path(data_dir)
    start = time.time()
    while True:
        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(datetime.now().isoformat())
            return True
        except FileExistsError:
            # Remove lock velho com mais de 10 minutos.
            try:
                if time.time() - lock.stat().st_mtime > 600:
                    lock.unlink(missing_ok=True)
                    continue
            except Exception:
                pass
            if time.time() - start > wait_seconds:
                return False
            time.sleep(0.5)


def _release_lock(data_dir: Path) -> None:
    """Libera o lock de atualização adquirido pelo processo."""
    try:
        _lock_path(data_dir).unlink(missing_ok=True)
    except Exception:
        pass


def baixar_series_drcalc(timeout: int = 30) -> list[DrCalcSeries]:
    """Baixa as séries disponíveis nas três categorias alvo do DrCalc.

    A fonte principal é o formulário oficial de ``Séries históricas``. O fluxo
    antigo, que tenta interpretar opções como URLs independentes, permanece
    apenas como fallback de compatibilidade com versões antigas do site.

    Falhas isoladas de uma série não interrompem a coleta inteira, mas as causas
    mais representativas são preservadas na exceção final para facilitar suporte
    quando nenhuma série puder ser confirmada.
    """
    client = DrCalcClient(timeout=timeout)
    series_list: list[DrCalcSeries] = []
    errors: list[str] = []

    try:
        series_list = client.fetch_historical_series()
    except Exception as exc:
        errors.append(f"consulta histórica: {type(exc).__name__}: {exc}")
    if series_list:
        return series_list

    # Fallback para estruturas antigas em que cada opção levava diretamente a
    # uma página de série. Não é mais o caminho preferencial.
    candidates = client.discover_series_urls()
    if not candidates:
        detail = "; ".join(errors[:3])
        suffix = f" Detalhes: {detail}" if detail else ""
        raise DrCalcUpdateError(
            "O DrCalc foi acessado, mas nenhum indexador foi localizado nas categorias configuradas."
            + suffix
        )
    for category, name, url in candidates:
        try:
            series = client.fetch_series(category, name, url)
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
            continue
        if series and series.records:
            series_list.append(series)
    if not series_list:
        detail = "; ".join(errors[:3])
        suffix = f" Causas observadas: {detail}" if detail else ""
        raise DrCalcUpdateError(f"Nenhuma série histórica válida foi extraída do DrCalc.{suffix}")
    return series_list


def atualizar_planilhas_drcalc(
    *,
    data_dir: str | Path | None = None,
    timeout: int = 30,
    series_list: list[DrCalcSeries] | None = None,
) -> DrCalcUpdateResult:
    """Força atualização das três planilhas locais a partir do DrCalc.

    Esta função sempre tenta baixar/mesclar/sobrescrever. Para executar apenas
    uma vez ao dia, use ``atualizar_planilhas_drcalc_se_necessario``.
    """
    target_dir = _data_dir(data_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    for filename in PLANILHAS_OBRIGATORIAS:
        if not (target_dir / filename).exists():
            raise DrCalcUpdateError(f"Planilha obrigatória não encontrada: {target_dir / filename}")

    try:
        previous_row_counts = {
            MENSAL_XLSX: _df_row_count(target_dir / MENSAL_XLSX),
            DIARIA_SELIC_IPCAE_XLSX: _df_row_count(target_dir / DIARIA_SELIC_IPCAE_XLSX, daily=True),
            DIARIA_12_6_XLSX: _df_row_count(target_dir / DIARIA_12_6_XLSX, daily=True),
        }
        series = series_list if series_list is not None else baixar_series_drcalc(timeout=timeout)
        monthly, updated_monthly, preserved = _merge_monthly(target_dir / MENSAL_XLSX, series)
        daily_selic_ipcae_series = _best_daily_series("selic_ipcae", series)
        daily_12_6_series = _best_daily_series("12_6", series)
        daily_selic_ipcae, updated_daily_1 = _merge_daily(
            target_dir / DIARIA_SELIC_IPCAE_XLSX,
            daily_selic_ipcae_series,
            "TAXA LEGAL DIARIA (SELIC-IPCAE)",
        )
        daily_12_6, updated_daily_2 = _merge_daily(
            target_dir / DIARIA_12_6_XLSX,
            daily_12_6_series,
            "TAXA LEGAL - 12% aa - 6% aa",
        )
        _validate_outputs(monthly, daily_selic_ipcae, daily_12_6)
        row_counts = {
            MENSAL_XLSX: int(len(monthly)),
            DIARIA_SELIC_IPCAE_XLSX: int(len(daily_selic_ipcae)),
            DIARIA_12_6_XLSX: int(len(daily_12_6)),
        }
        diff_summary = [
            _build_diff_row(MENSAL_XLSX, previous_row_counts.get(MENSAL_XLSX, 0), monthly),
            _build_diff_row(DIARIA_SELIC_IPCAE_XLSX, previous_row_counts.get(DIARIA_SELIC_IPCAE_XLSX, 0), daily_selic_ipcae),
            _build_diff_row(DIARIA_12_6_XLSX, previous_row_counts.get(DIARIA_12_6_XLSX, 0), daily_12_6),
        ]
        checks = _consistency_checks(monthly, daily_selic_ipcae, daily_12_6)

        with tempfile.TemporaryDirectory(prefix="drcalc_update_") as tmp_name:
            tmp_dir = Path(tmp_name)
            monthly_path = tmp_dir / MENSAL_XLSX
            daily_1_path = tmp_dir / DIARIA_SELIC_IPCAE_XLSX
            daily_2_path = tmp_dir / DIARIA_12_6_XLSX
            _write_monthly_workbook(monthly, monthly_path)
            _write_daily_workbook(daily_selic_ipcae, daily_1_path)
            _write_daily_workbook(daily_12_6, daily_2_path)

            backup_dir = _backup_planilhas(target_dir)
            _atomic_replace(monthly_path, target_dir / MENSAL_XLSX)
            _atomic_replace(daily_1_path, target_dir / DIARIA_SELIC_IPCAE_XLSX)
            _atomic_replace(daily_2_path, target_dir / DIARIA_12_6_XLSX)

        _clear_local_caches()
        result = DrCalcUpdateResult(
            executed=True,
            skipped=False,
            success=True,
            date=_today_str(),
            message="Planilhas de índices atualizadas com sucesso a partir do DrCalc.",
            backup_dir=str(backup_dir),
            updated_files=list(PLANILHAS_OBRIGATORIAS),
            updated_series=updated_monthly + updated_daily_1 + updated_daily_2,
            preserved_columns=preserved,
            previous_row_counts=previous_row_counts,
            row_counts=row_counts,
            diff_summary=diff_summary,
            consistency_checks=checks,
        )
        _write_state(target_dir, result)
        return result
    except Exception as exc:
        result = DrCalcUpdateResult(
            executed=True,
            skipped=False,
            success=False,
            date=_today_str(),
            message="Falha ao atualizar planilhas de índices; planilhas anteriores foram preservadas.",
            errors=[str(exc)],
        )
        _write_state(target_dir, result)
        if isinstance(exc, DrCalcUpdateError):
            raise
        raise DrCalcUpdateError(str(exc)) from exc


def atualizar_planilhas_drcalc_se_necessario(
    *,
    data_dir: str | Path | None = None,
    force: bool = False,
    timeout: int = 30,
    strict: bool = False,
) -> DrCalcUpdateResult:
    """Atualiza as planilhas apenas uma vez por dia.

    Use esta função no início do cálculo. Ela consulta o marcador diário em
    ``.drcalc_update_state.json``. Se já houve sucesso hoje, retorna rápido sem
    acessar a internet.

    Variáveis úteis:
    - ``JUDICIAL_CALC_DISABLE_RATE_UPDATE=1`` desativa a atualização;
    - ``JUDICIAL_CALC_DRCALC_TIMEOUT=15`` ajusta o timeout em segundos.
    """
    target_dir = _data_dir(data_dir)
    today = _today_str()

    if os.getenv("JUDICIAL_CALC_DISABLE_RATE_UPDATE", "0").strip().lower() in {"1", "true", "sim", "yes"}:
        return DrCalcUpdateResult(
            executed=False,
            skipped=True,
            success=True,
            date=today,
            message="Atualização automática das planilhas desativada por variável de ambiente.",
        )

    if not force and _already_updated_today(target_dir):
        state = _load_state(target_dir)
        return DrCalcUpdateResult(
            executed=False,
            skipped=True,
            success=True,
            date=today,
            message="Planilhas já foram atualizadas hoje; atualização ignorada.",
            backup_dir=(state.get("result") or {}).get("backup_dir"),
            updated_files=(state.get("result") or {}).get("updated_files", []),
            updated_series=(state.get("result") or {}).get("updated_series", []),
            preserved_columns=(state.get("result") or {}).get("preserved_columns", []),
            previous_row_counts=(state.get("result") or {}).get("previous_row_counts", {}),
            row_counts=(state.get("result") or {}).get("row_counts", {}),
            diff_summary=(state.get("result") or {}).get("diff_summary", []),
            consistency_checks=(state.get("result") or {}).get("consistency_checks", []),
        )

    if not _acquire_lock(target_dir):
        # Outro processo pode estar atualizando. Evita corrida e permite seguir.
        time.sleep(1)
        if _already_updated_today(target_dir):
            return DrCalcUpdateResult(
                executed=False,
                skipped=True,
                success=True,
                date=today,
                message="Outra execução atualizou as planilhas hoje; atualização ignorada.",
            )
        msg = "Não foi possível obter lock para atualização das planilhas."
        if strict:
            raise DrCalcUpdateError(msg)
        return DrCalcUpdateResult(executed=False, skipped=True, success=False, date=today, message=msg, errors=[msg])

    try:
        try:
            effective_timeout = int(os.getenv("JUDICIAL_CALC_DRCALC_TIMEOUT", str(timeout)))
        except Exception:
            effective_timeout = timeout
        return atualizar_planilhas_drcalc(data_dir=target_dir, timeout=effective_timeout)
    except Exception as exc:
        if strict:
            raise
        result = DrCalcUpdateResult(
            executed=True,
            skipped=False,
            success=False,
            date=today,
            message="Falha ao atualizar planilhas; cálculo deve usar as planilhas locais existentes.",
            errors=[str(exc)],
        )
        # Garante registro coerente mesmo quando a exceção ocorreu antes do
        # ponto em que ``atualizar_planilhas_drcalc`` conseguiu gravar o estado.
        try:
            _write_state(target_dir, result)
        except Exception:
            pass
        return result
    finally:
        _release_lock(target_dir)
