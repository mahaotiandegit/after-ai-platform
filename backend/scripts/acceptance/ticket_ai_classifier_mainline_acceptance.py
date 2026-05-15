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


def detect_order_no() -> str | None:
    try:
        from sqlalchemy import inspect, text
        from app.db.deps import get_db

        db_gen = get_db()
        db = next(db_gen)

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

    except Exception as exc:
        print(f"[WARN] detect_order_no failed: {type(exc).__name__}: {exc}")
        return None


def main() -> None:
    print("========== healthz ==========")

    status, data = request("GET", "/healthz")

    print(status)
    print(data)

    require(
        200 <= status < 300,
        "/healthz failed",
        data,
    )

    print("========== detect seed order_no ==========")

    order_no = detect_order_no()

    print("order_no =", order_no)

    payload = {
        "customer_question": QUESTION,
    }

    if order_no:
        payload["order_no"] = order_no

    print("========== original /tickets/auto-create mainline ==========")

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

    require(
        200 <= status < 300,
        "ticket auto-create failed",
        data,
    )

    require(
        isinstance(data, dict),
        "response is not json object",
        data,
    )

    ticket = data.get("ticket")

    require(
        isinstance(ticket, dict),
        "response.ticket should be json object",
        data,
    )

    require(
        ticket.get("category") == "logistics_delay_refund",
        "ticket.category should remain logistics_delay_refund",
        data,
    )

    require(
        ticket.get("priority") == "high",
        "ticket.priority should remain high",
        data,
    )

    title = str(ticket.get("title") or "")

    require(
        "物流延迟退款补偿处理" in title
        or ("物流" in title and ("退款" in title or "补偿" in title)),
        "ticket.title should preserve logistics delay refund meaning",
        data,
    )

    for field in [
        "llm_provider",
        "llm_model",
        "used_llm",
        "classification_source",
        "recommended_action",
    ]:
        require(
            field in data,
            f"missing AI classifier field in original auto-create response: {field}",
            data,
        )

    require(
        data.get("llm_provider") == "local-template",
        "llm_provider should be local-template",
        data,
    )

    require(
        data.get("used_llm") is True,
        "used_llm should be true",
        data,
    )

    source = str(data.get("classification_source") or "")

    require(
        "llm_gateway" in source,
        "classification_source should show llm_gateway",
        data,
    )

    recommended_action = str(data.get("recommended_action") or "")

    require(
        "物流" in recommended_action and ("补偿" in recommended_action or "退款" in recommended_action),
        "recommended_action should match logistics delay refund scenario",
        data,
    )

    print("========== PASS: ticket ai classifier mainline acceptance ==========")


if __name__ == "__main__":
    main()
