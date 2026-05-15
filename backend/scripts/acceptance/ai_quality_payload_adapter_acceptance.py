import json
import sys
import urllib.error
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


run_data = request_json(
    "http://127.0.0.1:8000/api/v1/ai-quality/evaluations/run-recent?limit=100&force=true",
    method="POST",
)

if run_data.get("force") is not True:
    print("[FAIL] run-recent should return force=true")
    print(json.dumps(run_data, ensure_ascii=False, indent=2))
    sys.exit(1)

if "evaluated_count" not in run_data or "items" not in run_data:
    print("[FAIL] run-recent missing evaluated_count/items")
    print(json.dumps(run_data, ensure_ascii=False, indent=2))
    sys.exit(1)

summary = request_json(
    "http://127.0.0.1:8000/api/v1/ai-quality/evaluations/summary?recent_limit=10&top_issue_limit=20",
    method="GET",
)

required_summary_keys = [
    "total_evaluations",
    "status_distribution",
    "scene_score_summary",
    "top_issues",
    "recent_high_risk_evaluations",
]

for key in required_summary_keys:
    if key not in summary:
        print("[FAIL] summary missing key:", key)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        sys.exit(1)

items = request_json(
    "http://127.0.0.1:8000/api/v1/ai-quality/evaluations?limit=20",
    method="GET",
)

if "items" not in items or not isinstance(items["items"], list):
    print("[FAIL] evaluations list invalid")
    print(json.dumps(items, ensure_ascii=False, indent=2))
    sys.exit(1)

if items["items"]:
    row = items["items"][0]
    for key in ["id", "ai_log_id", "scene", "score", "status", "issues", "suggestions"]:
        if key not in row:
            print("[FAIL] evaluation row missing:", key)
            print(json.dumps(row, ensure_ascii=False, indent=2))
            sys.exit(1)

print("[PASS] AI Quality Payload Adapter accepted")
print(json.dumps({
    "run_recent": {
        "requested_limit": run_data.get("requested_limit"),
        "force": run_data.get("force"),
        "evaluated_count": run_data.get("evaluated_count"),
    },
    "summary": summary,
}, ensure_ascii=False, indent=2))
