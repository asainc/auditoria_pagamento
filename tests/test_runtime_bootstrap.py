"""Valida que os iniciadores usam uma única configuração e não observam node_modules."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_runner_module():
    """Carrega o script como módulo sem precisar transformar ``scripts`` em pacote."""
    path = ROOT / "scripts" / "run_backend.py"
    spec = importlib.util.spec_from_file_location("run_backend_for_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_start_dev_uses_health_route_without_release_comparison() -> None:
    """O launcher verifica saúde real da API sem depender de texto de versão do release."""
    source = (ROOT / "scripts" / "start-dev.mjs").read_text(encoding="utf-8")
    assert "/api/v2/saude" in source
    assert "versao_api ===" not in source
    assert "startsWith('" not in source


def test_lock_pins_requests_transport_stack() -> None:
    """O lock mantém uma combinação reproduzível para o transporte HTTP no Windows."""
    lock = (ROOT / "requirements.lock").read_text(encoding="utf-8")
    assert "requests==2.34.2" in lock
    assert "urllib3==2.7.0" in lock
    assert "charset-normalizer==3.5.1" in lock
    assert "chardet==5.2.0" in lock


def test_start_scripts_delegate_to_single_runner() -> None:
    """Wrappers de sistema operacional não podem duplicar opções do Uvicorn."""
    expected = {
        "start-backend.ps1": "scripts/run_backend.py",
        "start-backend.cmd": "scripts\\run_backend.py",
        "start-backend.sh": "scripts/run_backend.py",
        "start-backend-dev.ps1": "scripts/run_backend.py --reload",
        "start-backend-dev.cmd": "scripts\\run_backend.py --reload",
        "start-backend-dev.sh": "scripts/run_backend.py --reload",
    }
    for filename, command in expected.items():
        source = (ROOT / "scripts" / filename).read_text(encoding="utf-8")
        assert command in source
        assert "-m uvicorn" not in source
        assert "--reload-dir" not in source


def test_reload_configuration_never_includes_frontend_or_node_modules() -> None:
    """A lista observada fica restrita ao backend e exclui explicitamente o frontend."""
    runtime = json.loads((ROOT / "config" / "runtime.json").read_text(encoding="utf-8"))
    directories = {value.replace("\\", "/") for value in runtime["reload"]["directories"]}
    excludes = {value.replace("\\", "/") for value in runtime["reload"]["exclude_paths"]}

    assert directories == {"backend", "src", "config", "prompts"}
    assert "frontend" not in directories
    assert "frontend/node_modules" not in directories
    assert "frontend" in excludes
    assert "frontend/node_modules" in excludes


def test_runner_passes_scoped_reload_options_to_uvicorn(monkeypatch) -> None:
    """Mesmo com reload ativo, o Uvicorn recebe somente caminhos controlados."""
    runner = _load_runner_module()
    calls = []

    monkeypatch.setattr(runner, "validate_python_environment", lambda: None)
    monkeypatch.setattr(runner.uvicorn, "run", lambda app, **options: calls.append((app, options)))

    runner.run_backend(reload_enabled=True)

    assert len(calls) == 1
    app, options = calls[0]
    assert app == "backend.principal:aplicacao"
    assert options["reload"] is True
    assert all("frontend" not in path.replace("\\", "/") for path in options["reload_dirs"])
    assert "frontend/node_modules" in {path.replace("\\", "/") for path in options["reload_excludes"]}
    assert {"*.py", "*.json", "*.md"}.issubset(set(options["reload_includes"]))



def test_start_dev_builds_proxy_from_runtime_backend_address() -> None:
    """A porta do backend pode mudar sem exigir edição manual do proxy Angular."""
    source = (ROOT / "scripts" / "start-dev.mjs").read_text(encoding="utf-8")
    assert "const runtimeProxyPath" in source
    assert "`http://${backendHost}:${backendPort}`" in source
    assert "'--proxy-config', runtimeProxyPath" in source
    assert "rmSync(runtimeProxyPath, { force: true })" in source


def test_reload_options_are_accepted_by_uvicorn_config(monkeypatch) -> None:
    """Garante que padrões de exclusão permaneçam relativos e aceitos pelo Uvicorn."""
    runner = _load_runner_module()
    settings = runner.load_runtime_settings()

    config = runner.uvicorn.Config(
        runner.BACKEND_APP,
        reload=True,
        reload_dirs=[str(path) for path in settings.reload_directories],
        reload_includes=list(settings.reload_include_patterns),
        reload_excludes=list(settings.reload_exclude_patterns),
    )

    observed = {path.as_posix() for path in config.reload_dirs}
    assert all("frontend" not in path for path in observed)
    assert "frontend/node_modules" in set(config.reload_excludes)

def test_readme_recommends_runner_instead_of_direct_uvicorn_reload() -> None:
    """A documentação não pode reintroduzir um watcher aberto na raiz do projeto."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "start-backend-dev.ps1" in readme
    assert "run_backend.py --reload" in readme
    assert "python -m uvicorn backend.principal:aplicacao --reload" not in readme
