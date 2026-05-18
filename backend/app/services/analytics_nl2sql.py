from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.nl2sql_safety import Nl2sqlSafetyError, validate_select_sql


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, datetime):
        return value.isoformat()

    return value


def _rows_to_dicts(result) -> tuple[list[str], list[dict[str, Any]]]:
    columns = list(result.keys())
    rows: list[dict[str, Any]] = []

    for row in result:
        item = {}
        for key, value in row._mapping.items():
            item[key] = _jsonable(value)
        rows.append(item)

    return columns, rows


def _extract_days(question: str) -> int:
    match = re.search(r"最近\s*(\d+)\s*天", question)
    if not match:
        return 7

    days = int(match.group(1))

    if days <= 0:
        return 7

    return min(days, 90)


def _start_time(days: int) -> datetime:
    return datetime.utcnow() - timedelta(days=days)


def _normalize_limit(limit: int) -> int:
    try:
        value = int(limit)
    except Exception:
        value = 20

    return max(1, min(value, 100))


def _log_query(
    db: Session,
    *,
    question: str,
    intent: str,
    generated_sql: str,
    status: str,
    blocked_reason: str | None,
    tables_used: list[str],
    columns: list[str],
    row_count: int,
    applied_limit: int | None,
) -> str:
    log_id = str(uuid.uuid4())

    db.execute(
        text(
            """
            INSERT INTO analytics_query_logs (
                id,
                question,
                intent,
                generated_sql,
                status,
                blocked_reason,
                tables_used,
                columns_json,
                row_count,
                applied_limit,
                created_at
            )
            VALUES (
                :id,
                :question,
                :intent,
                :generated_sql,
                :status,
                :blocked_reason,
                CAST(:tables_used AS jsonb),
                CAST(:columns_json AS jsonb),
                :row_count,
                :applied_limit,
                now()
            )
            """
        ),
        {
            "id": log_id,
            "question": question,
            "intent": intent,
            "generated_sql": generated_sql,
            "status": status,
            "blocked_reason": blocked_reason,
            "tables_used": json.dumps(tables_used, ensure_ascii=False),
            "columns_json": json.dumps(columns, ensure_ascii=False),
            "row_count": row_count,
            "applied_limit": applied_limit,
        },
    )

    db.commit()

    return log_id


def _execute_safe_select(
    db: Session,
    *,
    question: str,
    intent: str,
    sql: str,
    params: dict[str, Any],
    limit: int,
) -> tuple[list[str], list[dict[str, Any]], dict[str, Any]]:
    final_sql = sql.strip()
    safe_sql = None
    safe_params = dict(params)
    applied_limit = _normalize_limit(limit)
    tables_used: list[str] = []

    try:
        safety = validate_select_sql(
            final_sql,
            row_limit=applied_limit,
        )

        safe_sql = safety.sql
        tables_used = safety.tables_used
        applied_limit = safety.applied_limit

        if ":__safe_limit" in safe_sql:
            safe_params["__safe_limit"] = applied_limit

        result = db.execute(text(safe_sql), safe_params)
        columns, rows = _rows_to_dicts(result)

        log_id = _log_query(
            db,
            question=question,
            intent=intent,
            generated_sql=safe_sql,
            status="success",
            blocked_reason=None,
            tables_used=tables_used,
            columns=columns,
            row_count=len(rows),
            applied_limit=applied_limit,
        )

        return columns, rows, {
            "safe": True,
            "blocked_reason": None,
            "tables_used": tables_used,
            "applied_limit": applied_limit,
            "query_log_id": log_id,
        }

    except Nl2sqlSafetyError as exc:
        log_id = _log_query(
            db,
            question=question,
            intent=intent,
            generated_sql=final_sql,
            status="blocked",
            blocked_reason=str(exc),
            tables_used=tables_used,
            columns=[],
            row_count=0,
            applied_limit=applied_limit,
        )

        raise ValueError(f"NL2SQL 安全校验失败：{exc}; query_log_id={log_id}") from exc

    except Exception as exc:
        db.rollback()

        try:
            log_id = _log_query(
                db,
                question=question,
                intent=intent,
                generated_sql=safe_sql or final_sql,
                status="error",
                blocked_reason=f"{type(exc).__name__}: {exc}",
                tables_used=tables_used,
                columns=[],
                row_count=0,
                applied_limit=applied_limit,
            )
        except Exception:
            log_id = None

        suffix = f"; query_log_id={log_id}" if log_id else ""
        raise RuntimeError(f"NL2SQL 查询执行失败：{type(exc).__name__}: {exc}{suffix}") from exc


def ask_analytics_question(
    db: Session,
    question: str,
    limit: int = 20,
) -> dict[str, Any]:
    limit = _normalize_limit(limit)
    days = _extract_days(question)
    start = _start_time(days)

    if "物流" in question and ("多少" in question or "几" in question or "数量" in question):
        return _logistics_delay_ticket_count(db, question, days, start, limit)

    if "优先级" in question:
        return _ticket_priority_distribution(db, question, days, start, limit)

    if "状态" in question and ("工单" in question or "售后" in question):
        return _ticket_status_distribution(db, question, days, start, limit)

    if "退款" in question and ("状态" in question or "分布" in question or "统计" in question):
        return _refund_status_distribution(db, question, days, start, limit)

    if (
        "工单" in question
        or "售后" in question
        or "投诉" in question
        or "问题" in question
        or "趋势" in question
        or "分布" in question
    ):
        return _ticket_category_distribution(db, question, days, start, limit)

    return _overview(db, question, days, start, limit)


def _response(
    *,
    question: str,
    intent: str,
    sql: str,
    columns: list[str],
    rows: list[dict[str, Any]],
    summary: str,
    safety: dict[str, Any],
) -> dict[str, Any]:
    return {
        "question": question,
        "intent": intent,
        "sql": sql.strip(),
        "columns": columns,
        "rows": rows,
        "summary": summary,
        "safe": bool(safety.get("safe", True)),
        "blocked_reason": safety.get("blocked_reason"),
        "tables_used": safety.get("tables_used", []),
        "applied_limit": safety.get("applied_limit"),
        "query_log_id": safety.get("query_log_id"),
    }


def _logistics_delay_ticket_count(
    db: Session,
    question: str,
    days: int,
    start: datetime,
    limit: int,
) -> dict[str, Any]:
    intent = "logistics_delay_ticket_count"

    sql = """
    SELECT
        COUNT(*) AS ticket_count
    FROM tickets
    WHERE created_at >= :start_time
      AND (
        category ILIKE '%logistics%'
        OR category ILIKE '%物流%'
        OR title ILIKE '%物流%'
        OR summary ILIKE '%物流%'
        OR customer_question ILIKE '%物流%'
      )
    """

    columns, rows, safety = _execute_safe_select(
        db,
        question=question,
        intent=intent,
        sql=sql,
        params={
            "start_time": start,
        },
        limit=limit,
    )

    count = rows[0]["ticket_count"] if rows else 0

    return _response(
        question=question,
        intent=intent,
        sql=safety_sql_for_display(sql),
        columns=columns,
        rows=rows,
        summary=f"最近 {days} 天物流延迟相关工单共 {count} 条。",
        safety=safety,
    )


def _ticket_category_distribution(
    db: Session,
    question: str,
    days: int,
    start: datetime,
    limit: int,
) -> dict[str, Any]:
    intent = "ticket_category_distribution"

    sql = """
    SELECT
        category,
        COUNT(*) AS ticket_count
    FROM tickets
    WHERE created_at >= :start_time
    GROUP BY category
    ORDER BY ticket_count DESC
    LIMIT :limit
    """

    columns, rows, safety = _execute_safe_select(
        db,
        question=question,
        intent=intent,
        sql=sql,
        params={
            "start_time": start,
            "limit": limit,
        },
        limit=limit,
    )

    return _response(
        question=question,
        intent=intent,
        sql=sql,
        columns=columns,
        rows=rows,
        summary=f"最近 {days} 天工单按问题类型统计，共返回 {len(rows)} 类。",
        safety=safety,
    )


def _ticket_priority_distribution(
    db: Session,
    question: str,
    days: int,
    start: datetime,
    limit: int,
) -> dict[str, Any]:
    intent = "ticket_priority_distribution"

    sql = """
    SELECT
        priority,
        COUNT(*) AS ticket_count
    FROM tickets
    WHERE created_at >= :start_time
    GROUP BY priority
    ORDER BY ticket_count DESC
    LIMIT :limit
    """

    columns, rows, safety = _execute_safe_select(
        db,
        question=question,
        intent=intent,
        sql=sql,
        params={
            "start_time": start,
            "limit": limit,
        },
        limit=limit,
    )

    return _response(
        question=question,
        intent=intent,
        sql=sql,
        columns=columns,
        rows=rows,
        summary=f"最近 {days} 天工单按优先级统计，共返回 {len(rows)} 类。",
        safety=safety,
    )


def _ticket_status_distribution(
    db: Session,
    question: str,
    days: int,
    start: datetime,
    limit: int,
) -> dict[str, Any]:
    intent = "ticket_status_distribution"

    sql = """
    SELECT
        status,
        COUNT(*) AS ticket_count
    FROM tickets
    WHERE created_at >= :start_time
    GROUP BY status
    ORDER BY ticket_count DESC
    LIMIT :limit
    """

    columns, rows, safety = _execute_safe_select(
        db,
        question=question,
        intent=intent,
        sql=sql,
        params={
            "start_time": start,
            "limit": limit,
        },
        limit=limit,
    )

    return _response(
        question=question,
        intent=intent,
        sql=sql,
        columns=columns,
        rows=rows,
        summary=f"最近 {days} 天工单按状态统计，共返回 {len(rows)} 类。",
        safety=safety,
    )


def _refund_status_distribution(
    db: Session,
    question: str,
    days: int,
    start: datetime,
    limit: int,
) -> dict[str, Any]:
    intent = "refund_status_distribution"

    sql = """
    SELECT
        status,
        COUNT(*) AS refund_count
    FROM refunds
    WHERE created_at >= :start_time
    GROUP BY status
    ORDER BY refund_count DESC
    LIMIT :limit
    """

    columns, rows, safety = _execute_safe_select(
        db,
        question=question,
        intent=intent,
        sql=sql,
        params={
            "start_time": start,
            "limit": limit,
        },
        limit=limit,
    )

    return _response(
        question=question,
        intent=intent,
        sql=sql,
        columns=columns,
        rows=rows,
        summary=f"最近 {days} 天退款记录按状态统计，共返回 {len(rows)} 类。",
        safety=safety,
    )


def _overview(
    db: Session,
    question: str,
    days: int,
    start: datetime,
    limit: int,
) -> dict[str, Any]:
    intent = "ticket_overview"

    sql = """
    SELECT
        category,
        status,
        priority,
        COUNT(*) AS ticket_count
    FROM tickets
    WHERE created_at >= :start_time
    GROUP BY category, status, priority
    ORDER BY ticket_count DESC
    LIMIT :limit
    """

    columns, rows, safety = _execute_safe_select(
        db,
        question=question,
        intent=intent,
        sql=sql,
        params={
            "start_time": start,
            "limit": limit,
        },
        limit=limit,
    )

    return _response(
        question=question,
        intent=intent,
        sql=sql,
        columns=columns,
        rows=rows,
        summary=f"最近 {days} 天售后工单概览，共返回 {len(rows)} 条聚合结果。",
        safety=safety,
    )


def safety_sql_for_display(sql: str) -> str:
    sql = sql.strip()
    if "limit" not in sql.lower():
        return sql + "\nLIMIT :__safe_limit"
    return sql