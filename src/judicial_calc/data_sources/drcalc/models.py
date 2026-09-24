"""Tipos e constantes compartilhados pela integração DrCalc."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any
from judicial_calc.data_sources.local_excel import DIARIA_12_6_XLSX, DIARIA_SELIC_IPCAE_XLSX, MENSAL_XLSX

DRCALC_BASE_URL = "https://drcalc.net/consultaindices.asp?categoria=1&it=1&ml=Series"
DRCALC_HISTORY_START_YEAR = 2000
DRCALC_CATEGORIES: dict[str, int] = {
    "Índices de Preços e Custos": 1,
    "Índices do Mercado Financeiro": 2,
    "Índices de Cálculos Judiciais": 4,
}
DRCALC_CATEGORY_MATCHERS: dict[str, tuple[str, ...]] = {
    "Índices de Preços e Custos": ("indices de precos e custos", "precos e custos"),
    "Índices do Mercado Financeiro": ("indices do mercado financeiro", "mercado financeiro"),
    "Índices de Cálculos Judiciais": ("indices de calculos judiciais", "calculos judiciais"),
}
PLANILHAS_OBRIGATORIAS = (MENSAL_XLSX, DIARIA_SELIC_IPCAE_XLSX, DIARIA_12_6_XLSX)
STATE_FILENAME = ".drcalc_update_state.json"
LOCK_FILENAME = ".drcalc_update.lock"
BACKUP_DIRNAME = "backups_indices"

@dataclass(frozen=True)
class DrCalcRecord:
    """Uma observação extraída de uma série do DrCalc."""

    periodo: date | str
    valor: Decimal


@dataclass
class DrCalcSeries:
    """Série histórica extraída de uma página do DrCalc."""

    name: str
    url: str
    category: str
    records: list[DrCalcRecord]
    periodicity: str  # "mensal" ou "diaria"
    raw_columns: list[str] = field(default_factory=list)
    metric: str = "unknown"  # "rate_percent", "index_value" ou "unknown"


@dataclass
class DrCalcUpdateResult:
    """Resultado auditável da tentativa de atualização."""

    executed: bool
    skipped: bool
    success: bool
    date: str
    message: str
    backup_dir: str | None = None
    updated_files: list[str] = field(default_factory=list)
    updated_series: list[str] = field(default_factory=list)
    preserved_columns: list[str] = field(default_factory=list)
    source_url: str = DRCALC_BASE_URL
    categories: list[str] = field(default_factory=lambda: list(DRCALC_CATEGORIES.keys()))
    row_counts: dict[str, int] = field(default_factory=dict)
    previous_row_counts: dict[str, int] = field(default_factory=dict)
    diff_summary: list[dict[str, Any]] = field(default_factory=list)
    consistency_checks: list[dict[str, Any]] = field(default_factory=list)
    has_new_competence: bool = False
    new_competencies: list[dict[str, str]] = field(default_factory=list)
    restored_backup: str | None = None
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serializa o resultado da atualização do DrCalc para um dicionário simples e auditável."""
        return asdict(self)


class DrCalcUpdateError(RuntimeError):
    """Falha controlada da atualização das planilhas locais."""
