"""Fachada de compatibilidade para contratos do domínio de cálculo.

Novos módulos podem importar diretamente de ``calculation_input``,
``calculation_output``, ``calculation_parameters`` ou ``calculation_history``.
"""
from backend.contracts.calculation_parameters import *  # noqa: F401,F403
from backend.contracts.calculation_input import *  # noqa: F401,F403
from backend.contracts.calculation_output import *  # noqa: F401,F403
from backend.contracts.calculation_history import *  # noqa: F401,F403
