"""Orquestra cálculo, exportação e auditoria fora das rotas HTTP."""
from __future__ import annotations

import hashlib
import json
import logging
from time import perf_counter

from filelock import Timeout
from requests import RequestException

from backend.calculation_policy import policy_hash
from backend.errors import ServiceError
from backend.models import CalculationMetadata, CalculationRequest, CalculationResponse, SummaryEntry
from backend.repository import Repository
from backend.services.engine import EngineFacade, dataframe_table
from backend.services.engine_guidance import engine_error_guidance

logger = logging.getLogger("judicial")


class CalculationService:
    """Uma execução coerente usa a mesma versão de índices até o fim."""
    def __init__(self, repository: Repository, facade: EngineFacade):
        """Recebe dependências explicitamente para manter configuração e testes isolados."""
        self.repository = repository
        self.facade = facade

    def execute(self, payload: CalculationRequest, pdf: bool = False, audit: bool = False, expected_indices_hash: str | None = None) -> CalculationResponse | bytes:
        """Validação Pydantic antecede a fachada; falhas não expõem conteúdo sensível."""
        started = perf_counter()
        canonical_input = json.dumps(
            payload.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        input_hash = hashlib.sha256(canonical_input).hexdigest()
        current_policy_hash = policy_hash()
        try:
            with self.facade.lock:
                if expected_indices_hash and self.facade.index_hash() != expected_indices_hash:
                    raise ServiceError("Os índices mudaram desde o cálculo. Calcule novamente antes de exportar a memória.", 409)
                result = self.facade.calculate(payload)
                metadata = CalculationMetadata(
                    entrada_sha256=input_hash,
                    politica_sha256=current_policy_hash,
                    motor_sha256=self.facade.engine_hash,
                    indices_sha256=self.facade.index_hash(),
                    duracao_ms=round((perf_counter() - started) * 1000, 2),
                    revisao_humana_confirmada=True,
                )
                output = self.facade.pdf(result, audit) if pdf else CalculationResponse(origem_calculo=payload.origem_calculo, numero_processo=payload.numero_processo, memoria=dataframe_table(result.memoria), resumo=[SummaryEntry(campo=str(row["campo"]), valor=str(row["valor"])) for row in result.resumo.to_dict("records")], parametros=payload.parametros, metadata=metadata)
        except Timeout as exc:
            raise ServiceError("Índices em atualização. Aguarde e tente novamente.", 503) from exc
        except (RequestException, FileNotFoundError) as exc:
            raise ServiceError("Não foi possível obter a série de índices necessária. Confira a disponibilidade dos índices.", 503) from exc
        except (ValueError, KeyError, ArithmeticError) as exc:
            # A exceção do motor não é registrada integralmente para evitar ecoar valores de entrada nos logs.
            logger.warning("engine_validation", extra={"error_type": type(exc).__name__})
            raise ServiceError(engine_error_guidance(exc)) from exc
        self.repository.audit(
            "calculation_completed",
            {
                "origin": payload.origem_calculo,
                "input_hash": metadata.entrada_sha256,
                "policy_hash": metadata.politica_sha256,
                "engine_hash": metadata.motor_sha256,
                "indices_hash": metadata.indices_sha256,
                "rows": len(payload.parcelas),
                "duration_ms": metadata.duracao_ms,
                "human_review": True,
            },
        )
        return output
