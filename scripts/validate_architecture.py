"""Valida fronteiras arquiteturais, dependências proibidas e versões fixadas do frontend."""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PACKAGE = "streamlit"
IGNORED = {"node_modules", "dist", ".git", ".venv", ".angular", ".test-build", "__pycache__", ".pytest_cache"}


def architecture_errors(root: Path) -> list[str]:
    """Imports são analisados por AST, evitando falsos positivos em palavras como interest."""
    errors = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if any(part in IGNORED for part in relative.parts):
            continue
        if path.name in {".streamlit", "secrets.toml", "secrets.example.toml", "app_streamlit.py", "streamlit_app", "streamlit_ui"}:
            errors.append(f"Configuração/UI não permitida: {relative}")
        if not path.is_file():
            continue
        if path.suffix == ".py":
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = [item.name for item in node.names] if isinstance(node, ast.Import) else [node.module or ""] if isinstance(node, ast.ImportFrom) else []
                if any(name == FORBIDDEN_PACKAGE or name.startswith(FORBIDDEN_PACKAGE + ".") for name in names):
                    errors.append(f"Import proibido: {relative}:{node.lineno}")
                if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "st":
                    errors.append(f"API de UI não permitida: {relative}:{node.lineno}")
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"HTMLResponse", "Jinja2Templates"}:
                    errors.append(f"Interface Python: {relative}:{node.lineno}")
                if "routers" in relative.parts and any(name.startswith("judicial_calc") for name in names):
                    errors.append(f"Rota acessa motor diretamente: {relative}")
        if path.name in {"pyproject.toml", "requirements.txt", "requirements-dev.txt", "requirements.lock", "Dockerfile", "package.json", "package-lock.json"}:
            if FORBIDDEN_PACKAGE in path.read_text(encoding="utf-8").lower():
                errors.append(f"Dependência/configuração proibida: {relative}")
        if path.suffix == ".ts" and path.name.endswith("component.ts"):
            text = path.read_text(encoding="utf-8")
            if "HttpClient" in text or "fetch(" in text or "judicial_calc" in text:
                errors.append(f"Componente ultrapassa serviço HTTP: {relative}")
    manifest_path = root / "frontend/package.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        packages = {**manifest.get("dependencies", {}), **manifest.get("devDependencies", {})}
        for name, version in packages.items():
            if name.startswith(("@angular/", "@angular-devkit/")) and version != "21.2.21":
                errors.append(f"Angular fora da versão exigida: {name}={version}")
        lock = root / "frontend/package-lock.json"
        if lock.exists():
            for name, value in json.loads(lock.read_text())["packages"].items():
                if name.startswith("node_modules/@angular/") and value.get("version") != "21.2.21":
                    errors.append(f"Lock Angular divergente: {name}")
    return errors


if __name__ == "__main__":
    errors = architecture_errors(ROOT)
    if errors:
        raise SystemExit("\n".join(errors))
    print("Arquitetura aprovada: interface Angular 21.2.21, rotas sem motor direto e sem dependências de UI Python.")
