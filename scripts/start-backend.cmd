@echo off
setlocal
REM Inicia somente a API sem exigir ambiente virtual.
cd /d "%~dp0\.."

set "PYTHONPATH=%CD%\src;%CD%"

if defined BACKEND_PYTHON (
    "%BACKEND_PYTHON%" -m uvicorn backend.principal:aplicacao --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
) else if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m uvicorn backend.principal:aplicacao --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
) else (
    python -m uvicorn backend.principal:aplicacao --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
)

exit /b %ERRORLEVEL%
