"""Compatibilidade de imports legados.

Novos módulos devem importar de ``backend.contracts.<dominio>``. Este arquivo
permanece apenas para integrações e testes que ainda usam ``backend.models``.
"""
from backend.contracts import *  # noqa: F401,F403
