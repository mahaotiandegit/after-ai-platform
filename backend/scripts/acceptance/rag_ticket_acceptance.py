#!/usr/bin/env python3
import json
import sys
import urllib.error
import urllib.request


BASE_URL = "http://127.0.0.1:8000"

RAG_QUESTION = "物流延迟应该怎么补偿？"
COMBO_QUESTION = "我的包裹三天没更新了，能不能退款或者补偿？"
ORDER_ID = "22222222-2222-2222-2222-222222222201"


def fail(message: str):
    print(f"[FAIL] {message}")
    sys.exit(1)


def ok(message: str):
    print(f"[PASS] {message}")


def request_json(method: str, path: str, body=None):
    url = BASE_URL + path

    data = None
    headers = {
        "Content-Type": "application/json",
    }

    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        url=url,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            text = resp.read().decode("utf-8")
            if text:
                return resp.status, json.loads(text)
            return resp.status, None

    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(text)
        except Exception:
            return e.code, text

    except Exception as e:
        return 0, str(e)


def test_healthz():
    status, body = request_json("GET", "/healthz")

    if status != 200:
        fail(f"/healthz 不通，status={status}, body={body}")

    ok("/healthz 通过")


def test_rag_ask():
    status, body = request_json(
        "POST",
        "/api/v1/knowledge/ask",
        {
            "question": RAG_QUESTION,
            "top_k": 5,
        },
    )

    if status != 200:
        fail(f"RAG 接口失败，status={status}, body={body}")

    if not isinstance(body, dict):
        fail(f"RAG 返回不是 JSON 对象：{body}")

    answer = body.get("answer")
    qa_log_id = body.get("qa_log_id")
    citations = body.get("citations") or []
    hits = body.get("hits") or []

    if not answer:
        fail(f"RAG answer 为空：{body}")

    if not qa_log_id:
        fail(f"RAG qa_log_id 为空，说明 qa_logs 没写入：{body}")

    if not citations and not hits:
        fail(f"RAG citations 和 hits 都为空：{body}")

    ok(f"RAG 问答通过，qa_log_id={qa_log_id}")


def find_ticket_object(obj):
    if isinstance(obj, dict):
        text = json.dumps(obj, ensure_ascii=False)

        if "logistics_delay_refund" in text:
            return obj

        for value in obj.values():
            found = find_ticket_object(value)
            if found:
                return found

    if isinstance(obj, list):
        for item in obj:
            found = find_ticket_object(item)
            if found:
                return found

    return None


def test_combo_ticket():
    candidate_paths = [
        "/api/v1/tickets/auto-create",
        "/api/v1/tickets/create",
        "/api/v1/tickets",
    ]

    candidate_payloads = [
        {
            "order_id": ORDER_ID,
            "customer_question": COMBO_QUESTION,
        },
        {
            "order_id": ORDER_ID,
            "question": COMBO_QUESTION,
        },
        {
            "customer_question": COMBO_QUESTION,
        },
        {
            "question": COMBO_QUESTION,
        },
    ]

    errors = []

    for path in candidate_paths:
        for payload in candidate_payloads:
            status, body = request_json("POST", path, payload)

            if status not in (200, 201):
                errors.append(
                    {
                        "path": path,
                        "payload": payload,
                        "status": status,
                        "body": body,
                    }
                )
                continue

            ticket = find_ticket_object(body)

            if not ticket:
                errors.append(
                    {
                        "path": path,
                        "payload": payload,
                        "status": status,
                        "reason": "响应里没有找到 logistics_delay_refund",
                        "body": body,
                    }
                )
                continue

            text = json.dumps(ticket, ensure_ascii=False)

            if "logistics_delay_refund" not in text:
                fail(f"组合意图分类错误，响应={body}")

            if "high" not in text:
                fail(f"组合意图 priority 不是 high，响应={body}")

            if "物流延迟退款补偿处理" not in text and "物流" not in text:
                fail(f"组合意图标题/摘要不合理，响应={body}")

            ok(f"组合意图工单通过，path={path}")
            return

    print("========== 调试信息：最近失败记录 ==========")
    for error in errors[-5:]:
        print(json.dumps(error, ensure_ascii=False, indent=2))

    fail("组合意图工单验收失败，请检查工单创建接口路径或字段名")


def main():
    print("========== after-ai-platform 验收开始 ==========")

    test_healthz()
    test_rag_ask()
    test_combo_ticket()

    print("========== 全部验收通过 ==========")


if __name__ == "__main__":
    main()