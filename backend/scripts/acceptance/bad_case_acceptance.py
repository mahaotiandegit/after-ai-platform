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


def call_for_fresh_ai_log() -> None:
    status, data = request(
        "POST",
        "/api/v1/knowledge/ask-llm",
        {
            "question": "物流延迟应该怎么补偿？",
            "top_k": 3,
        },
    )

    require(200 <= status < 300, "failed to create fresh rag ai log", data)


def latest_ai_log_id(scene: str) -> str:
    from sqlalchemy import text
    from app.db.session import SessionLocal

    db = SessionLocal()

    try:
        row = db.execute(
            text(
                """
                SELECT id
                FROM ai_invocation_logs
                WHERE scene = :scene
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {
                "scene": scene,
            },
        ).mappings().first()

        require(row is not None, f"missing ai log for scene={scene}")

        return str(row["id"])

    finally:
        db.close()


def main() -> None:
    print("========== healthz ==========")

    status, data = request("GET", "/healthz")

    print(status)
    print(data)

    require(200 <= status < 300, "/healthz failed", data)

    print("========== create fresh ai log ==========")

    call_for_fresh_ai_log()

    ai_log_id = latest_ai_log_id("rag_ask_llm")

    print("ai_log_id =", ai_log_id)

    print("========== create bad case from ai log ==========")

    status, data = request(
        "POST",
        "/api/v1/bad-cases/from-ai-log",
        {
            "ai_log_id": ai_log_id,
            "correction": "补偿规则需要同时提示排除条件，并建议客服核实订单与物流状态。",
            "root_cause": "回答虽然命中知识片段，但处理建议不够结构化。",
            "priority": "high",
            "tags": [
                "rag",
                "logistics_delay",
                "answer_quality",
            ],
        },
    )

    print(status)
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str) if isinstance(data, dict) else data)

    require(200 <= status < 300, "create bad case failed", data)
    require(isinstance(data, dict), "bad case response should be json object", data)
    require(data.get("source_type") == "ai_invocation_log", "source_type should be ai_invocation_log", data)
    require(data.get("source_id") == ai_log_id, "source_id should match ai_log_id", data)
    require(data.get("scene") == "rag_ask_llm", "scene should be rag_ask_llm", data)
    require(data.get("priority") == "high", "priority should be high", data)
    require(data.get("status") == "open", "status should be open", data)

    bad_case_id = data["id"]

    print("========== list bad cases ==========")

    status, data = request(
        "GET",
        "/api/v1/bad-cases?scene=rag_ask_llm&status=open&limit=10",
    )

    print(status)
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str) if isinstance(data, dict) else data)

    require(200 <= status < 300, "list bad cases failed", data)
    require(isinstance(data, dict), "bad case list response should be json object", data)
    require(data.get("total", 0) >= 1, "bad case total should be >= 1", data)

    ids = {
        item.get("id")
        for item in data.get("items", [])
    }

    require(bad_case_id in ids, "created bad case should appear in list", data)

    print("========== update bad case status ==========")

    status, data = request(
        "PATCH",
        f"/api/v1/bad-cases/{bad_case_id}/status",
        {
            "status": "fixed",
            "root_cause": "RAG 回答缺少结构化 SOP 提示。",
            "correction": "后续 prompt 应强制返回：适用条件、排除条件、处理动作、升级条件。",
        },
    )

    print(status)
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str) if isinstance(data, dict) else data)

    require(200 <= status < 300, "update bad case status failed", data)
    require(data.get("id") == bad_case_id, "updated bad case id mismatch", data)
    require(data.get("status") == "fixed", "bad case status should be fixed", data)

    correction = str(data.get("correction") or "")

    require(
        "适用条件" in correction
        and "排除条件" in correction
        and "处理动作" in correction
        and "升级条件" in correction,
        "correction should be updated",
        data,
    )

    print("========== PASS: bad case acceptance ==========")


if __name__ == "__main__":
    main()
