from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


BASE_URL = "http://127.0.0.1:8000"
QUESTION = "我的包裹三天没更新了，能不能退款或者补偿？"


def request(
    method: str,
    path: str,
    body: dict | None = None,
) -> tuple[int, dict | str]:
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


def require(
    condition: bool,
    message: str,
    payload=None,
) -> None:
    if condition:
        return

    print("[FAIL]", message)

    if payload is not None:
        if isinstance(payload, dict):
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(payload)

    sys.exit(1)


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

    print("========== ticket ai create ==========")

    payload = {
        "customer_question": QUESTION,
    }

    status, data = request(
        "POST",
        "/api/v1/tickets/ai-create",
        payload,
    )

    print(status)

    if isinstance(data, dict):
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(data)

    require(
        200 <= status < 300,
        "ticket ai create failed",
        data,
    )

    require(
        isinstance(data, dict),
        "response is not json object",
        data,
    )

    category = data.get("category")
    priority = data.get("priority")
    title = str(data.get("title") or "")

    require(
        category == "logistics_delay_refund",
        "category should remain logistics_delay_refund",
        data,
    )

    require(
        priority == "high",
        "priority should remain high",
        data,
    )

    require(
        "物流延迟退款补偿处理" in title
        or ("物流" in title and ("退款" in title or "补偿" in title)),
        "title should preserve logistics delay refund meaning",
        data,
    )

    required_ai_fields = [
        "llm_provider",
        "llm_model",
        "used_llm",
        "classification_source",
        "recommended_action",
    ]

    for field in required_ai_fields:
        require(
            field in data,
            f"missing AI classifier field: {field}",
            data,
        )

    classification_source = str(data.get("classification_source") or "")
    llm_provider = str(data.get("llm_provider") or "")

    require(
        "llm_gateway" in classification_source or bool(llm_provider),
        "response should show LLM Gateway / AI classifier source",
        data,
    )

    print("========== PASS: ticket ai classifier v1 acceptance ==========")


if __name__ == "__main__":
    main()