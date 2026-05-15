from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import inspect, text


DEFAULT_SCENES = [
    "ticket_ai_classifier",
    "rag_ask_llm",
    "analytics_nl2sql",
]


def _jsonable(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return value


def _has_table(db, table_name: str) -> bool:
    return inspect(db.bind).has_table(table_name)


def _columns(db, table_name: str) -> set[str]:
    if not _has_table(db, table_name):
        return set()
    return {col["name"] for col in inspect(db.bind).get_columns(table_name)}


def _scalar(db, sql: str, params: dict | None = None):
    return db.execute(text(sql), params or {}).scalar()


def _recent_rows(db, table_name: str, wanted_columns: list[str], where_sql: str = "", limit: int = 5):
    cols = _columns(db, table_name)
    selected = [c for c in wanted_columns if c in cols]

    if not selected:
        return []

    order_col = "created_at" if "created_at" in cols else selected[0]

    sql = f"""
        SELECT {", ".join(selected)}
        FROM {table_name}
        {where_sql}
        ORDER BY {order_col} DESC
        LIMIT :limit
    """

    rows = db.execute(text(sql), {"limit": limit}).mappings().all()
    return [
        {key: _jsonable(value) for key, value in dict(row).items()}
        for row in rows
    ]


def get_ai_quality_overview(db):
    has_ai_logs = _has_table(db, "ai_invocation_logs")
    has_bad_cases = _has_table(db, "bad_cases")

    ai_cols = _columns(db, "ai_invocation_logs") if has_ai_logs else set()
    bad_cols = _columns(db, "bad_cases") if has_bad_cases else set()

    total_invocations = 0
    successful_invocations = 0
    avg_latency_ms = 0.0
    scene_distribution = {scene: 0 for scene in DEFAULT_SCENES}
    recent_failed_invocations = []

    if has_ai_logs:
        total_invocations = int(_scalar(db, "SELECT COUNT(*) FROM ai_invocation_logs") or 0)

        if "success" in ai_cols:
            successful_invocations = int(
                _scalar(db, "SELECT COUNT(*) FROM ai_invocation_logs WHERE success = true") or 0
            )

        if "latency_ms" in ai_cols:
            avg_latency_ms = float(
                _scalar(db, "SELECT COALESCE(AVG(latency_ms), 0) FROM ai_invocation_logs") or 0
            )

        if "scene" in ai_cols:
            rows = db.execute(
                text("""
                    SELECT scene, COUNT(*) AS count
                    FROM ai_invocation_logs
                    GROUP BY scene
                    ORDER BY count DESC, scene ASC
                """)
            ).mappings().all()

            for row in rows:
                scene_distribution[str(row["scene"])] = int(row["count"])

        failed_where = "WHERE success = false" if "success" in ai_cols else ""
        recent_failed_invocations = _recent_rows(
            db,
            "ai_invocation_logs",
            [
                "id",
                "scene",
                "provider",
                "model",
                "success",
                "error_message",
                "latency_ms",
                "created_at",
            ],
            where_sql=failed_where,
            limit=5,
        )

    total_bad_cases = 0
    open_bad_cases = 0
    fixed_bad_cases = 0
    recent_bad_cases = []

    if has_bad_cases:
        total_bad_cases = int(_scalar(db, "SELECT COUNT(*) FROM bad_cases") or 0)

        if "status" in bad_cols:
            open_bad_cases = int(
                _scalar(db, "SELECT COUNT(*) FROM bad_cases WHERE status = 'open'") or 0
            )
            fixed_bad_cases = int(
                _scalar(db, "SELECT COUNT(*) FROM bad_cases WHERE status = 'fixed'") or 0
            )

        recent_bad_cases = _recent_rows(
            db,
            "bad_cases",
            [
                "id",
                "ai_log_id",
                "ai_invocation_log_id",
                "scene",
                "correction",
                "root_cause",
                "priority",
                "tags",
                "status",
                "created_at",
                "updated_at",
            ],
            limit=5,
        )

    success_rate = round(successful_invocations * 100 / total_invocations, 2) if total_invocations else 0.0
    bad_case_fix_rate = round(fixed_bad_cases * 100 / total_bad_cases, 2) if total_bad_cases else 0.0

    return {
        "total_invocations": total_invocations,
        "success_rate": success_rate,
        "avg_latency_ms": round(avg_latency_ms, 2),
        "scene_distribution": scene_distribution,
        "total_bad_cases": total_bad_cases,
        "open_bad_cases": open_bad_cases,
        "fixed_bad_cases": fixed_bad_cases,
        "bad_case_fix_rate": bad_case_fix_rate,
        "recent_bad_cases": recent_bad_cases,
        "recent_failed_invocations": recent_failed_invocations,
    }

def _clamp_days(days: int | None) -> int:
    if days is None:
        return 7
    try:
        days = int(days)
    except Exception:
        return 7
    if days < 1:
        return 7
    if days > 90:
        return 90
    return days


def get_ai_quality_trends(db, days: int = 7):
    """
    AI quality trend data for dashboard charts.

    Returns daily trends for:
    - invocation count
    - successful / failed invocation count
    - success rate
    - average latency
    - scene distribution by day
    - bad case creation count by day
    - bad case fixed count by day
    """
    days = _clamp_days(days)

    has_ai_logs = _has_table(db, "ai_invocation_logs")
    has_bad_cases = _has_table(db, "bad_cases")

    ai_cols = _columns(db, "ai_invocation_logs") if has_ai_logs else set()
    bad_cols = _columns(db, "bad_cases") if has_bad_cases else set()

    daily_invocations = []
    scene_daily_distribution = []
    daily_bad_cases = []

    if has_ai_logs and "created_at" in ai_cols:
        success_expr = "SUM(CASE WHEN success = true THEN 1 ELSE 0 END)" if "success" in ai_cols else "0"
        failed_expr = "SUM(CASE WHEN success = false THEN 1 ELSE 0 END)" if "success" in ai_cols else "0"
        avg_latency_expr = "COALESCE(AVG(latency_ms), 0)" if "latency_ms" in ai_cols else "0"

        rows = db.execute(
            text(f"""
                SELECT
                    DATE(created_at) AS day,
                    COUNT(*) AS total,
                    {success_expr} AS success_count,
                    {failed_expr} AS failed_count,
                    {avg_latency_expr} AS avg_latency_ms
                FROM ai_invocation_logs
                WHERE created_at >= NOW() - (:days * INTERVAL '1 day')
                GROUP BY DATE(created_at)
                ORDER BY day ASC
            """),
            {"days": days},
        ).mappings().all()

        for row in rows:
            total = int(row["total"] or 0)
            success_count = int(row["success_count"] or 0)
            failed_count = int(row["failed_count"] or 0)
            avg_latency_ms = float(row["avg_latency_ms"] or 0)
            success_rate = round(success_count * 100 / total, 2) if total else 0.0

            daily_invocations.append({
                "day": _jsonable(row["day"]),
                "total": total,
                "success_count": success_count,
                "failed_count": failed_count,
                "success_rate": success_rate,
                "avg_latency_ms": round(avg_latency_ms, 2),
            })

        if "scene" in ai_cols:
            rows = db.execute(
                text("""
                    SELECT
                        DATE(created_at) AS day,
                        scene,
                        COUNT(*) AS count
                    FROM ai_invocation_logs
                    WHERE created_at >= NOW() - (:days * INTERVAL '1 day')
                    GROUP BY DATE(created_at), scene
                    ORDER BY day ASC, scene ASC
                """),
                {"days": days},
            ).mappings().all()

            for row in rows:
                scene_daily_distribution.append({
                    "day": _jsonable(row["day"]),
                    "scene": row["scene"],
                    "count": int(row["count"] or 0),
                })

    if has_bad_cases and "created_at" in bad_cols:
        fixed_expr = (
            "SUM(CASE WHEN status = 'fixed' THEN 1 ELSE 0 END)"
            if "status" in bad_cols
            else "0"
        )

        rows = db.execute(
            text(f"""
                SELECT
                    DATE(created_at) AS day,
                    COUNT(*) AS created_count,
                    {fixed_expr} AS fixed_count
                FROM bad_cases
                WHERE created_at >= NOW() - (:days * INTERVAL '1 day')
                GROUP BY DATE(created_at)
                ORDER BY day ASC
            """),
            {"days": days},
        ).mappings().all()

        for row in rows:
            created_count = int(row["created_count"] or 0)
            fixed_count = int(row["fixed_count"] or 0)
            daily_bad_cases.append({
                "day": _jsonable(row["day"]),
                "created_count": created_count,
                "fixed_count": fixed_count,
                "fix_rate": round(fixed_count * 100 / created_count, 2) if created_count else 0.0,
            })

    return {
        "days": days,
        "daily_invocations": daily_invocations,
        "scene_daily_distribution": scene_daily_distribution,
        "daily_bad_cases": daily_bad_cases,
    }
