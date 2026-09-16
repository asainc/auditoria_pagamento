"""Gera o manifesto SHA-256 dos arquivos Python do motor determinístico."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src"
TARGET = ROOT / "docs" / "motor_sha256.json"


def engine_manifest() -> dict[str, str]:
    """Retorna hashes ordenados dos fontes Python que compõem o pacote do motor."""
    return {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(SOURCE.rglob("*.py"))
        if "__pycache__" not in path.parts
    }


def main() -> int:
    """Persiste o manifesto em JSON estável para validação de integridade."""
    TARGET.write_text(json.dumps(engine_manifest(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Manifesto gerado: {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
