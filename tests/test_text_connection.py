"""Regressões de transporte com requisições interceptadas e conteúdo sintético."""
import secrets

import pytest
import requests

import gpt_bradesco as corporate
from backend.config import Settings, load_settings
from backend.services.bradesco_bridge import BradescoBridgeClient, BradescoBridgeError


@pytest.fixture
def transport(monkeypatch):
    """Isola o estado do módulo para impedir acesso à rede e contaminação entre testes."""
    monkeypatch.setattr(corporate, '_AUTH_CONFIG', {})
    monkeypatch.setattr(corporate, '_TOKEN_CACHE', None)
    monkeypatch.setenv('BRADESCO_AUTHORIZATION_TOKEN', secrets.token_urlsafe(24))
    for name in ('BRADESCO_TEXT_URL', 'BRADESCO_TEXT_URL_HOMOL', 'BRADESCO_IDENTITY_URL'):
        monkeypatch.delenv(name, raising=False)
    calls = []

    def request(method, url, **kwargs):
        """Devolve o envelope esperado sem acessar serviços externos."""
        calls.append((method, url, kwargs))
        response = requests.Response()
        response.status_code = 200
        response._content = b'{"response":{"output_text":"{}"}}'
        return response

    monkeypatch.setattr(corporate.requests, 'request', request)
    return calls


def test_transport_receives_environment_timeout_and_ca_without_settings_credentials(transport, tmp_path):
    """Credenciais no processo não podem fazer o backend ignorar ambiente e CA."""
    ca = tmp_path / 'synthetic.pem'
    ca.write_text('arquivo sintetico; TLS interceptado no teste')
    settings = Settings(bradesco_text_model='synthetic-model', bradesco_environment='homol',
                        bradesco_timeout_seconds=345, bradesco_ca_bundle=ca)
    assert BradescoBridgeClient(settings).generate_text('Mensagem sintética', max_tokens=1024) == '{}'
    _, url, arguments = transport[0]
    assert url.startswith(corporate._BASE_URLS['homol'])
    assert arguments['timeout'] == 345
    assert arguments['verify'] == str(ca)


def test_env_file_custom_urls_reach_transport(transport, monkeypatch, tmp_path):
    """URLs do .env chegam ao cliente sem exportar variáveis globais."""
    env = tmp_path / 'settings.env'
    env.write_text('BRADESCO_TEXT_MODEL=synthetic-model\n'
                   'BRADESCO_TEXT_URL=https://text.example.invalid/generate\n'
                   'BRADESCO_IDENTITY_URL=https://identity.example.invalid/login\n'
                   'BRADESCO_AMBIENTE=homol\nBRADESCO_TIMEOUT=345\n')
    monkeypatch.setenv('APP_ENV_FILE', str(env))
    settings = load_settings()
    BradescoBridgeClient(settings).generate_text('Mensagem sintética', max_tokens=1024)
    assert transport[0][1] == 'https://text.example.invalid/generate'
    assert corporate._service_url('identity') == 'https://identity.example.invalid/login'
    assert settings.bradesco_environment == 'homol'
    assert transport[0][2]['timeout'] == 345


@pytest.mark.parametrize('failure,code', [
    (requests.exceptions.SSLError, 'bradesco_certificado_invalido'),
    (requests.exceptions.Timeout, 'bradesco_tempo_esgotado'),
    (requests.exceptions.ConnectionError, 'bradesco_falha_rede'),
])
def test_wrapped_transport_errors_are_actionable_and_sanitized(transport, monkeypatch, failure, code):
    """A classificação preserva a causa técnica sem ecoar conteúdo externo."""
    def request(*args, **kwargs):
        """Simula falha antes de receber uma resposta do servidor."""
        raise failure('conteudo-que-nao-pode-aparecer')

    monkeypatch.setattr(corporate.requests, 'request', request)
    client = BradescoBridgeClient(Settings(bradesco_text_model='synthetic-model'))
    with pytest.raises(BradescoBridgeError) as caught:
        client.generate_text('Mensagem sintética', max_tokens=1024)
    assert caught.value.code == code
    assert 'conteudo-que-nao-pode-aparecer' not in caught.value.message
