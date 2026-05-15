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
        with urllib.request.urlopen(req, timeout=20) as resp:
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
            print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
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


def latest_log(scene: str) -> dict:
    return db_row(
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
            error_message,
            created_at
        FROM ai_invocation_logs
        WHERE scene = :scene
        ORDER BY created_at DESC
        LIMIT 1
        """,
        {"scene": scene},
    )


def count_logs(scene: str) -> int:
    return db_scalar(
        "SELECT COUNT(*) FROM ai_invocation_logs WHERE scene = :scene",
        {"scene": scene},
    )


def run_rag_ask_llm_acceptance() -> None:
    scene = "rag_ask_llm"

    print("========== RAG LLM audit: before ==========")
    before = count_logs(scene)
    print("before =", before)

    print("========== call /api/v1/knowledge/ask-llm ==========")

    status, data = request(
        "POST",
        "/api/v1/knowledge/ask-llm",
        {
            "question": "物流延迟应该怎么补偿？",
            "top_k": 3,
        },
    )

    print(status)
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str) if isinstance(data, dict) else data)

    require(200 <= status < 300, "knowledge ask-llm failed", data)
    require(isinstance(data, dict), "knowledge ask-llm response should be json object", data)
    require("answer" in data, "knowledge ask-llm response should contain answer", data)
    require("qa_log_id" in data, "knowledge ask-llm response should contain qa_log_id", data)

    print("========== RAG LLM audit: after ==========")
    after = count_logs(scene)
    print("after =", after)

    require(after > before, "rag_ask_llm audit count should increase", {"before": before, "after": after})

    latest = latest_log(scene)

    print("========== latest rag_ask_llm audit log ==========")
    print(json.dumps(latest, ensure_ascii=False, indent=2, default=str))

    require(latest.get("scene") == scene, "latest scene should be rag_ask_llm", latest)
    require(latest.get("success") is True, "rag_ask_llm success should be true", latest)
    require(latest.get("latency_ms") is not None, "rag_ask_llm latency_ms should not be null", latest)

    output_payload = latest.get("output_payload") or {}

    if isinstance(output_payload, str):
        output_payload = json.loads(output_payload)

    body = output_payload.get("body", {})

    require("answer" in body, "rag audit output body should contain answer", latest)
    require("qa_log_id" in body, "rag audit output body should contain qa_log_id", latest)


def run_analytics_nl2sql_acceptance() -> None:
    scene = "analytics_nl2sql"

    print("========== Analytics NL2SQL audit: before ==========")
    before = count_logs(scene)
    print("before =", before)

    print("========== call /api/v1/analytics/ask ==========")

    status, data = request(
        "POST",
        "/api/v1/analytics/ask",
        {
            "question": "最近7天物流延迟类工单有多少？",
        },
    )

    print(status)
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str) if isinstance(data, dict) else data)

    require(200 <= status < 300, "analytics ask failed", data)
    require(isinstance(data, dict), "analytics ask response should be json object", data)
    require("question" in data, "analytics ask response should contain question", data)
    require("sql" in data, "analytics ask response should contain sql", data)
    require("summary" in data, "analytics ask response should contain summary", data)

    print("========== Analytics NL2SQL audit: after ==========")
    after = count_logs(scene)
    print("after =", after)

    require(after > before, "analytics_nl2sql audit count should increase", {"before": before, "after": after})

    latest = latest_log(scene)

    print("========== latest analytics_nl2sql audit log ==========")
    print(json.dumps(latest, ensure_ascii=False, indent=2, default=str))

    require(latest.get("scene") == scene, "latest scene should be analytics_nl2sql", latest)
    require(latest.get("provider") == "local-nl2sql", "analytics provider should be local-nl2sql", latest)
    require(latest.get("model") == "analytics-nl2sql-v1", "analytics model should be analytics-nl2sql-v1", latest)
    require(latest.get("success") is True, "analytics_nl2sql success should be true", latest)
    require(latest.get("latency_ms") is not None, "analytics_nl2sql latency_ms should not be null", latest)

    output_payload = latest.get("output_payload") or {}

    if isinstance(output_payload, str):
        output_payload = json.loads(output_payload)

    body = output_payload.get("body", {})

    require("sql" in body, "analytics audit output body should contain sql", latest)
    require("summary" in body, "analytics audit output body should contain summary", latest)


def main() -> None:
    print("========== healthz ==========")

    status, data = request("GET", "/healthz")

    print(status)
    print(data)

    require(200 <= status < 300, "/healthz failed", data)

    run_rag_ask_llm_acceptance()
    run_analytics_nl2sql_acceptance()

    print("========== PASS: ai audit log all mainlines acceptance ==========")


if __name__ == "__main__":
    main()
