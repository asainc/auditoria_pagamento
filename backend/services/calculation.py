"""Orquestra cálculo, versionamento, exportação e auditoria fora das rotas HTTP."""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from time import perf_counter

from filelock import Timeout
from requests import RequestException

from backend.calculation_policy import policy_hash
from backend.errors import ServiceError
from backend.domain.calculation_parameters import normalize_parameters
from backend.contracts.calculation import (
    CalculationMetadata,
    CalculationRequest,
    CalculationResponse,
    SummaryEntry,
    VersionedCalculationResponse,
)
from backend.repositories.audit_repository import AuditRepository
from backend.repositories.calculation_repository import CalculationRepository
from backend.services.engine import EngineFacade, dataframe_table
from backend.services.engine_guidance import engine_error_guidance

logger = logging.getLogger("judicial")


class CalculationService:
    """Uma execução coerente usa a mesma versão de índices até o fim."""
    def __init__(self, repository: CalculationRepository, audit_repository: AuditRepository, facade: EngineFacade):
        """Recebe dependências explicitamente para manter configuração e testes isolados."""
        self.repository = repository
        self.audit_repository = audit_repository
        self.facade = facade

    def execute(
        self,
        payload: CalculationRequest,
        pdf: bool = False,
        expected_indices_hash: str | None = None,
        *,
        calculation_id: str | None = None,
        base_version: int | None = None,
        expected_current_version: int | None = None,
        actor: str = "system",
        persist_version: bool = True,
    ) -> VersionedCalculationResponse | bytes:
        """Executa o motor e cadastra automaticamente a versão do cálculo.

        Tanto cálculos de processo quanto manuais são persistidos. Uma nova versão só
        nasce quando parâmetros ou parcelas formam um novo estado de negócio; retries
        sem alteração reutilizam a versão e recebem uma execução técnica própria.
        """
        started = perf_counter()
        # Converte a API plana para o domínio aninhado antes de calcular/hashar.
        normalized_parameters = normalize_parameters(payload.parametros)
        canonical_payload = payload.model_dump(mode="json")
        canonical_payload["parametros"] = normalized_parameters.contrato_flat
        canonical_input = json.dumps(
            canonical_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        input_hash = hashlib.sha256(canonical_input).hexdigest()
        current_policy_hash = policy_hash()
        archived_pdf: bytes | None = None
        try:
            with self.facade.lock:
                if expected_indices_hash and self.facade.index_hash() != expected_indices_hash:
                    raise ServiceError("Os índices mudaram desde o cálculo. Calcule novamente antes de exportar a memória.", 409, code="INDICES_CHANGED")
                result = self.facade.calculate(payload)
                metadata = CalculationMetadata(
                    entrada_sha256=input_hash,
                    politica_sha256=current_policy_hash,
                    motor_sha256=self.facade.engine_hash,
                    indices_sha256=self.facade.index_hash(),
                    duracao_ms=round((perf_counter() - started) * 1000, 2),
                    revisao_humana_confirmada=True,
                )
                if pdf:
                    output: CalculationResponse | bytes = self.facade.pdf(result)
                else:
                    output = CalculationResponse(
                        origem_calculo=payload.origem_calculo,
                        numero_processo=payload.numero_processo,
                        identificador_calculo=str(payload.identificador_calculo),
                        memoria=dataframe_table(result.memoria),
                        resumo=[SummaryEntry(campo=str(row["campo"]), valor=str(row["valor"])) for row in result.resumo.to_dict("records")],
                        parametros=payload.parametros,
                        metadata=metadata,
                    )
                    if persist_version:
                        # A memória PDF nasce do mesmo resultado e fica congelada na execução.
                        archived_pdf = self.facade.pdf(result)
        except Timeout as exc:
            raise ServiceError("Índices em atualização. Aguarde e tente novamente.", 503, code="INDICES_BUSY", retryable=True) from exc
        except (RequestException, FileNotFoundError) as exc:
            raise ServiceError("Não foi possível obter a série de índices necessária. Confira a disponibilidade dos índices.", 503, code="INDICES_UNAVAILABLE", retryable=True) from exc
        except (ModuleNotFoundError, ImportError) as exc:
            # Em estações corporativas sem virtualenv, uma instalação antiga do
            # motor no perfil do usuário não deve virar erro 500 sem diagnóstico.
            logger.error("engine_import_error", extra={"error_type": type(exc).__name__})
            raise ServiceError(
                "O motor local não foi carregado corretamente. Reinicie o backend a partir da raiz do projeto atualizado.",
                503,
            ) from exc
        except (ValueError, KeyError, ArithmeticError) as exc:
            # A exceção do motor não é registrada integralmente para evitar ecoar valores de entrada nos logs.
            logger.warning("engine_validation", extra={"error_type": type(exc).__name__})
            raise ServiceError(engine_error_guidance(exc)) from exc

        if pdf:
            return output

        response = output
        registration = None
        execution = None
        if persist_version:
            if payload.identificador_calculo is None or archived_pdf is None:
                raise ServiceError("Não foi possível preparar o cadastro versionado do cálculo.", 500)
            try:
                registration, execution = self.repository.append_version(
                    request=payload,
                    response=response,
                    pdf=archived_pdf,
                    actor=actor,
                    calculation_id=calculation_id,
                    base_version=base_version,
                    expected_current_version=expected_current_version,
                )
            except ValueError as exc:
                raise ServiceError(str(exc), 409, code="CALCULATION_VERSION_CONFLICT") from exc
            except sqlite3.DatabaseError as exc:
                logger.error("calculation_version_persistence_failed", extra={"error_type": type(exc).__name__})
                raise ServiceError(
                    "O cálculo foi processado, mas não foi possível cadastrar sua versão. Nenhuma versão parcial foi salva; tente novamente.",
                    503,
                ) from exc

            # Reexecuções do mesmo estado mantêm a versão de negócio, mas o resultado
            # atual continua sendo devolvido e ganha um execucao_id próprio. Isso evita
            # misturar versionamento funcional com variações técnicas de motor/índices.

        self.audit_repository.append(
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
                "versioned": registration is not None,
                "version": registration.versao if registration else 0,
                "new_version": registration.criada if registration else False,
                "execution_recorded": execution is not None,
            },
        )
        return VersionedCalculationResponse(**response.model_dump(), registro=registration, execucao=execution)
