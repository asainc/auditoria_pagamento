"""Testes de regressão do atualizador externo de índices.

Os cenários usam HTML sintético para validar a descoberta sem depender de rede.
"""
from __future__ import annotations

from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

from backend.services.indices import _public_update_failure
from judicial_calc.data_sources.drcalc_updater import DrCalcClient, _build_category_url


class NavigationClient(DrCalcClient):
    """Cliente de teste que devolve uma navegação conhecida sem acesso externo."""

    def __init__(self, html: str) -> None:
        super().__init__(timeout=1)
        self.html = html

    def get(self, url: str) -> str:
        """Ignora a URL porque este teste valida somente o parser de navegação."""
        return self.html


def test_category_url_keeps_category_and_navigation_id_in_sync() -> None:
    """A landing page deve usar o mesmo ID em ``categoria`` e ``it``."""
    query = parse_qs(urlparse(_build_category_url(4)).query)
    assert query["categoria"] == ["4"]
    assert query["it"] == ["4"]
    assert query["ml"] == ["Series"]


def test_client_discovers_current_judicial_category_from_navigation_label() -> None:
    """Mudanças de ID são absorvidas pelo rótulo exibido no próprio DrCalc."""
    html = """
    <nav>
      <a href="consultaindices.asp?categoria=1&it=1&ml=Series">Índices de Preços e Custos</a>
      <a href="consultaindices.asp?categoria=2&it=2&ml=Series">Índices do Mercado Financeiro</a>
      <a href="consultaindices.asp?categoria=4&it=4&ml=Series">Índices de Cálculos Judiciais</a>
    </nav>
    """
    discovered = dict(NavigationClient(html)._discover_category_ids())
    assert discovered["Índices de Preços e Custos"] == 1
    assert discovered["Índices do Mercado Financeiro"] == 2
    assert discovered["Índices de Cálculos Judiciais"] == 4


def test_category_parser_ignores_month_year_and_category_selects() -> None:
    """Somente o seletor de indexadores pode gerar URLs de séries."""
    html = """
    <form>
      <select name="categoria">
        <option value="1">Índices de Preços e Custos</option>
        <option value="4">Índices de Cálculos Judiciais</option>
      </select>
      <select name="mesinicio">
        <option value="1">Janeiro</option><option value="2">Fevereiro</option><option value="3">Março</option>
      </select>
      <select name="anoinicio">
        <option value="2024">2024</option><option value="2025">2025</option><option value="2026">2026</option>
      </select>
      <select name="it" id="indexador">
        <option value="">Selecione</option>
        <option value="101">TJSP - Tabela judicial</option>
        <option value="102">TST - Débitos trabalhistas</option>
      </select>
    </form>
    """
    client = NavigationClient(html)
    links = client._extract_links_from_category(html, _build_category_url(4))
    assert [name for name, _ in links] == ["TJSP - Tabela judicial", "TST - Débitos trabalhistas"]
    assert [parse_qs(urlparse(url).query)["it"][0] for _, url in links] == ["101", "102"]


def test_public_failure_message_distinguishes_invalid_remote_series() -> None:
    """A interface recebe uma causa útil sem expor o detalhe técnico integral."""
    result = SimpleNamespace(
        message="Falha ao atualizar planilhas.",
        errors=["Nenhuma série histórica válida foi extraída do DrCalc."],
    )
    message = _public_update_failure(result)
    assert "não encontrou séries válidas" in message
    assert "preservadas" in message


def test_index_service_uses_result_success_instead_of_message_text(tmp_path, monkeypatch) -> None:
    """Resultado bem-sucedido não pode virar falha por heurística textual."""
    from threading import Lock

    from backend.config import Settings
    from backend.repository import Repository
    from backend.services import indices as indices_service
    from judicial_calc.data_sources.drcalc_updater import DrCalcUpdateResult

    result = DrCalcUpdateResult(
        executed=False,
        skipped=True,
        success=True,
        date="2026-09-13",
        message="Atualização previamente confirmada nesta execução.",
    )
    monkeypatch.setattr(indices_service, "atualizar_planilhas_drcalc_se_necessario", lambda **_: result)
    service = indices_service.IndexService(Settings(data_dir=tmp_path), Repository(tmp_path), SimpleNamespace(lock=Lock()))
    try:
        service.run()
        status = service.status()
        assert status.estado == "atualizado"
        assert status.mensagem == result.message
    finally:
        service.close()


def test_index_service_preserves_previous_files_on_remote_failure(tmp_path, monkeypatch) -> None:
    """Falha de descoberta deve ser explícita e não apagar o snapshot local."""
    from threading import Lock

    from backend.config import Settings
    from backend.repository import Repository
    from backend.services import indices as indices_service
    from judicial_calc.data_sources.drcalc_updater import DrCalcUpdateResult

    result = DrCalcUpdateResult(
        executed=True,
        skipped=False,
        success=False,
        date="2026-09-13",
        message="Falha ao atualizar planilhas.",
        errors=["Nenhuma série histórica válida foi extraída do DrCalc."],
    )
    monkeypatch.setattr(indices_service, "atualizar_planilhas_drcalc_se_necessario", lambda **_: result)
    service = indices_service.IndexService(Settings(data_dir=tmp_path), Repository(tmp_path), SimpleNamespace(lock=Lock()))
    try:
        service.run()
        status = service.status()
        assert status.estado == "falha"
        assert "não encontrou séries válidas" in status.mensagem
        assert "preservadas" in status.mensagem
    finally:
        service.close()


def test_index_service_does_not_claim_new_data_when_source_has_no_later_competence(tmp_path, monkeypatch) -> None:
    """Consulta bem-sucedida sem avanço deve ter estado próprio, não 'atualizado'."""
    from threading import Lock

    from backend.config import Settings
    from backend.repository import Repository
    from backend.services import indices as indices_service
    from judicial_calc.data_sources.drcalc_updater import DrCalcUpdateResult

    result = DrCalcUpdateResult(
        executed=True,
        skipped=False,
        success=True,
        date="2026-09-24",
        message="Verificação concluída sem competência posterior.",
        has_new_competence=False,
    )
    monkeypatch.setattr(indices_service, "atualizar_planilhas_drcalc_se_necessario", lambda **_: result)
    service = indices_service.IndexService(Settings(data_dir=tmp_path), Repository(tmp_path), SimpleNamespace(lock=Lock()))
    try:
        service.run()
        status = service.status()
        assert status.estado == "sem_novidade"
        assert status.mensagem == result.message
    finally:
        service.close()


class _FakeResponse:
    """Resposta HTTP mínima para validar a submissão sem rede externa."""

    def __init__(self, text: str, url: str) -> None:
        self.text = text
        self.url = url
        self.encoding = "utf-8"
        self.apparent_encoding = "utf-8"

    def raise_for_status(self) -> None:
        return None


class _HistorySession:
    """Sessão sintética que devolve uma tabela histórica conforme o indexador."""

    def __init__(self) -> None:
        self.headers: dict[str, str] = {}
        self.calls: list[tuple[str, str, dict[str, str]]] = []

    def get(self, url: str, params=None, timeout=None):
        from urllib.parse import parse_qs, urlparse

        payload = {str(k): str(v) for k, v in (params or {}).items()}
        if not payload:
            payload = {key: values[-1] for key, values in parse_qs(urlparse(url).query).items() if values}
        self.calls.append(("get", url, payload))
        return _FakeResponse(self._result_html(payload), url + "?submitted=1")

    def post(self, url: str, data=None, timeout=None):
        payload = {str(k): str(v) for k, v in (data or {}).items()}
        self.calls.append(("post", url, payload))
        return _FakeResponse(self._result_html(payload), url + "?submitted=1")

    @staticmethod
    def _result_html(payload: dict[str, str]) -> str:
        if not payload.get("indice"):
            return "<html><body>sem resultado</body></html>"
        return """
        <html><body>
          <table>
            <tr><th>Mês/Ano</th><th>Número Índice</th><th>Variação no mês</th></tr>
            <tr><td>07/2026</td><td>123,0000</td><td>0,25%</td></tr>
            <tr><td>08/2026</td><td>123,3936</td><td>0,32%</td></tr>
          </table>
        </body></html>
        """


def test_client_submits_real_history_form_instead_of_inventing_series_url() -> None:
    """O indexador deve ser enviado ao formulário histórico com início/fim explícitos."""
    html = """
    <html><body>
      <form action="consultaindices.asp" method="get">
        <select name="categoria"><option value="1" selected>Índices de Preços e Custos</option></select>
        <select name="mesini"><option value="1">Janeiro</option><option value="2">Fevereiro</option></select>
        <select name="anoini"><option value="1999">1999</option><option value="2000">2000</option><option value="2026">2026</option></select>
        <select name="mesfim"><option value="1">Janeiro</option><option value="8">Agosto</option><option value="9">Setembro</option><option value="12">Dezembro</option></select>
        <select name="anofim"><option value="2025">2025</option><option value="2026">2026</option></select>
        <select name="indice" id="indexador">
          <option value="">Selecione</option>
          <option value="9">IPCA (IBGE)</option>
        </select>
        <input type="submit" name="Consultar" value="Consultar">
      </form>
    </body></html>
    """
    session = _HistorySession()
    client = DrCalcClient(session=session, timeout=1)
    series = client._fetch_category_form_series(
        category_name="Índices de Preços e Custos",
        category_id=1,
        category_url=_build_category_url(1),
        html=html,
    )

    assert {item.metric for item in series} == {"rate_percent", "index_value"}
    assert all(item.name == "IPCA (IBGE)" for item in series)
    assert session.calls
    _, _, payload = session.calls[0]
    assert payload["indice"] == "9"
    assert payload["anoini"] == "2000"
    assert payload["anofim"] == "2026"
    assert payload["mesini"] == "1"
    assert payload["Consultar"] == "Consultar"


def test_history_parser_selects_variation_or_index_according_to_requested_metric() -> None:
    """Uma tabela com duas métricas não pode confundir variação com número-índice."""
    import pandas as pd

    df = pd.DataFrame(
        {
            "Mês/Ano": ["07/2026", "08/2026"],
            "Número Índice": ["123,0000", "123,3936"],
            "Variação no mês": ["0,25%", "0,32%"],
        }
    )
    client = DrCalcClient(session=_HistorySession(), timeout=1)
    rate = client._records_from_table(df, preferred_metric="rate")
    index = client._records_from_table(df, preferred_metric="index")

    assert [str(item.valor) for item in rate] == ["0.25", "0.32"]
    assert [str(item.valor) for item in index] == ["123.0000", "123.3936"]


def test_history_parser_accepts_separate_month_and_year_columns() -> None:
    """O parser deve aceitar o formato Ano + Mês + Variação usado por páginas legadas."""
    import pandas as pd

    df = pd.DataFrame(
        {
            "Ano": [2026, 2026],
            "Mês": ["Julho", "Agosto"],
            "Variação %": ["0,25", "0,32"],
        }
    )
    client = DrCalcClient(session=_HistorySession(), timeout=1)
    records = client._records_from_table(df, preferred_metric="rate")

    assert [item.periodo for item in records] == ["2026-07", "2026-08"]
    assert [str(item.valor) for item in records] == ["0.25", "0.32"]


def test_history_parser_accepts_year_by_month_matrix() -> None:
    """O parser deve reconhecer tabelas com uma linha por ano e meses em colunas."""
    import pandas as pd

    df = pd.DataFrame(
        {
            "Ano": [2026],
            "Jan": ["0,50"],
            "Fev": ["0,40"],
            "Mar": ["0,30"],
        }
    )
    client = DrCalcClient(session=_HistorySession(), timeout=1)
    records = client._records_from_table(df, preferred_metric="rate")

    assert [item.periodo for item in records] == ["2026-01", "2026-02", "2026-03"]


def test_explicit_percent_metric_converts_small_monthly_rate_without_threshold_error() -> None:
    """0,03% do DrCalc deve virar 0,0003 mesmo sendo menor que o limiar legado."""
    from decimal import Decimal
    from judicial_calc.data_sources.drcalc_updater import _convert_monthly_value

    converted = _convert_monthly_value("IPCA (IBGE)", Decimal("0.03"), source_metric="rate_percent")
    assert converted == Decimal("0.0003")


def test_explicit_percent_metric_converts_small_daily_rate_without_threshold_error() -> None:
    """Taxa diária 0,005% deve virar 0,00005 quando a unidade é explícita."""
    from decimal import Decimal
    from judicial_calc.data_sources.drcalc_updater import _convert_daily_value

    converted = _convert_daily_value(Decimal("0.005"), source_metric="rate_percent")
    assert converted == Decimal("0.00005")
