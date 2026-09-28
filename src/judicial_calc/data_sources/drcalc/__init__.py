"""Interface pública do atualizador de índices obtidos do DrCalc.

As classes e funções são implementadas em módulos menores por responsabilidade;
este arquivo define explicitamente o que pode ser importado pelo restante do
projeto sem conhecer essa organização interna.
"""
from .models import DrCalcRecord, DrCalcSeries, DrCalcUpdateResult, DrCalcUpdateError
from .client import DrCalcClient
from .service import baixar_series_drcalc, atualizar_planilhas_drcalc, atualizar_planilhas_drcalc_se_necessario
from .lifecycle import list_drcalc_backups, restaurar_backup_drcalc

__all__ = [
    "DrCalcRecord",
    "DrCalcSeries",
    "DrCalcUpdateResult",
    "DrCalcUpdateError",
    "DrCalcClient",
    "baixar_series_drcalc",
    "atualizar_planilhas_drcalc",
    "atualizar_planilhas_drcalc_se_necessario",
    "list_drcalc_backups",
    "restaurar_backup_drcalc",
]
