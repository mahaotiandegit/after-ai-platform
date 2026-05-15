import json
import sys
import urllib.error
import urllib.request


URL = "http://127.0.0.1:8000/api/v1/ai-quality/evaluations/summary?recent_limit=5&top_issue_limit=10"

required_keys = [
    "total_evaluations",
    "pass_count",
    "warn_count",
    "fail_count",
    "average_score",
    "status_distribution",
    "scene_score_summary",
    "top_issues",
    "recent_high_risk_evaluations",
]

try:
    with urllib.request.urlopen(URL, timeout=8) as resp:
        status = resp.status
        body = resp.read().decode("utf-8")
except urllib.error.HTTPError as e:
    print("[FAIL] HTTP error:", e.code)
    print(e.read().decode("utf-8", errors="replace"))
    sys.exit(1)
except Exception as e:
    print("[FAIL] request failed:", repr(e))
    sys.exit(1)

if status != 200:
    print("[FAIL] unexpected status:", status)
    print(body)
    sys.exit(1)

try:
    data = json.loads(body)
except Exception as e:
    print("[FAIL] invalid json:", repr(e))
    print(body)
    sys.exit(1)

missing = [key for key in required_keys if key not in data]
if missing:
    print("[FAIL] missing keys:", missing)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    sys.exit(1)

if not isinstance(data["status_distribution"], dict):
    print("[FAIL] status_distribution should be object")
    sys.exit(1)

for status_key in ["pass", "warn", "fail"]:
    if status_key not in data["status_distribution"]:
        print("[FAIL] status_distribution missing:", status_key)
        sys.exit(1)

if not isinstance(data["scene_score_summary"], list):
    print("[FAIL] scene_score_summary should be list")
    sys.exit(1)

if not isinstance(data["top_issues"], list):
    print("[FAIL] top_issues should be list")
    sys.exit(1)

if not isinstance(data["recent_high_risk_evaluations"], list):
    print("[FAIL] recent_high_risk_evaluations should be list")
    sys.exit(1)

if data["scene_score_summary"]:
    row = data["scene_score_summary"][0]
    for key in ["scene", "total", "average_score", "pass_count", "warn_count", "fail_count"]:
        if key not in row:
            print("[FAIL] scene summary row missing:", key)
            print(json.dumps(row, ensure_ascii=False, indent=2))
            sys.exit(1)

print("[PASS] AI Quality Evaluation Summary API accepted")
print(json.dumps(data, ensure_ascii=False, indent=2))
