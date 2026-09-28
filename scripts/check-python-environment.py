"""Valida o runtime Python antes de iniciar a API.

O objetivo é detectar ambiente global contaminado antes que ``requests`` emita
avisos pouco acionáveis ou que o backend seja executado com versões diferentes
do lock homologado do projeto.
"""
from __future__ import annotations

import importlib.metadata
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "requirements.lock"
CRITICAL = {
    "requests",
    "urllib3",
    "charset-normalizer",
    "chardet",
    "fastapi",
    "starlette",
    "uvicorn",
    "pydantic",
}


def locked_versions() -> dict[str, str]:
    """Lê somente pins exatos do lock para evitar inferências de versão."""
    result: dict[str, str] = {}
    for raw in LOCK.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([^\s;]+)", line)
        if match:
            result[match.group(1).lower().replace("_", "-")] = match.group(2)
    return result


def installed_version(package: str) -> str | None:
    """Retorna a versão instalada sem importar o pacote alvo."""
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def main() -> int:
    """Falha cedo quando o runtime diverge das dependências críticas homologadas."""
    expected = locked_versions()
    problems: list[str] = []

    if sys.version_info[:2] != (3, 12):
        problems.append(f"Python {sys.version.split()[0]} em uso; o projeto exige Python 3.12.x.")

    for package in sorted(CRITICAL):
        wanted = expected.get(package)
        if not wanted:
            continue
        found = installed_version(package)
        if found is None:
            problems.append(f"{package}: ausente (esperado {wanted}).")
        elif found != wanted:
            problems.append(f"{package}: instalado {found}; esperado {wanted}.")

    # Requests considera chardet >= 6 incompatível em linhas que ainda fazem essa checagem.
    chardet = installed_version("chardet")
    if chardet:
        try:
            major = int(chardet.split(".", 1)[0])
        except ValueError:
            major = 999
        if major >= 6:
            problems.append(
                f"chardet {chardet} é incompatível com o requests utilizado. "
                "Use o lock do projeto; não mantenha chardet >= 6 neste runtime."
            )

    if problems:
        print("ERRO: ambiente Python incompatível com o projeto.", file=sys.stderr)
        for item in problems:
            print(f"  - {item}", file=sys.stderr)
        print("", file=sys.stderr)
        print("Correção recomendada (ambiente isolado):", file=sys.stderr)
        print(r"  py -3.12 -m venv .venv", file=sys.stderr)
        print(r"  .venv\Scripts\python.exe -m pip install --upgrade pip", file=sys.stderr)
        print(r"  .venv\Scripts\python.exe -m pip install --upgrade --force-reinstall -r requirements.lock", file=sys.stderr)
        print(r"  .venv\Scripts\python.exe -m pip install --no-deps -e .", file=sys.stderr)
        return 2

    scope = "ambiente virtual" if sys.prefix != sys.base_prefix else "Python global"
    print(f"Dependências Python validadas ({scope}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
