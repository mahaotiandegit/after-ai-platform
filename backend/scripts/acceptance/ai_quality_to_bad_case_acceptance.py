import json
import sys
import urllib.error
import urllib.parse
import urllib.request


def request_json(url: str, method: str = "GET"):
    req = urllib.request.Request(url, method=method)

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        print("[FAIL] HTTP error:", method, url, e.code)
        print(e.read().decode("utf-8", errors="replace"))
        sys.exit(1)
    except Exception as e:
        print("[FAIL] request failed:", method, url, repr(e))
        sys.exit(1)

    if status < 200 or status >= 300:
        print("[FAIL] unexpected status:", status)
        print(body)
        sys.exit(1)

    try:
        return json.loads(body)
    except Exception as e:
        print("[FAIL] invalid json:", repr(e))
        print(body)
        sys.exit(1)


# 确保评估结果存在，并强制重评估一次
request_json(
    "http://127.0.0.1:8000/api/v1/ai-quality/evaluations/run-recent?limit=100&force=true",
    method="POST",
)

auto_data = request_json(
    "http://127.0.0.1:8000/api/v1/ai-quality/evaluations/auto-create-bad-cases?score_lte=60&limit=10",
    method="POST",
)

for key in ["score_lte", "limit", "matched_count", "created_count", "skipped_count", "items"]:
    if key not in auto_data:
        print("[FAIL] auto-create missing key:", key)
        print(json.dumps(auto_data, ensure_ascii=False, indent=2))
        sys.exit(1)

if not isinstance(auto_data["items"], list):
    print("[FAIL] auto-create items should be list")
    sys.exit(1)

if auto_data["items"]:
    row = auto_data["items"][0]
    for key in ["action", "evaluation_id", "bad_case"]:
        if key not in row:
            print("[FAIL] auto-create item missing key:", key)
            print(json.dumps(row, ensure_ascii=False, indent=2))
            sys.exit(1)

    if row["action"] not in ["created", "skipped"]:
        print("[FAIL] invalid action:", row["action"])
        sys.exit(1)

# 单条转换接口：只选 fail 评估；没有 fail 就跳过，不拿 pass 数据硬转
eval_list = request_json(
    "http://127.0.0.1:8000/api/v1/ai-quality/evaluations?status=fail&limit=1",
    method="GET",
)

if eval_list.get("items"):
    evaluation_id = urllib.parse.quote(eval_list["items"][0]["id"])
    single_data = request_json(
        f"http://127.0.0.1:8000/api/v1/ai-quality/evaluations/{evaluation_id}/to-bad-case",
        method="POST",
    )

    if single_data.get("action") not in ["created", "skipped", "not_found"]:
        print("[FAIL] single conversion invalid action")
        print(json.dumps(single_data, ensure_ascii=False, indent=2))
        sys.exit(1)
else:
    single_data = {
        "action": "skipped",
        "reason": "no fail evaluation exists",
    }

print("[PASS] AI Quality to Bad Case API accepted")
print(json.dumps({
    "auto_create": auto_data,
    "single": single_data,
}, ensure_ascii=False, indent=2))
