"""Atualizador DrCalc dividido por responsabilidade."""
from .models import DrCalcRecord, DrCalcSeries, DrCalcUpdateResult, DrCalcUpdateError
from .client import DrCalcClient
from .service import baixar_series_drcalc, atualizar_planilhas_drcalc, atualizar_planilhas_drcalc_se_necessario
from .lifecycle import list_drcalc_backups, restaurar_backup_drcalc
