"""Catálogo e padrões centrais do cálculo.

Este módulo é deliberadamente independente dos modelos Pydantic e dos serviços HTTP.
Ele pode ser importado pela validação dos contratos, pela política operacional, pela
tradução de erros e pelos geradores do frontend sem criar dependências circulares.

A fonte única é ``config/calculation_policy.json``. Alterações de rótulo, metadados
visuais ou valores padrão devem ser feitas nesse arquivo e depois refletidas nos
artefatos gerados do frontend/documentação.
"""
from __future__ import annotations

import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[1]
CalculationOrigin = Literal["manual", "processo"]


class CalculationPolicyConfigurationError(RuntimeError):
    """Indica erro estrutural na política versionada da aplicação."""


@lru_cache(maxsize=1)
def load_calculation_policy() -> dict[str, Any]:
    """Carrega e valida a estrutura mínima da política de cálculo.

    O caminho pode ser substituído por ``CALCULATION_POLICY_PATH`` em ambientes de
    validação controlada. O arquivo não contém segredos e deve ser versionado junto
    ao código para garantir reprodutibilidade.
    """
    path = Path(os.environ.get("CALCULATION_POLICY_PATH", ROOT / "config/calculation_policy.json"))
    if not path.is_file():
        raise CalculationPolicyConfigurationError(f"Política de cálculo não encontrada: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise CalculationPolicyConfigurationError("Não foi possível ler a política de cálculo.") from exc
    if not isinstance(data, dict):
        raise CalculationPolicyConfigurationError("A política de cálculo deve ser um objeto JSON.")
    if set(data.get("origins", {})) != {"manual", "processo"}:
        raise CalculationPolicyConfigurationError("A política deve definir as origens manual e processo.")
    fields = data.get("fields")
    if not isinstance(fields, list) or not fields:
        raise CalculationPolicyConfigurationError("A política deve conter o catálogo de parâmetros.")
    keys = [field.get("key") for field in fields if isinstance(field, dict)]
    if len(keys) != len(fields) or any(not isinstance(key, str) or not key for key in keys) or len(set(keys)) != len(keys):
        raise CalculationPolicyConfigurationError("O catálogo de parâmetros possui chave ausente ou duplicada.")
    required = data.get("required_parameter_keys")
    if not isinstance(required, list) or any(key not in keys for key in required):
        raise CalculationPolicyConfigurationError("required_parameter_keys contém campo inexistente.")
    for origin in ("manual", "processo"):
        defaults = data["origins"][origin].get("defaults", {})
        if not isinstance(defaults, dict) or any(key not in keys for key in defaults):
            raise CalculationPolicyConfigurationError(f"Padrões inválidos para a origem {origin}.")
    return data


def parameter_catalog() -> list[dict[str, Any]]:
    """Retorna cópia rasa do catálogo central de parâmetros."""
    return [dict(item) for item in load_calculation_policy()["fields"]]


def parameter_keys() -> tuple[str, ...]:
    """Retorna as chaves na ordem usada pela interface e pela documentação."""
    return tuple(item["key"] for item in load_calculation_policy()["fields"])


def required_parameter_keys() -> tuple[str, ...]:
    """Retorna os campos mínimos necessários para disparar o motor."""
    return tuple(load_calculation_policy()["required_parameter_keys"])


def parameter_label(key: str) -> str:
    """Converte uma chave técnica no rótulo oficial da aplicação."""
    for item in load_calculation_policy()["fields"]:
        if item["key"] == key:
            return str(item["label"])
    return key


def defaults_for_origin(origin: CalculationOrigin) -> dict[str, Any]:
    """Retorna os valores padrão efetivos para a origem informada.

    A função sempre devolve uma nova cópia para evitar que um serviço altere o
    objeto cacheado e contamine requisições futuras.
    """
    if origin not in {"manual", "processo"}:
        raise ValueError(f"Origem de cálculo inválida: {origin}")
    return dict(load_calculation_policy()["origins"][origin]["defaults"])


def apply_missing_defaults(parameters: dict[str, Any], origin: CalculationOrigin) -> dict[str, Any]:
    """Completa somente campos ausentes; valores explícitos nunca são sobrescritos."""
    resolved = dict(parameters)
    for key, value in defaults_for_origin(origin).items():
        if key not in resolved or resolved[key] in (None, ""):
            resolved[key] = value
    return resolved


def policy_hash() -> str:
    """Retorna SHA-256 canônico da política efetivamente carregada.

    O hash permite vincular cada cálculo à versão dos defaults e do catálogo de
    parâmetros sem persistir o conteúdo completo da política no registro de auditoria.
    """
    payload = json.dumps(
        load_calculation_policy(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
