"""Persistência e enriquecimento da trilha de revisão humana dos parâmetros."""
from __future__ import annotations

import sqlite3

from backend.errors import ServiceError
from backend.contracts.audit import ParameterChangeInput, ParameterChangeRecord
from backend.repositories.audit_repository import AuditRepository
from backend.repositories.extraction_repository import ExtractionRepository


class RevisionAuditService:
    """Registra eventos imutáveis sem depender do estado visual do Angular."""

    def __init__(self, repository: AuditRepository, extraction_repository: ExtractionRepository):
        """Recebe o repositório que persiste os eventos imutáveis de revisão."""
        self.repository = repository
        self.extraction_repository = extraction_repository

    def record(self, change: ParameterChangeInput, actor: str) -> ParameterChangeRecord:
        """Enriquece o evento com o valor/origem extraídos que o servidor conhece."""
        extracted_value = None
        extracted_source = None
        if change.origem_calculo == "processo" and change.numero_processo:
            result = self.extraction_repository.result(change.numero_processo)
            if result:
                key = change.campo
                path = f"parametros.{key}"
                decision = next((item for item in reversed(result.decisoes_cronologicas) if item.campo == path), None)
                chronology_defined = decision is not None
                if decision is not None:
                    extracted_value = decision.valor
                    extracted_source = (
                        f"{decision.documento} · página {decision.pagina} · sequência {decision.sequencia} "
                        f"· efeito {decision.efeito}"
                    )
                elif key in result.parametros_consolidados:
                    extracted_value = result.parametros_consolidados[key]
                if extracted_value is None and not chronology_defined:
                    adjustment = next((item for item in reversed(result.ajustes_operacionais) if item.campo == path), None)
                    if adjustment:
                        extracted_value = adjustment.valor
                        extracted_source = "Regra operacional · " + adjustment.motivo
                if extracted_value is None and not chronology_defined:
                    evidences = [item for item in result.campos if item.campo == path and item.escopo == "caso_concreto" and item.valor is not None]
                    values = {repr(item.valor) for item in evidences}
                    if len(values) == 1 and evidences:
                        extracted_value = evidences[-1].valor
                        extracted_source = f"{evidences[-1].documento} · página {evidences[-1].pagina}"
        try:
            return self.repository.add_parameter_change(
                change,
                actor=actor,
                extracted_value=extracted_value,
                extracted_source=extracted_source,
            )
        except sqlite3.DatabaseError as exc:
            # A revisão precisa ser persistida antes do cálculo, mas falhas do
            # SQLite devem chegar à interface como erro operacional acionável,
            # nunca como HTTP 500 genérico.
            raise ServiceError(
                "Não foi possível registrar a trilha de revisão. Reinicie o backend para aplicar a migração local e tente novamente.",
                503,
            ) from exc

    def list_for_process(self, process: str) -> list[ParameterChangeRecord]:
        """Retorna toda a trilha persistida do processo."""
        return self.repository.parameter_changes(process=process)

    def list_for_draft(self, draft: str) -> list[ParameterChangeRecord]:
        """Retorna a trilha do rascunho manual atual."""
        return self.repository.parameter_changes(draft=draft)
