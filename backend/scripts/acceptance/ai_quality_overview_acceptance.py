import json
import sys
import urllib.error
import urllib.request


URL = "http://127.0.0.1:8000/api/v1/ai-quality/overview"

required_keys = [
    "total_invocations",
    "success_rate",
    "avg_latency_ms",
    "scene_distribution",
    "total_bad_cases",
    "open_bad_cases",
    "fixed_bad_cases",
    "bad_case_fix_rate",
    "recent_bad_cases",
    "recent_failed_invocations",
]

try:
    with urllib.request.urlopen(URL, timeout=5) as resp:
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

missing = [k for k in required_keys if k not in data]
if missing:
    print("[FAIL] missing keys:", missing)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    sys.exit(1)

if not isinstance(data["scene_distribution"], dict):
    print("[FAIL] scene_distribution should be object")
    sys.exit(1)

if not isinstance(data["recent_bad_cases"], list):
    print("[FAIL] recent_bad_cases should be list")
    sys.exit(1)

if not isinstance(data["recent_failed_invocations"], list):
    print("[FAIL] recent_failed_invocations should be list")
    sys.exit(1)

print("[PASS] AI Quality Overview API accepted")
print(json.dumps(data, ensure_ascii=False, indent=2))
