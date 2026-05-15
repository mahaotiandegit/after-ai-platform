from __future__ import annotations

import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


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


def _execute_select(
    db: Session,
    sql: str,
    params: dict[str, Any],
) -> tuple[list[str], list[dict[str, Any]]]:
    normalized_sql = sql.strip().lower()

    if not normalized_sql.startswith("select"):
        raise ValueError("Only SELECT SQL is allowed")

    if ";" in normalized_sql:
        raise ValueError("Semicolon is not allowed in analytics SQL")

    result = db.execute(text(sql), params)
    return _rows_to_dicts(result)


def ask_analytics_question(
    db: Session,
    question: str,
    limit: int = 20,
) -> dict[str, Any]:
    days = _extract_days(question)
    start = _start_time(days)
    q = question.lower()

    if "物流" in question and ("多少" in question or "几" in question or "数量" in question):
        return _logistics_delay_ticket_count(db, question, days, start)

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


def _logistics_delay_ticket_count(
    db: Session,
    question: str,
    days: int,
    start: datetime,
) -> dict[str, Any]:
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

    columns, rows = _execute_select(
        db,
        sql,
        {
            "start_time": start,
        },
    )

    count = rows[0]["ticket_count"] if rows else 0

    return {
        "question": question,
        "intent": "logistics_delay_ticket_count",
        "sql": sql.strip(),
        "columns": columns,
        "rows": rows,
        "summary": f"最近 {days} 天物流延迟相关工单共 {count} 条。",
    }


def _ticket_category_distribution(
    db: Session,
    question: str,
    days: int,
    start: datetime,
    limit: int,
) -> dict[str, Any]:
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

    columns, rows = _execute_select(
        db,
        sql,
        {
            "start_time": start,
            "limit": limit,
        },
    )

    return {
        "question": question,
        "intent": "ticket_category_distribution",
        "sql": sql.strip(),
        "columns": columns,
        "rows": rows,
        "summary": f"最近 {days} 天工单按问题类型统计，共返回 {len(rows)} 类。",
    }


def _ticket_priority_distribution(
    db: Session,
    question: str,
    days: int,
    start: datetime,
    limit: int,
) -> dict[str, Any]:
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

    columns, rows = _execute_select(
        db,
        sql,
        {
            "start_time": start,
            "limit": limit,
        },
    )

    return {
        "question": question,
        "intent": "ticket_priority_distribution",
        "sql": sql.strip(),
        "columns": columns,
        "rows": rows,
        "summary": f"最近 {days} 天工单按优先级统计，共返回 {len(rows)} 类。",
    }


def _ticket_status_distribution(
    db: Session,
    question: str,
    days: int,
    start: datetime,
    limit: int,
) -> dict[str, Any]:
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

    columns, rows = _execute_select(
        db,
        sql,
        {
            "start_time": start,
            "limit": limit,
        },
    )

    return {
        "question": question,
        "intent": "ticket_status_distribution",
        "sql": sql.strip(),
        "columns": columns,
        "rows": rows,
        "summary": f"最近 {days} 天工单按状态统计，共返回 {len(rows)} 类。",
    }


def _refund_status_distribution(
    db: Session,
    question: str,
    days: int,
    start: datetime,
    limit: int,
) -> dict[str, Any]:
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

    columns, rows = _execute_select(
        db,
        sql,
        {
            "start_time": start,
            "limit": limit,
        },
    )

    return {
        "question": question,
        "intent": "refund_status_distribution",
        "sql": sql.strip(),
        "columns": columns,
        "rows": rows,
        "summary": f"最近 {days} 天退款记录按状态统计，共返回 {len(rows)} 类。",
    }


def _overview(
    db: Session,
    question: str,
    days: int,
    start: datetime,
    limit: int,
) -> dict[str, Any]:
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

    columns, rows = _execute_select(
        db,
        sql,
        {
            "start_time": start,
            "limit": limit,
        },
    )

    return {
        "question": question,
        "intent": "ticket_overview",
        "sql": sql.strip(),
        "columns": columns,
        "rows": rows,
        "summary": f"最近 {days} 天售后工单概览，共返回 {len(rows)} 条聚合结果。",
    }