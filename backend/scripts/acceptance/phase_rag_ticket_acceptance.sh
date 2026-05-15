#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "========== 1. healthz =========="
curl -fsS "$BASE_URL/healthz" | python3 -m json.tool

echo
echo "========== 2. knowledge search =========="
curl -fsSG "$BASE_URL/api/v1/knowledge/search" \
  --data-urlencode "q=物流延迟补偿" \
| python3 -m json.tool

echo
echo "========== 3. knowledge ask: natural question =========="
ASK_RESULT=$(curl -fsS -X POST "$BASE_URL/api/v1/knowledge/ask" \
  -H "Content-Type: application/json" \
  -d '{"question":"物流延迟应该怎么补偿？","top_k":5}')

echo "$ASK_RESULT" | python3 -m json.tool

python3 - <<PY
import json
data = json.loads('''$ASK_RESULT''')
assert data.get("qa_log_id"), "qa_log_id is empty"
assert data.get("citations"), "citations is empty"
assert data.get("query") == "物流延迟补偿", f"unexpected query: {data.get('query')}"
print("knowledge ask acceptance passed")
PY

echo
echo "========== 4. ticket auto-create: logistics_delay_refund =========="
TICKET_RESULT=$(curl -fsS -X POST "$BASE_URL/api/v1/tickets/auto-create" \
  -H "Content-Type: application/json" \
  -d '{
    "order_no": "ORDER-20260515-0001",
    "customer_question": "我的包裹三天没更新了，能不能退款或者补偿？",
    "created_by_id": "11111111-1111-1111-1111-111111111111"
  }')

echo "$TICKET_RESULT" | python3 -m json.tool

python3 - <<PY
import json
data = json.loads('''$TICKET_RESULT''')
ticket = data.get("ticket") or data
assert ticket.get("category") == "logistics_delay_refund", ticket
assert ticket.get("priority") == "high", ticket
print("ticket classification acceptance passed")
PY

echo
echo "========== 5. analytics overview =========="
curl -fsS "$BASE_URL/api/v1/analytics/overview" | python3 -m json.tool

echo
echo "========== PASS: RAG ask + qa_logs + logistics_delay_refund =========="
