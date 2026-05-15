#!/usr/bin/env python3
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
    url = BASE_URL + path

    data = None
    headers = {"Content-Type": "application/json"}

    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        url=url,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode("utf-8")
            return resp.status, json.loads(text) if text else None
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(text)
        except Exception:
            return e.code, text
    except Exception as e:
        return 0, str(e)


def assert_analytics_response(body, expected_intent: str):
    if not isinstance(body, dict):
        fail(f"响应不是 JSON object: {body}")

    required = ["question", "intent", "sql", "columns", "rows", "summary"]
    for key in required:
        if key not in body:
            fail(f"缺少字段 {key}: {body}")

    if body["intent"] != expected_intent:
        fail(f"intent 错误，expected={expected_intent}, actual={body['intent']}, body={body}")

    sql = body["sql"].strip().lower()
    if not sql.startswith("select"):
        fail(f"SQL 不是 SELECT: {body['sql']}")

    if ";" in sql:
        fail(f"SQL 不允许包含分号: {body['sql']}")

    if not isinstance(body["columns"], list):
        fail(f"columns 不是 list: {body}")

    if not isinstance(body["rows"], list):
        fail(f"rows 不是 list: {body}")

    if not body["summary"]:
        fail(f"summary 为空: {body}")


def test_healthz():
    status, body = request_json("GET", "/healthz")
    if status != 200:
        fail(f"/healthz 失败，status={status}, body={body}")
    ok("/healthz 通过")


def test_overview_still_works():
    status, body = request_json("GET", "/api/v1/analytics/overview")
    if status != 200:
        fail(f"/api/v1/analytics/overview 被破坏，status={status}, body={body}")
    ok("/analytics/overview 通过")


def test_logistics_count():
    status, body = request_json(
        "POST",
        "/api/v1/analytics/ask",
        {
            "question": "最近7天物流延迟类工单有多少？",
            "limit": 20,
        },
    )

    if status != 200:
        fail(f"物流延迟问数失败，status={status}, body={body}")

    assert_analytics_response(body, "logistics_delay_ticket_count")
    ok("物流延迟工单数量问数通过")


def test_category_distribution():
    status, body = request_json(
        "POST",
        "/api/v1/analytics/ask",
        {
            "question": "最近7天售后问题类型分布怎么样？",
            "limit": 20,
        },
    )

    if status != 200:
        fail(f"工单类型分布问数失败，status={status}, body={body}")

    assert_analytics_response(body, "ticket_category_distribution")
    ok("工单类型分布问数通过")


def test_priority_distribution():
    status, body = request_json(
        "POST",
        "/api/v1/analytics/ask",
        {
            "question": "最近7天高优先级工单多吗？按优先级统计一下",
            "limit": 20,
        },
    )

    if status != 200:
        fail(f"优先级分布问数失败，status={status}, body={body}")

    assert_analytics_response(body, "ticket_priority_distribution")
    ok("工单优先级分布问数通过")


def main():
    print("========== analytics ask acceptance ==========")
    test_healthz()
    test_overview_still_works()
    test_logistics_count()
    test_category_distribution()
    test_priority_distribution()
    print("========== 全部通过 ==========")


if __name__ == "__main__":
    main()
