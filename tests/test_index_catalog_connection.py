"""Verifica o contrato de conexão e o catálogo real servido pela aplicação."""
from pathlib import Path


def test_health_matches_frontend_and_indices_are_available(client):
    """Impede que uma divergência de versão volte a bloquear o catálogo no frontend."""
    health = client.get('/api/saude')
    assert health.status_code == 200
    version = health.json()['versao_api']
    source = (Path(__file__).parents[1] / 'frontend/src/app/core/connection-api.service.ts').read_text()
    assert f"health.versao_api !== '{version}'" in source
    result = client.get('/api/indices')
    assert result.status_code == 200
    keys = {item['chave'] for item in result.json()}
    assert {'sem_correcao', 'ipca_ibge', 'igp_m_fgv', 'inpc_ibge'} <= keys


def test_index_catalog_uses_real_local_coverage(client):
    """O rótulo não pode prometer competências ausentes da planilha instalada."""
    from judicial_calc.data_sources.local_excel import local_index_coverage

    response = client.get('/api/indices')
    assert response.status_code == 200
    ipca15 = next(item for item in response.json() if item['chave'] == 'ipca_15_ibge')
    coverage = local_index_coverage('ipca_15_ibge')
    assert ipca15['competencia_inicial'] == coverage.first_competence
    assert ipca15['competencia_final'] == coverage.last_competence
    assert ipca15['competencia_maxima_atualizacao'] == coverage.maximum_update_competence
    assert ipca15['disponivel'] is True
    assert 'ago/2026' not in ipca15['nome']
