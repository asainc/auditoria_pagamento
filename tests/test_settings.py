"""Evita regressão da configuração corporativa e vazamento de segredos."""
import secrets

import pytest

from backend import config


CORPORATE_ENV_VARS = [
    "APP_ENV_FILE", "APP_CONFIG_PATH", "APP_ENV", "APP_DATA_DIR",
    "BRADESCO_IAGEN_AMBIENTE", "BRADESCO_IDENTIFICADOR", "BRADESCO_SENHA",
    "BRADESCO_AUTHORIZATION_TOKEN", "BRADESCO_CA_BUNDLE", "BRADESCO_TIMEOUT_SECONDS",
    "BRADESCO_TEXT_MODEL", "BRADESCO_TEXT_REASONING_EFFORT", "BRADESCO_TEXT_VERBOSITY",
    "BRADESCO_TEXT_TEMPERATURE", "BRADESCO_TEXT_MAX_TOKENS", "BRADESCO_PROMPT_MAX_CHARS",
    "GATEWAY_TOKEN", "CORS_ORIGINS",
]


@pytest.fixture
def isolated_settings(monkeypatch, tmp_path):
    for name in CORPORATE_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(config, "ROOT", tmp_path)
    return tmp_path


def test_corporate_token_and_model_are_loaded_from_root_env(isolated_settings, monkeypatch, tmp_path):
    token = secrets.token_urlsafe(32)
    (isolated_settings / ".env").write_text(
        '\ufeffBRADESCO_AUTHORIZATION_TOKEN="' + token + '"\nBRADESCO_TEXT_MODEL=gpt-5.1\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path.parent)
    settings = config.load_settings()
    assert settings.bradesco_authorization_token.get_secret_value() == token
    assert settings.bradesco_text_model == "gpt-5.1"
    assert token not in repr(settings)


def test_environment_wins_over_env_file(isolated_settings, monkeypatch):
    file_token = secrets.token_urlsafe(32)
    environment_token = secrets.token_urlsafe(32)
    (isolated_settings / ".env").write_text("BRADESCO_AUTHORIZATION_TOKEN=" + file_token)
    monkeypatch.setenv("BRADESCO_AUTHORIZATION_TOKEN", environment_token)
    assert config.load_settings().bradesco_authorization_token.get_secret_value() == environment_token


def test_invalid_config_does_not_echo_secret(isolated_settings, monkeypatch):
    secret = secrets.token_urlsafe(32)
    monkeypatch.setenv("BRADESCO_AUTHORIZATION_TOKEN", secret)
    monkeypatch.setenv("BRADESCO_TIMEOUT_SECONDS", "invalido")
    with pytest.raises(ValueError) as caught:
        config.load_settings()
    assert "bradesco_timeout_seconds" in str(caught.value)
    assert secret not in str(caught.value)


def test_missing_explicit_env_file_is_an_error(isolated_settings, monkeypatch):
    monkeypatch.setenv("APP_ENV_FILE", str(isolated_settings / "inexistente.env"))
    with pytest.raises(ValueError, match="APP_ENV_FILE"):
        config.load_settings()
