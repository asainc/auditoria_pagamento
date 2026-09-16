from __future__ import annotations

from judicial_calc.core.types import ResultadoCalculo
from judicial_calc.data_sources.local_excel import available_indices, missing_indices
from judicial_calc.io.excel import salvar_resultado_excel
from judicial_calc.io.pdf import salvar_resultado_pdf, salvar_resultado_pdf_auditavel
from judicial_calc.services.calculation_service import calcular_debitos
from judicial_calc.data_sources.drcalc_updater import atualizar_planilhas_drcalc, atualizar_planilhas_drcalc_se_necessario, list_drcalc_backups, restaurar_backup_drcalc

__all__ = [
    "ResultadoCalculo",
    "available_indices",
    "missing_indices",
    "calcular_debitos",
    "salvar_resultado_excel",
    "salvar_resultado_pdf",
    "salvar_resultado_pdf_auditavel",
    "atualizar_planilhas_drcalc",
    "atualizar_planilhas_drcalc_se_necessario",
    "list_drcalc_backups",
    "restaurar_backup_drcalc",
]
