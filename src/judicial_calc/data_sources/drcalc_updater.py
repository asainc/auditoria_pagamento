"""Fachada retrocompatível do atualizador de índices.

A implementação foi dividida em ``drcalc.client``, ``drcalc.workbook``,
``drcalc.lifecycle`` e ``drcalc.service``. Imports antigos continuam válidos.
"""
from judicial_calc.data_sources.drcalc.models import *  # noqa: F401,F403
from judicial_calc.data_sources.drcalc.parsing import *  # noqa: F401,F403
from judicial_calc.data_sources.drcalc.client import *  # noqa: F401,F403
from judicial_calc.data_sources.drcalc.workbook import *  # noqa: F401,F403
from judicial_calc.data_sources.drcalc.lifecycle import *  # noqa: F401,F403
from judicial_calc.data_sources.drcalc.service import *  # noqa: F401,F403

# Compatibilidade explícita para helpers privados historicamente usados em testes/integradores.
from judicial_calc.data_sources.drcalc.parsing import _build_category_url
from judicial_calc.data_sources.drcalc.workbook import _convert_daily_value, _convert_monthly_value
