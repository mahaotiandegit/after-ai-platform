from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
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


def call_for_fresh_logs() -> None:
    request(
        "POST",
        "/api/v1/knowledge/ask-llm",
        {
            "question": "物流延迟应该怎么补偿？",
            "top_k": 3,
        },
    )

    request(
        "POST",
        "/api/v1/analytics/ask",
        {
            "question": "最近7天物流延迟类工单有多少？",
        },
    )


def main() -> None:
    print("========== healthz ==========")

    status, data = request("GET", "/healthz")
    print(status)
    print(data)

    require(200 <= status < 300, "/healthz failed", data)

    print("========== create fresh RAG + NL2SQL logs ==========")

    call_for_fresh_logs()

    print("========== query all logs ==========")

    status, data = request("GET", "/api/v1/ai-audit/logs?limit=10")

    print(status)
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str) if isinstance(data, dict) else data)

    require(200 <= status < 300, "list ai audit logs failed", data)
    require(isinstance(data, dict), "logs response should be json object", data)
    require("total" in data and "items" in data, "logs response should contain total/items", data)
    require(data["total"] >= 1, "logs total should be >= 1", data)
    require(len(data["items"]) >= 1, "logs items should not be empty", data)

    first = data["items"][0]

    for field in [
        "id",
        "scene",
        "provider",
        "model",
        "success",
        "latency_ms",
        "created_at",
    ]:
        require(field in first, f"log item missing field: {field}", first)

    print("========== query rag_ask_llm logs ==========")

    params = urllib.parse.urlencode(
        {
            "scene": "rag_ask_llm",
            "limit": 5,
        }
    )

    status, data = request("GET", f"/api/v1/ai-audit/logs?{params}")

    print(status)
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str) if isinstance(data, dict) else data)

    require(200 <= status < 300, "list rag_ask_llm logs failed", data)
    require(data["total"] >= 1, "rag_ask_llm logs should exist", data)
    require(data["items"][0]["scene"] == "rag_ask_llm", "filtered scene should be rag_ask_llm", data)

    print("========== query analytics_nl2sql logs ==========")

    params = urllib.parse.urlencode(
        {
            "scene": "analytics_nl2sql",
            "limit": 5,
        }
    )

    status, data = request("GET", f"/api/v1/ai-audit/logs?{params}")

    print(status)
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str) if isinstance(data, dict) else data)

    require(200 <= status < 300, "list analytics_nl2sql logs failed", data)
    require(data["total"] >= 1, "analytics_nl2sql logs should exist", data)
    require(data["items"][0]["scene"] == "analytics_nl2sql", "filtered scene should be analytics_nl2sql", data)

    print("========== query summary ==========")

    status, data = request("GET", "/api/v1/ai-audit/summary?days=7")

    print(status)
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str) if isinstance(data, dict) else data)

    require(200 <= status < 300, "summary failed", data)
    require(isinstance(data, dict), "summary response should be json object", data)
    require("items" in data, "summary should contain items", data)

    scenes = {
        item.get("scene")
        for item in data.get("items", [])
    }

    require("rag_ask_llm" in scenes, "summary should contain rag_ask_llm", data)
    require("analytics_nl2sql" in scenes, "summary should contain analytics_nl2sql", data)

    print("========== PASS: ai audit query acceptance ==========")


if __name__ == "__main__":
    main()
