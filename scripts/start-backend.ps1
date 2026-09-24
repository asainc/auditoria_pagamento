# Inicia somente a API. Funciona com Python corporativo global ou .venv, quando permitido.
$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $Root

# Prioridade: BACKEND_PYTHON explícito > .venv existente > Python disponível no PATH.
if ($env:BACKEND_PYTHON) {
    $Python = $env:BACKEND_PYTHON
} elseif (Test-Path (Join-Path $Root '.venv\Scripts\python.exe')) {
    $Python = Join-Path $Root '.venv\Scripts\python.exe'
} else {
    $Python = 'python'
}

# O layout src/ precisa estar visível mesmo quando a política corporativa impede instalação editável/venv.
$env:PYTHONPATH = "$Root\src;$Root"

& $Python -m uvicorn backend.principal:aplicacao --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
exit $LASTEXITCODE
