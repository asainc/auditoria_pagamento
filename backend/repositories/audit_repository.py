"""Persistência de auditoria técnica e revisão humana."""
from __future__ import annotations

import json

from backend.contracts.audit import ParameterChangeInput, ParameterChangeRecord
from backend.persistence.schema import timestamp
from backend.persistence.sqlite import SQLiteDatabase


class AuditRepository:
    """Eventos imutáveis sem conteúdo documental bruto."""

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def append(self, event: str, payload: dict[str, str | int | float | bool]) -> None:
        with self.database.connection() as connection:
            connection.execute(
                "INSERT INTO audit(moment,event,payload) VALUES(?,?,?)",
                (timestamp(), event, json.dumps(payload, ensure_ascii=False)),
            )

    def add_parameter_change(
        self,
        change: ParameterChangeInput,
        *,
        actor: str,
        extracted_value: object = None,
        extracted_source: str | None = None,
    ) -> ParameterChangeRecord:
        moment = timestamp()
        payload = change.model_dump(mode="json")
        payload.update({"ator_tecnico": actor, "valor_extraido": extracted_value, "origem_extraida": extracted_source})
        with self.database.connection() as connection:
            cursor = connection.execute(
                "INSERT INTO parameter_changes(moment,draft,process,origin,field,payload) VALUES(?,?,?,?,?,?)",
                (moment, change.rascunho_id, change.numero_processo, change.origem_calculo, change.campo, json.dumps(payload, ensure_ascii=False)),
            )
            identifier = int(cursor.lastrowid)
        return ParameterChangeRecord(
            **change.model_dump(),
            identificador=identifier,
            registrado_em=moment,
            ator_tecnico=actor,
            valor_extraido=extracted_value,
            origem_extraida=extracted_source,
        )

    def parameter_changes(self, *, process: str | None = None, draft: str | None = None) -> list[ParameterChangeRecord]:
        if bool(process) == bool(draft):
            raise ValueError("Informe exatamente process ou draft para consultar alterações.")
        column, value = ("process", process) if process else ("draft", draft)
        with self.database.connection() as connection:
            rows = connection.execute(
                f"SELECT id,moment,payload FROM parameter_changes WHERE {column}=? ORDER BY id",
                (value,),
            ).fetchall()
        records: list[ParameterChangeRecord] = []
        for row in rows:
            payload = json.loads(row["payload"])
            records.append(ParameterChangeRecord(
                origem_calculo=payload["origem_calculo"],
                numero_processo=payload.get("numero_processo"),
                rascunho_id=payload["rascunho_id"],
                campo=payload["campo"],
                valor_anterior=payload.get("valor_anterior"),
                valor_novo=payload.get("valor_novo"),
                extracao_id=payload.get("extracao_id"),
                identificador=int(row["id"]),
                registrado_em=str(row["moment"]),
                ator_tecnico=payload.get("ator_tecnico", "desconhecido"),
                valor_extraido=payload.get("valor_extraido"),
                origem_extraida=payload.get("origem_extraida"),
            ))
        return records
