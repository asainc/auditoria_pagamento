"""Orquestração de lotes reaproveita o cálculo unitário, sem duplicar o motor."""
from backend.errors import ServiceError
from backend.models import BatchItem, BatchRequest, BatchResponse
from backend.services.calculation import CalculationService


class BatchService:
    """Execução sequencial limita memória e mantém erros separados por processo."""
    def __init__(self, calculation: CalculationService):
        """Recebe dependências explicitamente para manter configuração e testes isolados."""
        self.calculation = calculation

    def execute(self, payload: BatchRequest) -> BatchResponse:
        """Preserva os sucessos e informa explicitamente cada falha de domínio."""
        results = []
        for process in payload.processos:
            try:
                results.append(BatchItem(numero_processo=process.numero_processo, resultado=self.calculation.execute(process)))
            except ServiceError as exc:
                results.append(BatchItem(numero_processo=process.numero_processo, erro=exc.message))
        return BatchResponse(resultados=results)
