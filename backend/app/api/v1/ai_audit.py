from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.deps import get_db


router = APIRouter(prefix="/ai-audit", tags=["ai-audit"])


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)

    if hasattr(value, "isoformat"):
        return value.isoformat()

    return value


def _row_to_dict(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: _jsonable(value)
        for key, value in row.items()
    }


@router.get("/logs")
def list_ai_invocation_logs(
    scene: str | None = Query(default=None, description="AI 场景，例如 ticket_ai_classifier / rag_ask_llm / analytics_nl2sql"),
    success: bool | None = Query(default=None, description="是否成功"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    where_clauses: list[str] = []
    params: dict[str, Any] = {
        "limit": limit,
        "offset": offset,
    }

    if scene:
        where_clauses.append("scene = :scene")
        params["scene"] = scene

    if success is not None:
        where_clauses.append("success = :success")
        params["success"] = success

    where_sql = ""

    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    total = db.execute(
        text(
            f"""
            SELECT COUNT(*)
            FROM ai_invocation_logs
            {where_sql}
            """
        ),
        params,
    ).scalar_one()

    rows = db.execute(
        text(
            f"""
            SELECT
                id,
                trace_id,
                scene,
                provider,
                model,
                input_summary,
                input_payload,
                output_payload,
                success,
                error_message,
                latency_ms,
                created_at
            FROM ai_invocation_logs
            {where_sql}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings().all()

    return {
        "total": int(total),
        "limit": limit,
        "offset": offset,
        "items": [
            _row_to_dict(dict(row))
            for row in rows
        ],
    }


@router.get("/summary")
def summarize_ai_invocation_logs(
    days: int = Query(default=7, ge=1, le=90),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    rows = db.execute(
        text(
            """
            SELECT
                scene,
                COUNT(*) AS total,
                SUM(CASE WHEN success THEN 1 ELSE 0 END) AS success_count,
                SUM(CASE WHEN success THEN 0 ELSE 1 END) AS failed_count,
                ROUND(AVG(latency_ms)::numeric, 2) AS avg_latency_ms,
                MAX(created_at) AS latest_at
            FROM ai_invocation_logs
            WHERE created_at >= NOW() - (:days || ' days')::interval
            GROUP BY scene
            ORDER BY total DESC, scene ASC
            """
        ),
        {
            "days": days,
        },
    ).mappings().all()

    return {
        "days": days,
        "items": [
            _row_to_dict(dict(row))
            for row in rows
        ],
    }
