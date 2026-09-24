"""Cliente HTTP e parser de formulários/tabelas históricas do DrCalc."""
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from io import StringIO
import re
from typing import Any, Iterable
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse
import pandas as pd
import requests
from bs4 import BeautifulSoup
from .models import DrCalcRecord, DrCalcSeries, DRCALC_BASE_URL, DRCALC_CATEGORIES, DRCALC_CATEGORY_MATCHERS, DRCALC_HISTORY_START_YEAR
from .parsing import _build_category_url, _decimal_from_ptbr, _normalize_text, _parse_date_like, _periodicity

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
            for target_name, aliases in DRCALC_CATEGORY_MATCHERS.items():
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
