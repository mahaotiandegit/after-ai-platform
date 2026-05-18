#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from sqlalchemy import create_engine, text


BACKEND_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.nl2sql_safety import Nl2sqlSafetyError, validate_select_sql  # noqa: E402


BASE_URL = os.getenv("ACCEPTANCE_BASE_URL", "http://127.0.0.1:8000")


def database_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql://after_ai:after_ai_password@localhost:5432/after_ai_platform",
    )


def fail(message: str):
    print(f"[FAIL] {message}")
    sys.exit(1)


def ok(message: str):
    print(f"[PASS] {message}")


def request_json(method: str, path: str, body=None):
    data = None
    headers = {"Content-Type": "application/json"}

    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        BASE_URL + path,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            text_body = resp.read().decode("utf-8")
            return resp.status, json.loads(text_body) if text_body else None
    except urllib.error.HTTPError as e:
        text_body = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(text_body)
        except Exception:
            return e.code, text_body
    except Exception as e:
        return 0, str(e)


def test_healthz():
    status, body = request_json("GET", "/healthz")
    if status != 200:
        fail(f"/healthz failed, status={status}, body={body}")

    ok("/healthz")


def test_safety_guard_allows_safe_select():
    safe = validate_select_sql(
        """
        SELECT
            category,
            COUNT(*) AS ticket_count
        FROM tickets
        GROUP BY category
        ORDER BY ticket_count DESC
        """,
        row_limit=20,
    )

    if "LIMIT :__safe_limit" not in safe.sql:
        fail(f"safe sql should append limit: {safe.sql}")

    if "tickets" not in safe.tables_used:
        fail(f"tables_used should include tickets: {safe.tables_used}")

    ok("safe SELECT allowed and LIMIT enforced")


def test_safety_guard_blocks_dangerous_sql():
    dangerous_sqls = [
        "DELETE FROM tickets",
        "UPDATE tickets SET status='closed'",
        "DROP TABLE tickets",
        "ALTER TABLE tickets ADD COLUMN hacked TEXT",
        "TRUNCATE TABLE tickets",
        "SELECT * FROM tickets; DROP TABLE tickets",
        "SELECT * FROM users",
        "SELECT pg_sleep(10)",
        "SELECT * FROM pg_catalog.pg_tables",
        "SELECT * FROM information_schema.tables",
        "SELECT * FROM tickets -- comment",
    ]

    for sql in dangerous_sqls:
        try:
            validate_select_sql(sql)
        except Nl2sqlSafetyError:
            continue
        except Exception as exc:
            fail(f"unexpected exception type for {sql}: {type(exc).__name__}: {exc}")

        fail(f"dangerous sql was not blocked: {sql}")

    ok("dangerous SQL blocked")


def test_analytics_api_and_log():
    status, body = request_json(
        "POST",
        "/api/v1/analytics/ask",
        {
            "question": "最近 7 天工单按类型分布",
            "limit": 20,
        },
    )

    if status != 200:
        fail(f"/api/v1/analytics/ask failed, status={status}, body={body}")

    required = [
        "question",
        "intent",
        "sql",
        "columns",
        "rows",
        "summary",
        "safe",
        "tables_used",
        "applied_limit",
        "query_log_id",
    ]

    for field in required:
        if field not in body:
            fail(f"analytics response missing {field}: {body}")

    if body["safe"] is not True:
        fail(f"safe should be true: {body}")

    if not body["query_log_id"]:
        fail(f"query_log_id empty: {body}")

    if "tickets" not in body["tables_used"]:
        fail(f"tables_used should include tickets: {body}")

    engine = create_engine(database_url())

    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT id, status, question, row_count
                FROM analytics_query_logs
                WHERE id = :id
                """
            ),
            {
                "id": body["query_log_id"],
            },
        ).mappings().first()

    if not row:
        fail(f"analytics_query_logs missing id={body['query_log_id']}")

    if row["status"] != "success":
        fail(f"query log status should be success: {dict(row)}")

    ok(
        "analytics API safe query and log passed, "
        f"log_id={body['query_log_id']}, rows={len(body['rows'])}"
    )


def test_log_table_exists():
    engine = create_engine(database_url())

    with engine.begin() as conn:
        exists = conn.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_name = 'analytics_query_logs'
                )
                """
            )
        ).scalar()

        if not exists:
            fail("analytics_query_logs table not found")

        count = conn.execute(
            text("SELECT count(*) FROM analytics_query_logs")
        ).scalar()

    ok(f"analytics_query_logs exists, count={count}")


def main():
    print("========== v0.8.5 NL2SQL safety acceptance ==========")
    test_healthz()
    test_log_table_exists()
    test_safety_guard_allows_safe_select()
    test_safety_guard_blocks_dangerous_sql()
    test_analytics_api_and_log()
    print("========== v0.8.5 验收通过 ==========")


if __name__ == "__main__":
    main()