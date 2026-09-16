"""Evita regressão da leitura de API_TOKEN e vazamento em erros de configuração."""
import secrets
import pytest
from backend import config


@pytest.fixture
def isolated_settings(monkeypatch, tmp_path):
    for name in ["APP_ENV_FILE", "APP_CONFIG_PATH", "APP_ENV", "APP_DATA_DIR", "API_TOKEN", "OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL", "OPENAI_REASONING_EFFORT", "OPENAI_TIMEOUT_SECONDS", "OPENAI_MAX_OUTPUT_TOKENS", "GATEWAY_TOKEN", "CORS_ORIGINS"]:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(config, "ROOT", tmp_path)
    return tmp_path


def test_api_token_is_loaded_from_root_env_from_any_working_directory(isolated_settings, monkeypatch, tmp_path):
    token = secrets.token_urlsafe(32)
    (isolated_settings / ".env").write_text('\ufeffAPI_TOKEN="' + token + '"\nOPENAI_MODEL=gpt-5.6-sol\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path.parent)
    settings = config.load_settings()
    assert settings.openai_api_key.get_secret_value() == token
    assert settings.openai_model == "gpt-5.6-sol"
    assert token not in repr(settings)


def test_environment_wins_and_primary_token_wins_within_same_source(isolated_settings, monkeypatch):
    file_token, alias_token, primary_token = [secrets.token_urlsafe(32) for _ in range(3)]
    (isolated_settings / ".env").write_text("API_TOKEN=" + file_token)
    monkeypatch.setenv("OPENAI_API_KEY", alias_token)
    assert config.load_settings().openai_api_key.get_secret_value() == alias_token
    monkeypatch.setenv("API_TOKEN", primary_token)
    assert config.load_settings().openai_api_key.get_secret_value() == primary_token
    monkeypatch.setenv("API_TOKEN", "")
    assert config.load_settings().openai_api_key.get_secret_value() == ""


def test_invalid_config_does_not_echo_token(isolated_settings, monkeypatch):
    token = secrets.token_urlsafe(32)
    monkeypatch.setenv("API_TOKEN", token)
    monkeypatch.setenv("OPENAI_TIMEOUT_SECONDS", "invalido")
    with pytest.raises(ValueError) as caught:
        config.load_settings()
    assert "openai_timeout_seconds" in str(caught.value)
    assert token not in str(caught.value)


def test_missing_explicit_env_file_is_an_error(isolated_settings, monkeypatch):
    monkeypatch.setenv("APP_ENV_FILE", str(isolated_settings / "inexistente.env"))
    with pytest.raises(ValueError, match="APP_ENV_FILE"):
        config.load_settings()
