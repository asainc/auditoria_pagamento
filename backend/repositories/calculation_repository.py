"""Persistência do agregado Cálculo → Versão → Execução → Artefato."""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from datetime import date, datetime, time as clock_time, timezone
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from backend.calculation_identity import display_process_number, normalize_manual_identifier, normalize_process_number
from backend.contracts.calculation import (
    CalculationComparison,
    CalculationDiff,
    CalculationExecutionRef,
    CalculationExecutionsPage,
    CalculationExecutionSummary,
    CalculationHistoryItem,
    CalculationHistoryPage,
    CalculationRequest,
    CalculationResponse,
    CalculationState,
    CalculationStateResult,
    CalculationVersionDetail,
    CalculationVersionRef,
    CalculationVersionSummary,
    CalculationVersionsPage,
)
from backend.persistence.schema import business_hash, full_diff, timestamp
from backend.persistence.sqlite import SQLiteDatabase


def _changed_fields(diff: CalculationDiff) -> list[str]:
    changed = [item.caminho for item in diff.campos]
    if diff.parcelas:
        changed.append("parcelas")
    return changed


def _record_identity(origin: str, identifier: str, process: str | None) -> tuple[str, str, str]:
    if origin == "processo":
        if not process:
            raise ValueError("Número do processo ausente para cadastro do cálculo.")
        normalized = normalize_process_number(process)
        display = display_process_number(process)
        return normalized, normalized, display
    normalized = normalize_manual_identifier(identifier)
    return f"manual:{normalized}", normalized, identifier.strip()


def _total_difference(before: str | None, after: str | None) -> str | None:
    if before is None or after is None:
        return None
    try:
        return str(Decimal(after) - Decimal(before))
    except (InvalidOperation, ValueError):
        return None


def _artifact_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class CalculationRepository:
    """Repositório transacional do ciclo de vida de cálculos versionados."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def append_version(
        self,
        *,
        request: CalculationRequest,
        response: CalculationResponse,
        pdf: bytes,
        actor: str,
        calculation_id: str | None = None,
        base_version: int | None = None,
        expected_current_version: int | None = None,
    ) -> tuple[CalculationVersionRef, CalculationExecutionRef]:
        """Cria versão somente para novo estado funcional e sempre registra execução."""
        moment = timestamp()
        request_payload = request.model_dump(mode="json")
        state_hash = business_hash(request_payload)
        total = next((item.valor for item in response.resumo if item.campo == "total_geral"), None)
        competence = f"{request.parametros.mes_atualizacao}/{request.parametros.ano_atualizacao}"
        identifier = str(request.identificador_calculo or "").strip()
        if not identifier:
            raise ValueError("O cálculo não possui identificador para cadastro no histórico.")
        record_key, normalized_identifier, display_identifier = _record_identity(request.origem_calculo, identifier, request.numero_processo)

        with self.database.immediate() as connection:
            record = connection.execute(
                "SELECT * FROM calculation_records WHERE origin=? AND normalized_identifier=? ORDER BY created_at LIMIT 1",
                (request.origem_calculo, normalized_identifier),
            ).fetchone()
            if calculation_id:
                requested = connection.execute("SELECT * FROM calculation_records WHERE id=?", (calculation_id,)).fetchone()
                if requested is None:
                    raise ValueError("O cálculo informado não existe mais no histórico.")
                if str(requested["origin"]) != request.origem_calculo or str(requested["normalized_identifier"] or "") != normalized_identifier:
                    raise ValueError("O cálculo informado não pertence ao identificador selecionado.")
                if record is not None and str(record["id"]) != calculation_id:
                    raise ValueError("Já existe outro cálculo cadastrado para este identificador.")
                record = requested

            if record is None:
                calculation_id = f"calc_{uuid4().hex}"
                connection.execute(
                    """
                    INSERT INTO calculation_records(
                        id,process,origin,identifier,normalized_identifier,state,state_changed_at,state_changed_by,
                        created_at,created_by,updated_at
                    ) VALUES(?,?,?,?,?,'ativo',NULL,NULL,?,?,?)
                    """,
                    (calculation_id, record_key, request.origem_calculo, display_identifier, normalized_identifier, moment, actor, moment),
                )
            else:
                calculation_id = str(record["id"])
                state = str(record["state"] or "ativo")
                if state != "ativo":
                    label = "arquivado" if state == "arquivado" else "cancelado"
                    raise ValueError(f"O cálculo está {label}. Reative-o no Histórico antes de gerar nova execução.")
                if str(record["identifier"] or "") != display_identifier:
                    connection.execute("UPDATE calculation_records SET identifier=? WHERE id=?", (display_identifier, calculation_id))

            latest = connection.execute(
                "SELECT * FROM calculation_versions WHERE calculation_id=? ORDER BY version DESC LIMIT 1",
                (calculation_id,),
            ).fetchone()
            latest_version = int(latest["version"]) if latest else 0

            # A versão-base representa o snapshot que o usuário decidiu editar e pode
            # ser histórica. A versão-atual-esperada é o token de concorrência: ela
            # garante que ninguém criou uma nova versão enquanto aquela edição estava
            # aberta. Clientes antigos, que não enviam o token, preservam a regra
            # anterior e só podem editar a versão mais recente.
            if expected_current_version is not None:
                if latest_version != expected_current_version:
                    raise ValueError(
                        f"Conflito de versão: este cálculo já está na V{latest_version}, "
                        f"mas a edição foi aberta quando a versão atual era V{expected_current_version}. "
                        "Recarregue o Histórico antes de salvar alterações."
                    )
            elif base_version is not None and latest is not None and latest_version != base_version:
                raise ValueError(
                    f"Conflito de versão: este cálculo já está na V{latest_version}, "
                    f"mas sua edição partiu da V{base_version}. Recarregue a versão atual antes de salvar alterações."
                )

            matching = connection.execute(
                "SELECT * FROM calculation_versions WHERE calculation_id=? AND business_hash=? ORDER BY version DESC LIMIT 1",
                (calculation_id, state_hash),
            ).fetchone()

            created = False
            if matching is not None:
                target = matching
                version = int(target["version"])
                version_base = int(target["base_version"]) if target["base_version"] is not None else None
                version_created_at = str(target["created_at"])
            else:
                reference = latest
                if base_version is not None:
                    reference = connection.execute(
                        "SELECT * FROM calculation_versions WHERE calculation_id=? AND version=?",
                        (calculation_id, base_version),
                    ).fetchone()
                    if reference is None:
                        raise ValueError("A versão base informada não existe neste cálculo.")
                version_base = int(reference["version"]) if reference is not None else None
                previous_request = json.loads(reference["request"]) if reference is not None else None
                diff = full_diff(previous_request, request_payload)
                version = latest_version + 1
                try:
                    connection.execute(
                        """
                        INSERT INTO calculation_versions(
                            calculation_id,version,base_version,created_at,created_by,request,total,index_name,
                            update_competence,business_hash,changed_fields,diff_json
                        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            calculation_id, version, version_base, moment, actor, request.model_dump_json(), total,
                            request.parametros.indice, competence, state_hash,
                            json.dumps(_changed_fields(diff), ensure_ascii=False), diff.model_dump_json(),
                        ),
                    )
                except sqlite3.IntegrityError as exc:
                    # A constraint única é a última barreira contra duas transações
                    # que tentem materializar o mesmo estado funcional.
                    duplicate = connection.execute(
                        "SELECT * FROM calculation_versions WHERE calculation_id=? AND business_hash=?",
                        (calculation_id, state_hash),
                    ).fetchone()
                    if duplicate is None:
                        raise
                    version = int(duplicate["version"])
                    version_base = int(duplicate["base_version"]) if duplicate["base_version"] is not None else None
                    version_created_at = str(duplicate["created_at"])
                else:
                    created = True
                    version_created_at = moment

            execution_id = f"exec_{uuid4().hex}"
            metadata = response.metadata
            connection.execute(
                """
                INSERT INTO calculation_executions(
                    id,calculation_id,version,executed_at,executed_by,response,input_hash,policy_hash,
                    engine_hash,indices_hash,duration_ms
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    execution_id, calculation_id, version, moment, actor, response.model_dump_json(),
                    metadata.entrada_sha256, metadata.politica_sha256, metadata.motor_sha256,
                    metadata.indices_sha256, metadata.duracao_ms,
                ),
            )
            connection.execute(
                """
                INSERT INTO calculation_artifacts(
                    id,execution_id,kind,sha256,size_bytes,mime_type,content,created_at
                ) VALUES(?,?,?,?,?,'application/pdf',?,?)
                """,
                (f"art_{uuid4().hex}", execution_id, "memoria", _artifact_hash(pdf), len(pdf), sqlite3.Binary(pdf), moment),
            )
            connection.execute("UPDATE calculation_records SET updated_at=? WHERE id=?", (moment, calculation_id))

        return (
            CalculationVersionRef(calculo_id=calculation_id, versao=version, versao_base=version_base, criado_em=version_created_at, criada=created),
            CalculationExecutionRef(execucao_id=execution_id, calculo_id=calculation_id, versao=version, executada_em=moment, nova_versao=created),
        )

    def history(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        origin: str | None = None,
        state: CalculationState | None = None,
        index_name: str | None = None,
        created_by: str | None = None,
        updated_from: date | None = None,
        updated_to: date | None = None,
        sort: str = "processo",
    ) -> CalculationHistoryPage:
        conditions: list[str] = []
        params: list[object] = []
        if search:
            term = search.strip()
            normalized_term = "".join(character for character in term.upper() if character.isalnum())
            conditions.append("(LOWER(r.identifier) LIKE ? OR UPPER(r.normalized_identifier) LIKE ?)")
            params.extend([f"%{term.lower()}%", f"%{normalized_term}%"])
        if origin:
            conditions.append("r.origin=?")
            params.append(origin)
        if state:
            conditions.append("r.state=?")
            params.append(state)
        if index_name:
            conditions.append("LOWER(v.index_name) LIKE ?")
            params.append(f"%{index_name.strip().lower()}%")
        if created_by:
            conditions.append("LOWER(r.created_by) LIKE ?")
            params.append(f"%{created_by.strip().lower()}%")
        if updated_from:
            conditions.append("r.updated_at>=?")
            params.append(datetime.combine(updated_from, clock_time.min, tzinfo=timezone.utc).isoformat())
        if updated_to:
            conditions.append("r.updated_at<=?")
            params.append(datetime.combine(updated_to, clock_time.max, tzinfo=timezone.utc).isoformat())
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        base_from = """
            FROM calculation_records r
            JOIN calculation_versions v ON v.calculation_id=r.id
             AND v.version=(SELECT MAX(v2.version) FROM calculation_versions v2 WHERE v2.calculation_id=r.id)
        """
        order_by = {
            "processo": "CASE WHEN r.origin='processo' THEN 0 ELSE 1 END, LENGTH(r.normalized_identifier), r.normalized_identifier, r.identifier",
            "atualizado_desc": "r.updated_at DESC, r.identifier",
            "atualizado_asc": "r.updated_at ASC, r.identifier",
            "criado_desc": "r.created_at DESC, r.identifier",
            "criado_asc": "r.created_at ASC, r.identifier",
        }.get(sort, "CASE WHEN r.origin='processo' THEN 0 ELSE 1 END, LENGTH(r.normalized_identifier), r.normalized_identifier, r.identifier")
        offset = (page - 1) * page_size
        with self.database.connection() as connection:
            total = int(connection.execute(f"SELECT COUNT(*) {base_from}{where}", params).fetchone()[0])
            rows = connection.execute(
                f"""
                SELECT r.*,v.version AS current_version,v.total,v.index_name,v.update_competence,
                       (SELECT COUNT(*) FROM calculation_versions vx WHERE vx.calculation_id=r.id) AS version_count,
                       (SELECT COUNT(*) FROM calculation_executions ex WHERE ex.calculation_id=r.id) AS execution_count
                {base_from}{where}
                ORDER BY {order_by}
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            ).fetchall()
        items = [
            CalculationHistoryItem(
                calculo_id=str(row["id"]), origem_calculo=str(row["origin"]),
                identificador_calculo=str(row["identifier"] or row["process"]),
                numero_processo=str(row["identifier"] or row["process"]) if row["origin"] == "processo" else None,
                numero_processo_normalizado=str(row["normalized_identifier"]) if row["origin"] == "processo" else None,
                estado=str(row["state"] or "ativo"), criado_em=str(row["created_at"]), criado_por=str(row["created_by"]),
                atualizado_em=str(row["updated_at"]), quantidade_versoes=int(row["version_count"]),
                quantidade_execucoes=int(row["execution_count"]), versao_atual=int(row["current_version"]),
                total_atual=str(row["total"]) if row["total"] is not None else None, indice_atual=str(row["index_name"]),
                competencia_atualizacao_atual=str(row["update_competence"]),
            )
            for row in rows
        ]
        return CalculationHistoryPage(itens=items, pagina=page, tamanho_pagina=page_size, total_itens=total, total_paginas=math.ceil(total / page_size) if total else 0)

    def versions(self, calculation_id: str, *, page: int = 1, page_size: int = 50) -> CalculationVersionsPage | None:
        offset = (page - 1) * page_size
        with self.database.connection() as connection:
            exists = connection.execute("SELECT 1 FROM calculation_records WHERE id=?", (calculation_id,)).fetchone()
            if exists is None:
                return None
            total = int(connection.execute("SELECT COUNT(*) FROM calculation_versions WHERE calculation_id=?", (calculation_id,)).fetchone()[0])
            rows = connection.execute(
                """
                SELECT v.*,
                       (SELECT COUNT(*) FROM calculation_executions e WHERE e.calculation_id=v.calculation_id AND e.version=v.version) AS execution_count,
                       (SELECT MAX(e.executed_at) FROM calculation_executions e WHERE e.calculation_id=v.calculation_id AND e.version=v.version) AS last_execution,
                       (SELECT e.input_hash FROM calculation_executions e WHERE e.calculation_id=v.calculation_id AND e.version=v.version ORDER BY e.executed_at,e.id LIMIT 1) AS input_hash,
                       (SELECT e.indices_hash FROM calculation_executions e WHERE e.calculation_id=v.calculation_id AND e.version=v.version ORDER BY e.executed_at,e.id LIMIT 1) AS indices_hash
                FROM calculation_versions v
                WHERE v.calculation_id=?
                ORDER BY v.version DESC
                LIMIT ? OFFSET ?
                """,
                (calculation_id, page_size, offset),
            ).fetchall()
        summaries = [
            CalculationVersionSummary(
                versao=int(row["version"]), versao_base=int(row["base_version"]) if row["base_version"] is not None else None,
                criado_em=str(row["created_at"]), criado_por=str(row["created_by"]),
                total_geral=str(row["total"]) if row["total"] is not None else None, indice=str(row["index_name"]),
                competencia_atualizacao=str(row["update_competence"]), entrada_sha256=str(row["input_hash"] or ""),
                indices_sha256=str(row["indices_hash"] or ""), campos_alterados=json.loads(row["changed_fields"] or "[]"),
                diff=CalculationDiff.model_validate_json(row["diff_json"] or "{}"), quantidade_execucoes=max(1, int(row["execution_count"] or 0)),
                ultima_execucao_em=str(row["last_execution"]) if row["last_execution"] else None,
            )
            for row in rows
        ]
        return CalculationVersionsPage(calculo_id=calculation_id, itens=summaries, pagina=page, tamanho_pagina=page_size, total_itens=total, total_paginas=math.ceil(total / page_size) if total else 0)

    def version(self, calculation_id: str, version: int) -> CalculationVersionDetail | None:
        with self.database.connection() as connection:
            row = connection.execute(
                """
                SELECT r.process,r.origin,r.identifier,r.state,v.*,
                       (SELECT MAX(vx.version) FROM calculation_versions vx WHERE vx.calculation_id=v.calculation_id) AS current_version,
                       (SELECT COUNT(*) FROM calculation_executions e WHERE e.calculation_id=v.calculation_id AND e.version=v.version) AS execution_count,
                       (SELECT e.response FROM calculation_executions e WHERE e.calculation_id=v.calculation_id AND e.version=v.version ORDER BY e.executed_at,e.id LIMIT 1) AS initial_response
                FROM calculation_versions v
                JOIN calculation_records r ON r.id=v.calculation_id
                WHERE v.calculation_id=? AND v.version=?
                """,
                (calculation_id, version),
            ).fetchone()
        if row is None or not row["initial_response"]:
            return None
        origin = str(row["origin"] or "processo")
        identifier = str(row["identifier"] or row["process"])
        response_payload = json.loads(row["initial_response"])
        response_payload.setdefault("identificador_calculo", identifier)
        return CalculationVersionDetail(
            calculo_id=calculation_id, origem_calculo=origin, identificador_calculo=identifier,
            numero_processo=identifier if origin == "processo" else None, estado_calculo=str(row["state"] or "ativo"),
            versao=int(row["version"]), versao_atual=int(row["current_version"]),
            versao_base=int(row["base_version"]) if row["base_version"] is not None else None,
            criado_em=str(row["created_at"]), criado_por=str(row["created_by"]),
            campos_alterados=json.loads(row["changed_fields"] or "[]"), diff=CalculationDiff.model_validate_json(row["diff_json"] or "{}"),
            quantidade_execucoes=max(1, int(row["execution_count"] or 0)), requisicao=CalculationRequest.model_validate_json(row["request"]),
            resultado=CalculationResponse.model_validate(response_payload),
        )

    def compare(self, calculation_id: str, version_from: int, version_to: int) -> CalculationComparison | None:
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT version,request,total FROM calculation_versions WHERE calculation_id=? AND version IN (?,?)",
                (calculation_id, version_from, version_to),
            ).fetchall()
        by_version = {int(row["version"]): row for row in rows}
        if version_from not in by_version or version_to not in by_version:
            return None
        before_row, after_row = by_version[version_from], by_version[version_to]
        total_before = str(before_row["total"]) if before_row["total"] is not None else None
        total_after = str(after_row["total"]) if after_row["total"] is not None else None
        return CalculationComparison(
            calculo_id=calculation_id, versao_origem=version_from, versao_destino=version_to,
            total_origem=total_before, total_destino=total_after, diferenca_total=_total_difference(total_before, total_after),
            diff=full_diff(json.loads(before_row["request"]), json.loads(after_row["request"])),
        )

    def change_state(self, calculation_id: str, state: CalculationState, *, actor: str) -> CalculationStateResult | None:
        moment = timestamp()
        with self.database.connection() as connection:
            row = connection.execute("SELECT state FROM calculation_records WHERE id=?", (calculation_id,)).fetchone()
            if row is None:
                return None
            connection.execute(
                "UPDATE calculation_records SET state=?,state_changed_at=?,state_changed_by=?,updated_at=? WHERE id=?",
                (state, moment, actor, moment, calculation_id),
            )
            connection.execute(
                "INSERT INTO audit(moment,event,payload) VALUES(?,?,?)",
                (moment, "calculation_state_changed", json.dumps({"calculation_id": calculation_id, "state": state})),
            )
        return CalculationStateResult(calculo_id=calculation_id, estado=state, atualizado_em=moment)

    def executions(self, calculation_id: str, version: int, *, page: int = 1, page_size: int = 20) -> CalculationExecutionsPage | None:
        offset = (page - 1) * page_size
        with self.database.connection() as connection:
            exists = connection.execute(
                "SELECT 1 FROM calculation_versions WHERE calculation_id=? AND version=?",
                (calculation_id, version),
            ).fetchone()
            if exists is None:
                return None
            total = int(connection.execute(
                "SELECT COUNT(*) FROM calculation_executions WHERE calculation_id=? AND version=?",
                (calculation_id, version),
            ).fetchone()[0])
            rows = connection.execute(
                """
                SELECT id,version,executed_at,executed_by,input_hash,policy_hash,engine_hash,indices_hash,duration_ms
                FROM calculation_executions
                WHERE calculation_id=? AND version=?
                ORDER BY executed_at DESC,id DESC
                LIMIT ? OFFSET ?
                """,
                (calculation_id, version, page_size, offset),
            ).fetchall()
        items = [
            CalculationExecutionSummary(
                execucao_id=str(row["id"]), versao=int(row["version"]), executada_em=str(row["executed_at"]),
                executada_por=str(row["executed_by"]), entrada_sha256=str(row["input_hash"]),
                politica_sha256=str(row["policy_hash"]), motor_sha256=str(row["engine_hash"]),
                indices_sha256=str(row["indices_hash"]), duracao_ms=float(row["duration_ms"]),
            )
            for row in rows
        ]
        return CalculationExecutionsPage(
            calculo_id=calculation_id, versao=version, itens=items, pagina=page, tamanho_pagina=page_size,
            total_itens=total, total_paginas=math.ceil(total / page_size) if total else 0,
        )

    def version_pdf(self, calculation_id: str, version: int, *, audit: bool) -> bytes | None:
        """Lê artefato congelado; ``audit`` existe apenas para históricos legados.

        Novas execuções persistem somente ``memoria``. Para não alterar a tela de
        Histórico nesta entrega, solicitações legadas por ``memoria_auditavel``
        usam a memória padrão quando o artefato antigo não existe. Nenhum PDF
        adicional é gerado.
        """
        kinds = ("memoria_auditavel", "memoria") if audit else ("memoria",)
        with self.database.connection() as connection:
            for kind in kinds:
                row = connection.execute(
                    """
                    SELECT a.content
                    FROM calculation_executions e
                    JOIN calculation_artifacts a ON a.execution_id=e.id AND a.kind=?
                    WHERE e.calculation_id=? AND e.version=?
                    ORDER BY e.executed_at,e.id
                    LIMIT 1
                    """,
                    (kind, calculation_id, version),
                ).fetchone()
                if row and row["content"] is not None:
                    return bytes(row["content"])
        return None

    def execution_pdf(self, calculation_id: str, execution_id: str, *, audit: bool) -> bytes | None:
        """Lê a memória da execução; ``audit`` mantém somente compatibilidade legada."""
        kinds = ("memoria_auditavel", "memoria") if audit else ("memoria",)
        with self.database.connection() as connection:
            for kind in kinds:
                row = connection.execute(
                    """
                    SELECT a.content
                    FROM calculation_executions e
                    JOIN calculation_artifacts a ON a.execution_id=e.id AND a.kind=?
                    WHERE e.calculation_id=? AND e.id=?
                    """,
                    (kind, calculation_id, execution_id),
                ).fetchone()
                if row and row["content"] is not None:
                    return bytes(row["content"])
        return None
