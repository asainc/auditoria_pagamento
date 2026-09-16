# Executar após instalar as dependências conforme README.
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
& '.\.venv\Scripts\python.exe' -m uvicorn backend.principal:aplicacao --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
exit $LASTEXITCODE
