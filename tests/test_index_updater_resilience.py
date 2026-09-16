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
