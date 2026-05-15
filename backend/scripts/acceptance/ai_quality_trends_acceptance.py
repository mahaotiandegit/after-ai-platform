import json
import sys
import urllib.error
import urllib.request


URL = "http://127.0.0.1:8000/api/v1/ai-quality/trends?days=7"

required_keys = [
    "days",
    "daily_invocations",
    "scene_daily_distribution",
    "daily_bad_cases",
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

if data["days"] != 7:
    print("[FAIL] days should be 7")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    sys.exit(1)

if not isinstance(data["daily_invocations"], list):
    print("[FAIL] daily_invocations should be list")
    sys.exit(1)

if not isinstance(data["scene_daily_distribution"], list):
    print("[FAIL] scene_daily_distribution should be list")
    sys.exit(1)

if not isinstance(data["daily_bad_cases"], list):
    print("[FAIL] daily_bad_cases should be list")
    sys.exit(1)

if data["daily_invocations"]:
    row = data["daily_invocations"][0]
    for key in ["day", "total", "success_count", "failed_count", "success_rate", "avg_latency_ms"]:
        if key not in row:
            print("[FAIL] daily_invocations row missing key:", key)
            print(json.dumps(row, ensure_ascii=False, indent=2))
            sys.exit(1)

print("[PASS] AI Quality Trends API accepted")
print(json.dumps(data, ensure_ascii=False, indent=2))
