"""Contrato externo simples; limites financeiros continuam no contrato interno."""
from typing import Literal
from backend.models import Contract, DamageType, EvidenceEffect, EvidenceNature, FieldEvidence


class WireEvidence(FieldEvidence):
    """Mantém o schema externo simples e torna papel/efeito explicitamente obrigatórios."""
    pagina: int
    natureza: EvidenceNature
    efeito: EvidenceEffect


class WireInstallment(Contract):
    """Dinheiro como texto evita regex Decimal e conversão por ponto flutuante."""
    data: str
    valor_singelo: str
    descricao: str
    verba_tipo: DamageType


class WireFinancialEvent(Contract):
    """Todos os campos são obrigatórios no transporte, sem defaults no schema."""
    tipo: Literal["deposito_judicial", "pagamento_parcial", "compensacao", "levantamento"]
    data: str | None
    valor: str
    criterio: Literal["abater_na_data_do_pagamento", "descontar_no_final", "informativo"]
    indice_atualizacao: str | None
    aplicar_juros_apos_evento: bool


class WireExtractionFragment(Contract):
    """Somente tipos básicos e enums são enviados ao gerador estruturado."""
    campos: list[WireEvidence]
    parcelas: list[WireInstallment]
    eventos_financeiros: list[WireFinancialEvent]
    alertas: list[str]
