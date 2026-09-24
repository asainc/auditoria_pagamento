"""Tipos internos da extração; separados da orquestração para evitar acoplamento."""
from __future__ import annotations

from backend.models import AiUsage, Contract, FieldEvidence, Installment


class ExtractionFragment(Contract):
    """Fragmento especializado já validado pelo contrato interno."""

    campos: list[FieldEvidence]
    parcelas: list[Installment]
    alertas: list[str]


class ProviderResult(Contract):
    """Fragmento estruturado e telemetria observável das chamadas corporativas."""

    fragmento: ExtractionFragment
    usos: list[AiUsage]
