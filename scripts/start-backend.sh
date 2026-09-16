#!/usr/bin/env bash
# Inicia somente a API; depende da instalação descrita no README.
set -euo pipefail
cd "$(dirname "$0")/.."
exec .venv/bin/python -m uvicorn backend.principal:aplicacao --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
