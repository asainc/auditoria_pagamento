"""Normalização determinística da saída do text_generator antes de qualquer reparo por IA."""
from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from pydantic import ValidationError

from backend.services.extraction_wire import WireExtractionFragment


class StructuredOutputError(ValueError):
    """Falha estrutural sem ecoar conteúdo documental."""


class StructuredOutputParser:
    """Aceita variações estruturais seguras e valida o contrato canônico."""

    WRAPPERS = ("result", "resultado", "response", "output", "data")
    TOP_ALIASES = {
        "fields": "campos",
        "evidencias": "campos",
        "evidence": "campos",
        "installments": "parcelas",
        "parcelas_extraidas": "parcelas",
        "warnings": "alertas",
        "avisos": "alertas",
    }
    FIELD_ALIASES = {
        "field": "campo",
        "path": "campo",
        "value": "valor",
        "document": "documento",
        "file": "documento",
        "page": "pagina",
        "quote": "trecho",
        "excerpt": "trecho",
        "scope": "escopo",
        "nature": "natureza",
        "effect": "efeito",
    }
    INSTALLMENT_ALIASES = {
        "date": "data",
        "value": "valor_singelo",
        "valor": "valor_singelo",
        "description": "descricao",
        "damage_type": "verba_tipo",
        "type": "verba_tipo",
        "multiplier": "multiplicador",
    }

    @staticmethod
    def _decode(text: str) -> dict[str, Any]:
        value = text.strip()
        fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", value, re.IGNORECASE | re.DOTALL)
        if fenced:
            value = fenced.group(1).strip()
        decoded = json.loads(value)
        if not isinstance(decoded, dict):
            raise StructuredOutputError("A saída estruturada deve ser um objeto JSON.")
        return decoded

    @classmethod
    def _unwrap(cls, decoded: dict[str, Any]) -> dict[str, Any]:
        expected = {"campos", "parcelas", "alertas", *cls.TOP_ALIASES.keys()}
        if expected.intersection(decoded):
            return decoded
        for key in cls.WRAPPERS:
            nested = decoded.get(key)
            if isinstance(nested, dict):
                return nested
            if isinstance(nested, str):
                try:
                    candidate = cls._decode(nested)
                except (ValueError, json.JSONDecodeError):
                    continue
                return candidate
        return decoded

    @staticmethod
    def _rename(source: dict[str, Any], aliases: dict[str, str]) -> dict[str, Any]:
        result = dict(source)
        for alias, canonical in aliases.items():
            if canonical not in result and alias in result:
                result[canonical] = result.pop(alias)
        return result

    @classmethod
    def normalize(cls, decoded: dict[str, Any]) -> dict[str, Any]:
        normalized = cls._rename(deepcopy(cls._unwrap(decoded)), cls.TOP_ALIASES)
        for key in ("campos", "parcelas", "alertas"):
            normalized.setdefault(key, [])
        if isinstance(normalized["campos"], dict):
            normalized["campos"] = [normalized["campos"]]
        if isinstance(normalized["parcelas"], dict):
            normalized["parcelas"] = [normalized["parcelas"]]
        if normalized["alertas"] is None:
            normalized["alertas"] = []
        fields: list[dict[str, Any]] = []
        for item in normalized.get("campos", []):
            if not isinstance(item, dict):
                fields.append(item)
                continue
            row = cls._rename(item, cls.FIELD_ALIASES)
            row.setdefault("natureza", "indeterminado")
            row.setdefault("efeito", "informa")
            fields.append(row)
        installments: list[dict[str, Any]] = []
        for item in normalized.get("parcelas", []):
            if not isinstance(item, dict):
                installments.append(item)
                continue
            row = cls._rename(item, cls.INSTALLMENT_ALIASES)
            row.setdefault("descricao", "")
            row.setdefault("multiplicador", None)
            installments.append(row)
        normalized["campos"] = fields
        normalized["parcelas"] = installments
        return normalized

    def parse(self, text: str) -> WireExtractionFragment:
        decoded = self._decode(text)
        return WireExtractionFragment.model_validate(self.normalize(decoded))

    @staticmethod
    def validation_summary(exc: ValidationError) -> str:
        rows: list[str] = []
        for error in exc.errors(include_input=False, include_url=False):
            location = ".".join(str(item) for item in error.get("loc", ())) or "raiz"
            rows.append(f"- {location}: {error.get('msg', error.get('type', 'inválido'))}")
        return "\n".join(rows[:30])
