from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


BASE_URL = "http://127.0.0.1:8000"
QUESTION = "我的包裹三天没更新了，能不能退款或者补偿？"


def request(method: str, path: str, body: dict | None = None) -> tuple[int, dict | str]:
    data = None
    headers = {}

    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(
        BASE_URL + path,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(raw)
            except Exception:
                return resp.status, raw

    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(raw)
        except Exception:
            return exc.code, raw


def require(condition: bool, message: str, payload=None) -> None:
    if condition:
        return

    print("[FAIL]", message)

    if payload is not None:
        if isinstance(payload, dict):
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(payload)

    sys.exit(1)


def db_scalar(sql: str, params: dict | None = None):
    from sqlalchemy import text
    from app.db.session import SessionLocal

    db = SessionLocal()

    try:
        return db.execute(text(sql), params or {}).scalar_one()

    finally:
        db.close()


def db_row(sql: str, params: dict | None = None) -> dict:
    from sqlalchemy import text
    from app.db.session import SessionLocal

    db = SessionLocal()

    try:
        row = db.execute(text(sql), params or {}).mappings().first()
        return dict(row or {})

    finally:
        db.close()


def detect_order_no() -> str | None:
    from sqlalchemy import inspect, text
    from app.db.session import SessionLocal

    db = SessionLocal()

    try:
        inspector = inspect(db.get_bind())
        columns = [column["name"] for column in inspector.get_columns("orders")]

        order_no_column = None

        for candidate in ["order_no", "order_number", "order_code", "no"]:
            if candidate in columns:
                order_no_column = candidate
                break

        if order_no_column is None:
            return None

        if "created_at" in columns:
            sql = f"SELECT {order_no_column} FROM orders ORDER BY created_at DESC LIMIT 1"
        else:
            sql = f"SELECT {order_no_column} FROM orders LIMIT 1"

        value = db.execute(text(sql)).scalar_one_or_none()

        return str(value) if value is not None else None

    finally:
        db.close()


def main() -> None:
    print("========== healthz ==========")

    status, data = request("GET", "/healthz")

    print(status)
    print(data)

    require(200 <= status < 300, "/healthz failed", data)

    print("========== count audit logs before ==========")

    before = db_scalar(
        "SELECT COUNT(*) FROM ai_invocation_logs WHERE scene = :scene",
        {"scene": "ticket_ai_classifier"},
    )

    print("before =", before)

    print("========== call ticket auto-create ==========")

    payload = {
        "customer_question": QUESTION,
    }

    order_no = detect_order_no()

    if order_no:
        payload["order_no"] = order_no

    status, data = request(
        "POST",
        "/api/v1/tickets/auto-create",
        payload,
    )

    print(status)

    if isinstance(data, dict):
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(data)

    require(200 <= status < 300, "ticket auto-create failed", data)
    require(isinstance(data, dict), "response should be json object", data)

    print("========== count audit logs after ==========")

    after = db_scalar(
        "SELECT COUNT(*) FROM ai_invocation_logs WHERE scene = :scene",
        {"scene": "ticket_ai_classifier"},
    )

    print("after =", after)

    require(after > before, "ai_invocation_logs should increase after ticket classification")

    print("========== latest audit log ==========")

    latest = db_row(
        """
        SELECT
            id,
            scene,
            provider,
            model,
            success,
            latency_ms,
            input_payload,
            output_payload,
            created_at
        FROM ai_invocation_logs
        WHERE scene = :scene
        ORDER BY created_at DESC
        LIMIT 1
        """,
        {"scene": "ticket_ai_classifier"},
    )

    print(json.dumps(latest, ensure_ascii=False, indent=2, default=str))

    require(latest.get("scene") == "ticket_ai_classifier", "scene should be ticket_ai_classifier", latest)
    require(latest.get("provider") == "local-template", "provider should be local-template", latest)
    require(latest.get("success") is True, "success should be true", latest)
    require(latest.get("latency_ms") is not None, "latency_ms should not be null", latest)

    output_payload = latest.get("output_payload") or {}

    if isinstance(output_payload, str):
        output_payload = json.loads(output_payload)

    require(
        output_payload.get("category") == "logistics_delay_refund",
        "audit output_payload.category should be logistics_delay_refund",
        latest,
    )

    require(
        output_payload.get("priority") == "high",
        "audit output_payload.priority should be high",
        latest,
    )

    print("========== PASS: ai audit log acceptance ==========")


if __name__ == "__main__":
    main()
