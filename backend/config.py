"""Configuração validada; erros não são substituídos silenciosamente por padrões."""
from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import Field, SecretStr, ValidationError, field_validator, model_validator
from starlette.config import Config
from typing import Literal
from backend.models import Contract, InterestType
from backend.calculation_policy import defaults_for_origin

ROOT = Path(__file__).resolve().parents[1]


class OperationalSettings(Contract):
    """Visão tipada dos padrões documentais definidos no catálogo central.

    A classe existe para manter injeção explícita nos serviços, mas não é uma fonte
    de configuração independente. Os valores vêm de ``calculation_policy.json``.
    """
    default_index: str = Field(default_factory=lambda: str(defaults_for_origin("processo")["indice"]), frozen=True)
    default_moratory_type: InterestType = Field(default_factory=lambda: defaults_for_origin("processo")["juros_moratorios_tipo"], frozen=True)
    default_compensatory_type: InterestType = Field(default_factory=lambda: defaults_for_origin("processo")["juros_compensatorios_tipo"], frozen=True)
    default_art_523: Literal["nao_aplicar", "aplicar_multa", "aplicar_multa_honorarios"] = Field(default_factory=lambda: defaults_for_origin("processo")["art_523"], frozen=True)


class Settings(Contract):
    """Parâmetros operacionais centralizados; segredos vêm do ambiente."""
    environment: str = "local"
    operational: OperationalSettings = Field(default_factory=OperationalSettings)
    data_dir: Path = ROOT / "data"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:4200", "http://127.0.0.1:4200"])
    max_upload_bytes: int = Field(default=20 * 1024 * 1024, ge=1024, le=100 * 1024 * 1024)
    max_upload_files: int = Field(default=20, ge=1, le=100)
    extraction_workers: int = Field(default=2, ge=1, le=4)

    # Integração corporativa: segredos são lidos somente do ambiente/.env local.
    bradesco_environment: Literal["dev", "homol", "prod"] = "dev"
    bradesco_identificador: SecretStr = SecretStr("")
    bradesco_senha: SecretStr = SecretStr("")
    bradesco_authorization_token: SecretStr = SecretStr("")
    bradesco_ca_bundle: Path | None = None
    bradesco_timeout_seconds: int = Field(default=600, ge=10, le=1800)

    # Geração de texto usada por TODOS os prompts do projeto.
    bradesco_text_model: str = Field(default="", max_length=100)
    bradesco_text_reasoning_effort: Literal["none", "low", "medium", "high"] = "medium"
    bradesco_text_verbosity: Literal["low", "medium", "high"] = "medium"
    bradesco_text_modalities: Literal["text"] = "text"
    bradesco_text_temperature: float = Field(default=1.0, ge=0, le=2)
    bradesco_text_max_tokens: int = Field(default=16384, ge=1024, le=65536)
    bradesco_prompt_max_chars: int = Field(default=55000, ge=10000, le=250000)

    gateway_token: SecretStr = SecretStr("")
    index_timeout_seconds: int = Field(default=30, ge=1, le=60)

    @field_validator("cors_origins")
    @classmethod
    def validate_origins(cls, values: list[str]) -> list[str]:
        """Uma origem explícita evita conceder acesso CORS a sites arbitrários."""
        from urllib.parse import urlsplit
        for value in values:
            parsed = urlsplit(value)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc or "*" in value or parsed.path or parsed.query or parsed.fragment:
                raise ValueError("CORS exige origens HTTP/HTTPS explícitas, sem caminho.")
        return values

    @model_validator(mode="after")
    def require_gateway(self) -> Settings:
        """Publicação depende do gateway autenticado; não há login paralelo na UI."""
        if self.environment != "local" and len(self.gateway_token.get_secret_value()) < 32:
            raise ValueError("Defina GATEWAY_TOKEN com ao menos 32 caracteres no backend e no gateway autenticado.")
        return self


def load_settings() -> Settings:
    """Prioridade: ambiente > .env > JSON > padrões; segredos corporativos não são persistidos."""
    env_path = Path(os.environ.get("APP_ENV_FILE", ROOT / ".env"))
    if "APP_ENV_FILE" in os.environ and not env_path.is_file():
        raise ValueError("APP_ENV_FILE aponta para um arquivo inexistente.")
    file_values = Config(env_path if env_path.is_file() else None, environ={}, encoding="utf-8-sig").file_values
    variables = {**file_values, **os.environ}
    path = Path(variables.get("APP_CONFIG_PATH", ROOT / "config/app.settings.json"))
    if "APP_CONFIG_PATH" in variables and not path.is_file():
        raise ValueError("APP_CONFIG_PATH aponta para um arquivo inexistente.")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
    except (OSError, ValueError):
        raise ValueError("Não foi possível ler o JSON de configuração do backend.") from None
    if not isinstance(data, dict):
        raise ValueError("A configuração do backend deve ser um objeto JSON.")
    mapping = {
        "APP_ENV": "environment",
        "APP_DATA_DIR": "data_dir",
        "BRADESCO_IAGEN_AMBIENTE": "bradesco_environment",
        "BRADESCO_IDENTIFICADOR": "bradesco_identificador",
        "BRADESCO_SENHA": "bradesco_senha",
        "BRADESCO_AUTHORIZATION_TOKEN": "bradesco_authorization_token",
        "BRADESCO_CA_BUNDLE": "bradesco_ca_bundle",
        "BRADESCO_TIMEOUT_SECONDS": "bradesco_timeout_seconds",
        "BRADESCO_TEXT_MODEL": "bradesco_text_model",
        "BRADESCO_TEXT_REASONING_EFFORT": "bradesco_text_reasoning_effort",
        "BRADESCO_TEXT_VERBOSITY": "bradesco_text_verbosity",
        "BRADESCO_TEXT_TEMPERATURE": "bradesco_text_temperature",
        "BRADESCO_TEXT_MAX_TOKENS": "bradesco_text_max_tokens",
        "BRADESCO_PROMPT_MAX_CHARS": "bradesco_prompt_max_chars",
        "GATEWAY_TOKEN": "gateway_token",
    }
    # O ambiente tem precedência mesmo quando usa o nome alternativo da chave.
    for layer in (file_values, os.environ):
        for variable, field in mapping.items():
            if variable in layer:
                value = layer[variable].strip()
                data[field] = (value or None) if field == "bradesco_ca_bundle" else value
        if "CORS_ORIGINS" in layer:
            data["cors_origins"] = [item.strip() for item in layer["CORS_ORIGINS"].split(",")]
    try:
        return Settings.model_validate(data)
    except ValidationError as error:
        fields = ", ".join(".".join(map(str, item["loc"])) or "configuração" for item in error.errors(include_input=False))
        raise ValueError(f"Configuração inválida no backend. Revise: {fields}.") from None
