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
        with urllib.request.urlopen(req, timeout=15) as resp:
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


def test_ask_llm():
    status, body = request_json(
        "POST",
        "/api/v1/knowledge/ask-llm",
        {
            "question": "物流延迟应该怎么补偿？",
            "top_k": 5,
        },
    )

    if status != 200:
        fail(f"/knowledge/ask-llm 失败，status={status}, body={body}")

    required = [
        "question",
        "answer",
        "citations",
        "hits",
        "provider",
        "model",
        "used_llm",
        "qa_log_id",
    ]

    for key in required:
        if key not in body:
            fail(f"缺少字段 {key}: {body}")

    if not body["answer"]:
        fail(f"answer 为空: {body}")

    if body["provider"] not in {"local", "openai", "deepseek", "openai-compatible"}:
        fail(f"provider 非法: {body}")

    if not isinstance(body["hits"], list):
        fail(f"hits 不是 list: {body}")

    if not isinstance(body["citations"], list):
        fail(f"citations 不是 list: {body}")

    ok(f"LLM RAG 接口通过，provider={body['provider']}, model={body['model']}, hits={len(body['hits'])}")


def main():
    print("========== llm gateway acceptance ==========")
    test_healthz()
    test_ask_llm()
    print("========== 全部通过 ==========")


if __name__ == "__main__":
    main()
