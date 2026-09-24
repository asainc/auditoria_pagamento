"""Estado local, backup, restauração, cache e exclusão mútua do atualizador."""
from __future__ import annotations
from datetime import date, datetime
import json
import os
from pathlib import Path
import shutil
import time
from typing import Any
from judicial_calc.data_sources.local_excel import (
    DIARIA_12_6_XLSX, DIARIA_SELIC_IPCAE_XLSX, MENSAL_XLSX, _resource_path,
    load_daily_rate_table, load_index_series, load_monthly_indices, load_taxa_legal_mensal_percentual,
)
from .models import BACKUP_DIRNAME, LOCK_FILENAME, PLANILHAS_OBRIGATORIAS, STATE_FILENAME, DrCalcUpdateError, DrCalcUpdateResult

def _today_str() -> str:
    """Retorna a data corrente em formato ISO para gravação do estado do atualizador."""
    return date.today().isoformat()


def _data_dir(path: str | Path | None = None) -> Path:
    """Resolve a pasta que contém as planilhas locais de índices."""
    if path is not None:
        return Path(path)
    return _resource_path(MENSAL_XLSX).parent


def _state_path(data_dir: Path) -> Path:
    """Resolve o arquivo JSON usado para persistir o estado do atualizador."""
    return data_dir / STATE_FILENAME


def _lock_path(data_dir: Path) -> Path:
    """Resolve o arquivo de lock que impede duas atualizações simultâneas."""
    return data_dir / LOCK_FILENAME


def _load_state(data_dir: Path) -> dict[str, Any]:
    """Lê o estado persistido do atualizador e retorna uma estrutura vazia quando não existe estado válido."""
    path = _state_path(data_dir)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_state(data_dir: Path, result: DrCalcUpdateResult) -> None:
    """Persiste o estado da atualização preservando o último sucesso.

    Quando uma tentativa falha, não apagamos ``last_success_date``. Isso evita
    a mensagem enganosa "sem sucesso registrado" depois de uma falha pontual de
    rede ou de indisponibilidade do DrCalc, desde que já tenha havido uma
    atualização válida anteriormente.
    """
    previous = _load_state(data_dir)
    previous_success = previous.get("last_success_date")
    previous_success_at = previous.get("last_success_at")
    payload = {
        "last_success_date": result.date if result.success else previous_success,
        "last_success_at": datetime.now().isoformat(timespec="seconds") if result.success else previous_success_at,
        "last_attempt_at": datetime.now().isoformat(timespec="seconds"),
        "result": result.to_dict(),
    }
    _state_path(data_dir).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _already_updated_today(data_dir: Path) -> bool:
    """Verifica se já existe atualização bem-sucedida registrada para a data corrente."""
    state = _load_state(data_dir)
    if state.get("last_success_date") != _today_str():
        return False
    # O marcador só vale quando os três arquivos esperados existem.
    return all((data_dir / filename).exists() for filename in PLANILHAS_OBRIGATORIAS)

def _backup_planilhas(data_dir: Path) -> Path:
    """Cria cópia de segurança das planilhas antes de substituí-las."""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = data_dir / BACKUP_DIRNAME / stamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    for filename in PLANILHAS_OBRIGATORIAS:
        src = data_dir / filename
        if src.exists():
            shutil.copy2(src, backup_dir / filename)
    return backup_dir


def _atomic_replace(src: Path, dst: Path) -> None:
    """Substitui um arquivo de destino de forma atômica após gravação temporária."""
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    if tmp.exists():
        tmp.unlink()
    shutil.copy2(src, tmp)
    os.replace(tmp, dst)

def list_drcalc_backups(data_dir: str | Path | None = None) -> list[dict[str, Any]]:
    """Lista backups locais das planilhas de índices."""
    base = _data_dir(data_dir) / BACKUP_DIRNAME
    if not base.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted((p for p in base.iterdir() if p.is_dir()), reverse=True):
        files = [filename for filename in PLANILHAS_OBRIGATORIAS if (path / filename).exists()]
        rows.append(
            {
                "backup_id": path.name,
                "created_at": path.name,
                "path": str(path),
                "arquivos": ", ".join(files),
                "completo": len(files) == len(PLANILHAS_OBRIGATORIAS),
            }
        )
    return rows


def restaurar_backup_drcalc(
    backup_id_or_path: str,
    *,
    data_dir: str | Path | None = None,
) -> DrCalcUpdateResult:
    """Restaura as planilhas a partir de um backup criado pelo atualizador.

    Antes da restauração, cria um novo backup do estado atual, permitindo
    desfazer a restauração caso necessário.
    """
    target_dir = _data_dir(data_dir)
    candidate = Path(backup_id_or_path)
    if not candidate.exists():
        candidate = target_dir / BACKUP_DIRNAME / str(backup_id_or_path)
    if not candidate.exists() or not candidate.is_dir():
        raise DrCalcUpdateError(f"Backup não encontrado: {backup_id_or_path}")
    missing = [filename for filename in PLANILHAS_OBRIGATORIAS if not (candidate / filename).exists()]
    if missing:
        raise DrCalcUpdateError("Backup incompleto. Arquivos ausentes: " + ", ".join(missing))

    safety_backup = _backup_planilhas(target_dir)
    for filename in PLANILHAS_OBRIGATORIAS:
        _atomic_replace(candidate / filename, target_dir / filename)
    _clear_local_caches()
    result = DrCalcUpdateResult(
        executed=True,
        skipped=False,
        success=True,
        date=_today_str(),
        message="Backup de índices restaurado com sucesso.",
        backup_dir=str(safety_backup),
        updated_files=list(PLANILHAS_OBRIGATORIAS),
        restored_backup=str(candidate),
        consistency_checks=[{"checagem": "Backup completo", "status": "ok", "detalhe": str(candidate)}],
    )
    _write_state(target_dir, result)
    return result


def _clear_local_caches() -> None:
    """Limpa caches de leitura de índices para que os próximos cálculos usem os arquivos atuais."""
    from judicial_calc.data_sources.local_excel import local_index_coverage

    for func in (load_monthly_indices, load_index_series, local_index_coverage, load_daily_rate_table):
        try:
            func.cache_clear()  # type: ignore[attr-defined]
        except Exception:
            pass
    try:
        load_taxa_legal_mensal_percentual.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass
    try:
        from judicial_calc.indices.local_excel import _default_series_map

        _default_series_map.cache_clear()
    except Exception:
        pass
    try:
        from judicial_calc.indices.registry import create_default_index_registry

        create_default_index_registry.cache_clear()
    except Exception:
        pass


def _acquire_lock(data_dir: Path, wait_seconds: int = 20) -> bool:
    """Adquire o lock de atualização e retorna o recurso usado para liberação posterior."""
    lock = _lock_path(data_dir)
    start = time.time()
    while True:
        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(datetime.now().isoformat())
            return True
        except FileExistsError:
            # Remove lock velho com mais de 10 minutos.
            try:
                if time.time() - lock.stat().st_mtime > 600:
                    lock.unlink(missing_ok=True)
                    continue
            except Exception:
                pass
            if time.time() - start > wait_seconds:
                return False
            time.sleep(0.5)


def _release_lock(data_dir: Path) -> None:
    """Libera o lock de atualização adquirido pelo processo."""
    try:
        _lock_path(data_dir).unlink(missing_ok=True)
    except Exception:
        pass
