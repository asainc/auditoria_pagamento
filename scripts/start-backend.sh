#!/usr/bin/env bash
# Inicia somente a API com Python global ou .venv, quando disponível.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -n "${BACKEND_PYTHON:-}" ]]; then
  PYTHON_CMD="$BACKEND_PYTHON"
elif [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON_CMD="$ROOT/.venv/bin/python"
else
  PYTHON_CMD="python"
fi

export PYTHONPATH="$ROOT/src:$ROOT${PYTHONPATH:+:$PYTHONPATH}"
exec "$PYTHON_CMD" -m uvicorn backend.principal:aplicacao --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
