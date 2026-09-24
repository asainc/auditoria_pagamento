"""Gera interfaces TypeScript do OpenAPI; a API é a fonte única dos contratos."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from backend.principal import aplicacao

def type_name(schema: dict) -> str:
    """Converte somente estruturas publicadas pelo Pydantic/OpenAPI."""
    if "$ref" in schema:
        return schema["$ref"].rsplit("/", 1)[1].replace("-", "_")
    if "const" in schema:
        return json.dumps(schema["const"])
    if "enum" in schema:
        return " | ".join(json.dumps(value, ensure_ascii=False) for value in schema["enum"])
    for key in ("anyOf", "oneOf"):
        if key in schema:
            return " | ".join(type_name(value) for value in schema[key])
    kind = schema.get("type")
    if kind == "array":
        return f"Array<{type_name(schema['items'])}>"
    if kind == "object":
        if "properties" in schema:
            required = schema.get("required", [])
            return "{ " + "; ".join(f"{json.dumps(key)}{'' if key in required else '?'}: {type_name(value)}" for key, value in schema["properties"].items()) + " }"
        additional = schema.get("additionalProperties", {})
        return f"Record<string, {type_name(additional) if isinstance(additional, dict) else 'unknown'}>"
    return {"string": "string", "integer": "number", "number": "number", "boolean": "boolean", "null": "null"}.get(kind, "unknown")


def main() -> None:
    """Salva contrato e interfaces com ordenação estável para comparação em testes."""
    specification = aplicacao.openapi()
    (ROOT / "docs/openapi.json").write_text(json.dumps(specification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["/** Gerado de docs/openapi.json. Atualize por scripts/generate_contracts.py. */"]
    schemas = specification["components"]["schemas"]
    for name, schema in sorted(schemas.items()):
        lines.append(f"export type {name.replace('-', '_')} = {type_name(schema)};")
    # Quando o mesmo modelo Pydantic é usado como entrada e saída, o OpenAPI pode
    # gerar sufixos _Input/_Output. Mantemos o alias de entrada usado pelo Angular
    # para evitar espalhar uma mudança puramente geracional pelo código da UI.
    for name in sorted(schemas):
        if name.endswith("-Input"):
            base = name.removesuffix("-Input").replace("-", "_")
            if base not in {item.replace("-", "_") for item in schemas}:
                lines.append(f"export type {base} = {name.replace('-', '_')};")
    path = ROOT / "frontend/src/app/core/contracts.ts"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
