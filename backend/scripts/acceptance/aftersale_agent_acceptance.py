#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


BASE_URL = "http://127.0.0.1:8000"


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
        with urllib.request.urlopen(req, timeout=60) as resp:
            text = resp.read().decode("utf-8")
            return resp.status, json.loads(text) if text else None
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(text)
        except Exception:
            return exc.code, text
    except Exception as exc:
        return 0, str(exc)


def test_healthz():
    status, body = request_json("GET", "/healthz")
    if status != 200:
        fail(f"/healthz failed: status={status}, body={body}")
    ok("/healthz")


def test_agent_without_ticket_creation():
    status, body = request_json(
        "POST",
        "/api/v1/agent/aftersale",
        {
            "question": "用户说包裹三天没更新，想要补偿，客服应该怎么处理？",
            "order_no": "ORDER-20260515-0001",
            "top_k": 5,
            "auto_create_ticket": False,
            "include_analytics": False,
        },
    )

    if status != 200:
        fail(f"agent without ticket failed: status={status}, body={body}")

    required = [
        "question",
        "route_intents",
        "final_answer",
        "action_plan",
        "risk_flags",
        "tool_calls",
        "used_llm",
        "provider",
        "model",
    ]

    for field in required:
        if field not in body:
            fail(f"agent response missing {field}: {body}")

    tool_names = [item.get("tool_name") for item in body["tool_calls"]]

    if "knowledge_rag" not in tool_names:
        fail(f"knowledge_rag not called: {tool_names}")

    if "order_context" not in tool_names:
        fail(f"order_context not called: {tool_names}")

    if "ticket_auto_create" in tool_names:
        fail(f"ticket_auto_create should not be called when auto_create_ticket=false: {tool_names}")

    if not body["final_answer"]:
        fail(f"final_answer empty: {body}")

    if not body["action_plan"]:
        fail(f"action_plan empty: {body}")

    ok(
        "agent without ticket creation passed, "
        f"tools={tool_names}, provider={body.get('provider')}"
    )


def test_agent_with_analytics():
    status, body = request_json(
        "POST",
        "/api/v1/agent/aftersale",
        {
            "question": "最近7天物流相关工单有多少？",
            "top_k": 5,
            "auto_create_ticket": False,
            "include_analytics": True,
        },
    )

    if status != 200:
        fail(f"agent analytics failed: status={status}, body={body}")

    tool_names = [item.get("tool_name") for item in body["tool_calls"]]

    if "analytics_nl2sql" not in tool_names:
        fail(f"analytics_nl2sql not called: {tool_names}")

    if not body["final_answer"]:
        fail(f"final_answer empty in analytics test: {body}")

    ok(f"agent analytics passed, tools={tool_names}")


def test_agent_with_ticket_creation():
    status, body = request_json(
        "POST",
        "/api/v1/agent/aftersale",
        {
            "question": "用户投诉包裹三天没更新，要求退款和补偿，请创建工单。",
            "order_no": "ORDER-20260515-0001",
            "top_k": 5,
            "auto_create_ticket": True,
            "include_analytics": False,
        },
    )

    if status != 200:
        fail(f"agent ticket creation failed: status={status}, body={body}")

    tool_names = [item.get("tool_name") for item in body["tool_calls"]]

    if "ticket_auto_create" not in tool_names:
        fail(f"ticket_auto_create not called: {tool_names}")

    if not body.get("created_ticket_no"):
        fail(f"created_ticket_no empty: {body}")

    ok(
        "agent ticket creation passed, "
        f"ticket_no={body.get('created_ticket_no')}, tools={tool_names}"
    )


def main():
    print("========== v0.8.0 aftersale agent acceptance ==========")
    test_healthz()
    test_agent_without_ticket_creation()
    test_agent_with_analytics()
    test_agent_with_ticket_creation()
    print("========== v0.8.0 验收通过 ==========")


if __name__ == "__main__":
    main()