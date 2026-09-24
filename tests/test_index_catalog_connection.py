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
