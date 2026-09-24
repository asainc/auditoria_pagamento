"""Orquestra download, staging, validação, promoção e fallback dos índices."""
from __future__ import annotations
import os
from pathlib import Path
import tempfile
import time
from .client import DrCalcClient
from .models import (
    DIARIA_12_6_XLSX, DIARIA_SELIC_IPCAE_XLSX, MENSAL_XLSX, PLANILHAS_OBRIGATORIAS, DrCalcSeries, DrCalcUpdateError, DrCalcUpdateResult,
)
from .lifecycle import (
    _acquire_lock, _already_updated_today, _atomic_replace, _backup_planilhas, _clear_local_caches, _data_dir, _load_state, _release_lock, _today_str, _write_state,
)
from .workbook import (
    _best_daily_series, _build_diff_row, _consistency_checks, _coverage_advancements, _daily_dataframe_from_workbook, _merge_daily, _merge_monthly,
    _monthly_dataframe_from_workbook, _validate_outputs, _write_daily_workbook, _write_monthly_workbook,
)

def baixar_series_drcalc(timeout: int = 30) -> list[DrCalcSeries]:
    """Baixa as séries disponíveis nas três categorias alvo do DrCalc.

    A fonte principal é o formulário oficial de ``Séries históricas``. O fluxo
    antigo, que tenta interpretar opções como URLs independentes, permanece
    apenas como fallback de compatibilidade com versões antigas do site.

    Falhas isoladas de uma série não interrompem a coleta inteira, mas as causas
    mais representativas são preservadas na exceção final para facilitar suporte
    quando nenhuma série puder ser confirmada.
    """
    client = DrCalcClient(timeout=timeout)
    series_list: list[DrCalcSeries] = []
    errors: list[str] = []

    try:
        series_list = client.fetch_historical_series()
    except Exception as exc:
        errors.append(f"consulta histórica: {type(exc).__name__}: {exc}")
    if series_list:
        return series_list

    # Fallback para estruturas antigas em que cada opção levava diretamente a
    # uma página de série. Não é mais o caminho preferencial.
    candidates = client.discover_series_urls()
    if not candidates:
        detail = "; ".join(errors[:3])
        suffix = f" Detalhes: {detail}" if detail else ""
        raise DrCalcUpdateError(
            "O DrCalc foi acessado, mas nenhum indexador foi localizado nas categorias configuradas."
            + suffix
        )
    for category, name, url in candidates:
        try:
            series = client.fetch_series(category, name, url)
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
            continue
        if series and series.records:
            series_list.append(series)
    if not series_list:
        detail = "; ".join(errors[:3])
        suffix = f" Causas observadas: {detail}" if detail else ""
        raise DrCalcUpdateError(f"Nenhuma série histórica válida foi extraída do DrCalc.{suffix}")
    return series_list


def atualizar_planilhas_drcalc(
    *,
    data_dir: str | Path | None = None,
    timeout: int = 30,
    series_list: list[DrCalcSeries] | None = None,
) -> DrCalcUpdateResult:
    """Força atualização das três planilhas locais a partir do DrCalc.

    Esta função sempre tenta baixar/mesclar/sobrescrever. Para executar apenas
    uma vez ao dia, use ``atualizar_planilhas_drcalc_se_necessario``.
    """
    target_dir = _data_dir(data_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    for filename in PLANILHAS_OBRIGATORIAS:
        if not (target_dir / filename).exists():
            raise DrCalcUpdateError(f"Planilha obrigatória não encontrada: {target_dir / filename}")

    try:
        # Captura a cobertura anterior antes de qualquer mesclagem. Essa foto é
        # usada para distinguir "fonte consultada" de "competência avançada".
        previous_monthly = _monthly_dataframe_from_workbook(target_dir / MENSAL_XLSX)
        previous_daily_selic = _daily_dataframe_from_workbook(target_dir / DIARIA_SELIC_IPCAE_XLSX)
        previous_daily_12_6 = _daily_dataframe_from_workbook(target_dir / DIARIA_12_6_XLSX)
        previous_row_counts = {
            MENSAL_XLSX: int(len(previous_monthly)),
            DIARIA_SELIC_IPCAE_XLSX: int(len(previous_daily_selic)),
            DIARIA_12_6_XLSX: int(len(previous_daily_12_6)),
        }
        series = series_list if series_list is not None else baixar_series_drcalc(timeout=timeout)
        monthly, updated_monthly, preserved = _merge_monthly(target_dir / MENSAL_XLSX, series)
        daily_selic_ipcae_series = _best_daily_series("selic_ipcae", series)
        daily_12_6_series = _best_daily_series("12_6", series)
        daily_selic_ipcae, updated_daily_1 = _merge_daily(
            target_dir / DIARIA_SELIC_IPCAE_XLSX,
            daily_selic_ipcae_series,
            "TAXA LEGAL DIARIA (SELIC-IPCAE)",
        )
        daily_12_6, updated_daily_2 = _merge_daily(
            target_dir / DIARIA_12_6_XLSX,
            daily_12_6_series,
            "TAXA LEGAL - 12% aa - 6% aa",
        )
        _validate_outputs(monthly, daily_selic_ipcae, daily_12_6)
        row_counts = {
            MENSAL_XLSX: int(len(monthly)),
            DIARIA_SELIC_IPCAE_XLSX: int(len(daily_selic_ipcae)),
            DIARIA_12_6_XLSX: int(len(daily_12_6)),
        }
        diff_summary = [
            _build_diff_row(MENSAL_XLSX, previous_row_counts.get(MENSAL_XLSX, 0), monthly),
            _build_diff_row(DIARIA_SELIC_IPCAE_XLSX, previous_row_counts.get(DIARIA_SELIC_IPCAE_XLSX, 0), daily_selic_ipcae),
            _build_diff_row(DIARIA_12_6_XLSX, previous_row_counts.get(DIARIA_12_6_XLSX, 0), daily_12_6),
        ]
        checks = _consistency_checks(monthly, daily_selic_ipcae, daily_12_6)
        new_competencies = _coverage_advancements(
            previous_monthly,
            monthly,
            previous_daily_selic,
            daily_selic_ipcae,
            previous_daily_12_6,
            daily_12_6,
        )
        has_new_competence = bool(new_competencies)
        checks.append(
            {
                "checagem": "Fonte trouxe competência posterior à instalada",
                "status": "ok" if has_new_competence else "sem_novidade",
                "detalhe": f"{len(new_competencies)} série(s) avançaram a competência máxima.",
            }
        )

        with tempfile.TemporaryDirectory(prefix="drcalc_update_") as tmp_name:
            tmp_dir = Path(tmp_name)
            monthly_path = tmp_dir / MENSAL_XLSX
            daily_1_path = tmp_dir / DIARIA_SELIC_IPCAE_XLSX
            daily_2_path = tmp_dir / DIARIA_12_6_XLSX
            _write_monthly_workbook(monthly, monthly_path)
            _write_daily_workbook(daily_selic_ipcae, daily_1_path)
            _write_daily_workbook(daily_12_6, daily_2_path)

            backup_dir = _backup_planilhas(target_dir)
            try:
                _atomic_replace(monthly_path, target_dir / MENSAL_XLSX)
                _atomic_replace(daily_1_path, target_dir / DIARIA_SELIC_IPCAE_XLSX)
                _atomic_replace(daily_2_path, target_dir / DIARIA_12_6_XLSX)
            except Exception as replace_exc:
                # Se uma substituição falhar no meio do conjunto, restaura todos
                # os arquivos do backup para não deixar versões misturadas.
                restore_errors: list[str] = []
                for filename in PLANILHAS_OBRIGATORIAS:
                    backup_file = backup_dir / filename
                    if not backup_file.exists():
                        continue
                    try:
                        _atomic_replace(backup_file, target_dir / filename)
                    except Exception as restore_exc:
                        restore_errors.append(f"{filename}: {type(restore_exc).__name__}")
                _clear_local_caches()
                if restore_errors:
                    raise DrCalcUpdateError(
                        "Falha ao substituir as planilhas e a restauração automática não foi integral. "
                        "Revise o backup criado antes de continuar."
                    ) from replace_exc
                raise DrCalcUpdateError(
                    "Falha ao substituir as planilhas; o backup anterior foi restaurado automaticamente."
                ) from replace_exc

        _clear_local_caches()
        message = (
            "Novas competências de índices foram incorporadas com sucesso a partir do DrCalc."
            if has_new_competence
            else "Verificação concluída: a fonte não trouxe competência posterior à já instalada. A cobertura máxima não foi avançada."
        )
        result = DrCalcUpdateResult(
            executed=True,
            skipped=False,
            success=True,
            date=_today_str(),
            message=message,
            backup_dir=str(backup_dir),
            updated_files=list(PLANILHAS_OBRIGATORIAS),
            updated_series=updated_monthly + updated_daily_1 + updated_daily_2,
            preserved_columns=preserved,
            previous_row_counts=previous_row_counts,
            row_counts=row_counts,
            diff_summary=diff_summary,
            consistency_checks=checks,
            has_new_competence=has_new_competence,
            new_competencies=new_competencies,
        )
        _write_state(target_dir, result)
        return result
    except Exception as exc:
        result = DrCalcUpdateResult(
            executed=True,
            skipped=False,
            success=False,
            date=_today_str(),
            message="Falha ao atualizar planilhas de índices; planilhas anteriores foram preservadas.",
            errors=[str(exc)],
        )
        _write_state(target_dir, result)
        if isinstance(exc, DrCalcUpdateError):
            raise
        raise DrCalcUpdateError(str(exc)) from exc


def atualizar_planilhas_drcalc_se_necessario(
    *,
    data_dir: str | Path | None = None,
    force: bool = False,
    timeout: int = 30,
    strict: bool = False,
) -> DrCalcUpdateResult:
    """Atualiza as planilhas apenas uma vez por dia.

    Use esta função no início do cálculo. Ela consulta o marcador diário em
    ``.drcalc_update_state.json``. Se já houve sucesso hoje, retorna rápido sem
    acessar a internet.

    Variáveis úteis:
    - ``JUDICIAL_CALC_DISABLE_RATE_UPDATE=1`` desativa a atualização;
    - ``JUDICIAL_CALC_DRCALC_TIMEOUT=15`` ajusta o timeout em segundos.
    """
    target_dir = _data_dir(data_dir)
    today = _today_str()

    if os.getenv("JUDICIAL_CALC_DISABLE_RATE_UPDATE", "0").strip().lower() in {"1", "true", "sim", "yes"}:
        return DrCalcUpdateResult(
            executed=False,
            skipped=True,
            success=True,
            date=today,
            message="Atualização automática das planilhas desativada por variável de ambiente.",
        )

    if not force and _already_updated_today(target_dir):
        state = _load_state(target_dir)
        return DrCalcUpdateResult(
            executed=False,
            skipped=True,
            success=True,
            date=today,
            message="Planilhas já foram atualizadas hoje; atualização ignorada.",
            backup_dir=(state.get("result") or {}).get("backup_dir"),
            updated_files=(state.get("result") or {}).get("updated_files", []),
            updated_series=(state.get("result") or {}).get("updated_series", []),
            preserved_columns=(state.get("result") or {}).get("preserved_columns", []),
            previous_row_counts=(state.get("result") or {}).get("previous_row_counts", {}),
            row_counts=(state.get("result") or {}).get("row_counts", {}),
            diff_summary=(state.get("result") or {}).get("diff_summary", []),
            consistency_checks=(state.get("result") or {}).get("consistency_checks", []),
            has_new_competence=bool((state.get("result") or {}).get("has_new_competence", False)),
            new_competencies=(state.get("result") or {}).get("new_competencies", []),
        )

    if not _acquire_lock(target_dir):
        # Outro processo pode estar atualizando. Evita corrida e permite seguir.
        time.sleep(1)
        if _already_updated_today(target_dir):
            return DrCalcUpdateResult(
                executed=False,
                skipped=True,
                success=True,
                date=today,
                message="Outra execução atualizou as planilhas hoje; atualização ignorada.",
            )
        msg = "Não foi possível obter lock para atualização das planilhas."
        if strict:
            raise DrCalcUpdateError(msg)
        return DrCalcUpdateResult(executed=False, skipped=True, success=False, date=today, message=msg, errors=[msg])

    try:
        try:
            effective_timeout = int(os.getenv("JUDICIAL_CALC_DRCALC_TIMEOUT", str(timeout)))
        except Exception:
            effective_timeout = timeout
        return atualizar_planilhas_drcalc(data_dir=target_dir, timeout=effective_timeout)
    except Exception as exc:
        if strict:
            raise
        result = DrCalcUpdateResult(
            executed=True,
            skipped=False,
            success=False,
            date=today,
            message="Falha ao atualizar planilhas; cálculo deve usar as planilhas locais existentes.",
            errors=[str(exc)],
        )
        # Garante registro coerente mesmo quando a exceção ocorreu antes do
        # ponto em que ``atualizar_planilhas_drcalc`` conseguiu gravar o estado.
        try:
            _write_state(target_dir, result)
        except Exception:
            pass
        return result
    finally:
        _release_lock(target_dir)
