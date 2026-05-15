import json
import sys
import urllib.error
import urllib.request


def request_json(url: str, method: str = "GET"):
    req = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
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


run_data = request_json(
    "http://127.0.0.1:8000/api/v1/ai-quality/evaluations/run-recent?limit=20",
    method="POST",
)

for key in ["requested_limit", "evaluated_count", "items"]:
    if key not in run_data:
        print("[FAIL] run-recent missing key:", key)
        print(json.dumps(run_data, ensure_ascii=False, indent=2))
        sys.exit(1)

list_data = request_json(
    "http://127.0.0.1:8000/api/v1/ai-quality/evaluations?limit=20",
    method="GET",
)

for key in ["total", "items"]:
    if key not in list_data:
        print("[FAIL] evaluations list missing key:", key)
        print(json.dumps(list_data, ensure_ascii=False, indent=2))
        sys.exit(1)

if not isinstance(list_data["items"], list):
    print("[FAIL] items should be list")
    sys.exit(1)

if list_data["items"]:
    row = list_data["items"][0]
    required_row_keys = [
        "id",
        "ai_log_id",
        "scene",
        "score",
        "status",
        "issues",
        "suggestions",
        "created_at",
    ]
    for key in required_row_keys:
        if key not in row:
            print("[FAIL] evaluation row missing key:", key)
            print(json.dumps(row, ensure_ascii=False, indent=2))
            sys.exit(1)

    if row["status"] not in ["pass", "warn", "fail"]:
        print("[FAIL] invalid evaluation status:", row["status"])
        sys.exit(1)

    if not isinstance(row["issues"], list):
        print("[FAIL] issues should be list")
        sys.exit(1)

    if not isinstance(row["suggestions"], list):
        print("[FAIL] suggestions should be list")
        sys.exit(1)

print("[PASS] AI Quality Evaluations API accepted")
print(json.dumps({
    "run_recent": run_data,
    "evaluations": list_data,
}, ensure_ascii=False, indent=2))
