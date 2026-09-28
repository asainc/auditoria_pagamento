"""Sessão HTTP compartilhada pelas consultas públicas do motor.

A sessão reaproveita conexões de rede entre chamadas. Nenhuma credencial é
armazenada neste módulo.
"""
from __future__ import annotations

import requests

HTTP = requests.Session()
