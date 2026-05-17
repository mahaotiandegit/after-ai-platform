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
    data = None
    headers = {"Content-Type": "application/json"}

    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        url=BASE_URL + path,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
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


def test_healthz():
    status, body = request_json("GET", "/healthz")

    if status != 200:
        fail(f"/healthz 失败，status={status}, body={body}")

    ok("/healthz 通过")


def test_knowledge_ask_with_deepseek():
    status, body = request_json(
        "POST",
        "/api/v1/knowledge/ask",
        {
            "question": "物流延迟应该怎么补偿？",
            "top_k": 5,
        },
    )

    if status != 200:
        fail(f"/api/v1/knowledge/ask 失败，status={status}, body={body}")

    required_fields = [
        "question",
        "query",
        "answer",
        "answer_summary",
        "citations",
        "hits",
        "qa_log_id",
        "provider",
        "model",
        "used_llm",
        "fallback_reason",
    ]

    for field in required_fields:
        if field not in body:
            fail(f"响应缺少字段 {field}: {body}")

    if not body["answer"]:
        fail(f"answer 为空: {body}")

    if not isinstance(body["citations"], list):
        fail(f"citations 不是 list: {body}")

    if not isinstance(body["hits"], list):
        fail(f"hits 不是 list: {body}")

    if len(body["citations"]) == 0:
        fail(f"citations 为空，RAG 没有返回引用: {body}")

    if not body["qa_log_id"]:
        fail(f"qa_log_id 为空，问答日志没有落库: {body}")

    if body["provider"] != "deepseek":
        fail(f"provider 不是 deepseek，当前为: {body['provider']}")

    if body["model"] != "deepseek-chat":
        fail(f"model 不是 deepseek-chat，当前为: {body['model']}")

    if body["used_llm"] is not True:
        fail(f"used_llm 不是 true，fallback_reason={body.get('fallback_reason')}")

    if body["fallback_reason"]:
        fail(f"fallback_reason 不为空: {body['fallback_reason']}")

    ok(
        "DeepSeek RAG 主链路通过，"
        f"provider={body['provider']}, "
        f"model={body['model']}, "
        f"citations={len(body['citations'])}, "
        f"qa_log_id={body['qa_log_id']}"
    )


def main():
    print("========== v0.6.0 DeepSeek RAG acceptance ==========")
    test_healthz()
    test_knowledge_ask_with_deepseek()
    print("========== v0.6.0 验收通过 ==========")


if __name__ == "__main__":
    main()