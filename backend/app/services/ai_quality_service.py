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
