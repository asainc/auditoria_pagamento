"""Persistência de telemetria FinOps e cache determinístico de respostas estruturadas."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from backend.contracts.quality import FinOpsStageMetric, FinOpsSummary
from backend.persistence.schema import timestamp
from backend.persistence.sqlite import SQLiteDatabase


class AiOperationsRepository:
    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    def cached_response(self, request_sha256: str, model: str, *, ttl_days: int = 30) -> str | None:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=max(1, ttl_days))).isoformat()
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT response_json,created_at FROM ai_prompt_cache WHERE request_sha256=? AND model=?",
                (request_sha256, model),
            ).fetchone()
            if row is not None and str(row["created_at"]) < cutoff:
                connection.execute("DELETE FROM ai_prompt_cache WHERE request_sha256=?", (request_sha256,))
                row = None
            if row is not None:
                connection.execute(
                    "UPDATE ai_prompt_cache SET hit_count=hit_count+1,last_hit_at=? WHERE request_sha256=?",
                    (timestamp(), request_sha256),
                )
        return str(row["response_json"]) if row else None

    def cache_response(self, request_sha256: str, model: str, stage: str, response_json: str) -> None:
        with self.database.connection() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO ai_prompt_cache(request_sha256,model,stage,response_json,created_at) VALUES(?,?,?,?,?)",
                (request_sha256, model, stage, response_json, timestamp()),
            )

    def record_usage(self, payload: dict) -> None:
        with self.database.connection() as connection:
            connection.execute(
                """
                INSERT INTO ai_usage_events(
                    created_at,job,stage,model,request_sha256,cache_hit,success,input_chars,output_chars,
                    input_tokens_actual,cached_input_tokens_actual,output_tokens_actual,input_tokens_estimated,
                    output_tokens_estimated,cost_estimated_usd,duration_ms,pages,structural_repair
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    timestamp(), payload.get("job"), payload["stage"], payload["model"], payload["request_sha256"],
                    int(bool(payload.get("cache_hit"))), int(bool(payload.get("success", True))),
                    int(payload.get("input_chars") or 0), int(payload.get("output_chars") or 0),
                    payload.get("input_tokens_actual"), payload.get("cached_input_tokens_actual"), payload.get("output_tokens_actual"),
                    int(payload.get("input_tokens_estimated") or 0), int(payload.get("output_tokens_estimated") or 0),
                    str(payload["cost_estimated_usd"]) if payload.get("cost_estimated_usd") is not None else None,
                    float(payload.get("duration_ms") or 0), payload.get("pages"), int(bool(payload.get("structural_repair"))),
                ),
            )

    def job_api_consumption(self, job: str) -> tuple[int, int]:
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT COALESCE(SUM(CASE WHEN cache_hit=0 THEN 1 ELSE 0 END),0),COALESCE(SUM(CASE WHEN cache_hit=0 THEN input_chars ELSE 0 END),0) FROM ai_usage_events WHERE job=?",
                (job,),
            ).fetchone()
        return int(row[0]), int(row[1])

    def current_month_cost(self) -> Decimal | None:
        """Retorna custo mensal apenas quando TODAS as chamadas têm estimativa disponível."""
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT cache_hit,cost_estimated_usd FROM ai_usage_events WHERE created_at>=?",
                (month_start,),
            ).fetchall()
        api_rows = [row for row in rows if not int(row["cache_hit"])]
        if not api_rows or any(row["cost_estimated_usd"] is None for row in api_rows):
            return None
        return sum((Decimal(str(row["cost_estimated_usd"])) for row in api_rows), Decimal("0"))

    def summary(
        self,
        days: int,
        *,
        monthly_budget_usd: Decimal | None = None,
        budget_warning_ratio: Decimal = Decimal("0.80"),
    ) -> FinOpsSummary:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with self.database.connection() as connection:
            rows = connection.execute("SELECT * FROM ai_usage_events WHERE created_at>=?", (cutoff,)).fetchall()
        calls = sum(1 for row in rows if not int(row["cache_hit"]))
        failures = sum(1 for row in rows if not int(row["cache_hit"]) and not int(row["success"]))
        hits = sum(1 for row in rows if int(row["cache_hit"]))
        input_chars = sum(int(row["input_chars"]) for row in rows)
        output_chars = sum(int(row["output_chars"]) for row in rows)
        estimated = sum(int(row["input_tokens_estimated"]) + int(row["output_tokens_estimated"]) for row in rows)
        api_rows = [row for row in rows if not int(row["cache_hit"])]
        actual_rows = [
            row for row in api_rows
            if row["input_tokens_actual"] is not None and row["output_tokens_actual"] is not None
        ]
        actual = (
            sum(int(row["input_tokens_actual"]) + int(row["output_tokens_actual"]) for row in actual_rows)
            if api_rows and len(actual_rows) == len(api_rows) else None
        )
        if api_rows and len(actual_rows) == len(api_rows):
            origin = "gateway"
        elif actual_rows:
            origin = "mista"
        else:
            origin = "estimativa_local" if api_rows else ("cache" if hits else "indisponivel")
        cost_rows = [row for row in api_rows if row["cost_estimated_usd"] is not None]
        cost = (
            sum((Decimal(str(row["cost_estimated_usd"])) for row in cost_rows), Decimal("0"))
            if api_rows and len(cost_rows) == len(api_rows) else None
        )
        by_stage: dict[str, list] = {}
        for row in rows:
            by_stage.setdefault(str(row["stage"]), []).append(row)
        stage_metrics: list[FinOpsStageMetric] = []
        for stage, stage_rows in sorted(by_stage.items()):
            stage_api_rows = [row for row in stage_rows if not int(row["cache_hit"])]
            stage_actual_rows = [
                row for row in stage_api_rows
                if row["input_tokens_actual"] is not None and row["output_tokens_actual"] is not None
            ]
            stage_cost_rows = [row for row in stage_api_rows if row["cost_estimated_usd"] is not None]
            stage_metrics.append(FinOpsStageMetric(
                etapa=stage,
                chamadas_api=sum(1 for row in stage_rows if not int(row["cache_hit"])),
                falhas_api=sum(1 for row in stage_rows if not int(row["cache_hit"]) and not int(row["success"])),
                acertos_cache=sum(1 for row in stage_rows if int(row["cache_hit"])),
                caracteres_entrada=sum(int(row["input_chars"]) for row in stage_rows),
                caracteres_saida=sum(int(row["output_chars"]) for row in stage_rows),
                tokens_reais=(
                    sum(int(row["input_tokens_actual"]) + int(row["output_tokens_actual"]) for row in stage_actual_rows)
                    if stage_api_rows and len(stage_actual_rows) == len(stage_api_rows) else None
                ),
                tokens_estimados=sum(int(row["input_tokens_estimated"]) + int(row["output_tokens_estimated"]) for row in stage_rows),
                custo_estimado_usd=(
                    sum((Decimal(str(row["cost_estimated_usd"])) for row in stage_cost_rows), Decimal("0"))
                    if stage_api_rows and len(stage_cost_rows) == len(stage_api_rows) else None
                ),
            ))
        denominator = calls + hits
        month_cost = self.current_month_cost()
        budget_ratio = None
        budget_status = "not_configured"
        if monthly_budget_usd is not None and monthly_budget_usd > 0 and month_cost is not None:
            budget_ratio = month_cost / monthly_budget_usd
            budget_status = "exceeded" if budget_ratio >= 1 else ("warning" if budget_ratio >= budget_warning_ratio else "ok")
        elif monthly_budget_usd is not None and monthly_budget_usd > 0:
            # Orçamento existe, mas sem tarifas/telemetria completas não é seguro afirmar consumo zero.
            budget_status = "unavailable"
        return FinOpsSummary(
            periodo_dias=days, chamadas_api=calls, falhas_api=failures, acertos_cache=hits,
            taxa_cache=(Decimal(hits) / Decimal(denominator) if denominator else Decimal("0")),
            caracteres_entrada=input_chars, caracteres_saida=output_chars, tokens_reais=actual,
            tokens_estimados=estimated, custo_estimado_usd=cost, origem_tokens=origin,
            economia_chamadas_cache=hits, orcamento_mensal_usd=monthly_budget_usd,
            consumo_mes_estimado_usd=month_cost, percentual_orcamento=budget_ratio,
            status_orcamento=budget_status, por_etapa=stage_metrics,
        )
