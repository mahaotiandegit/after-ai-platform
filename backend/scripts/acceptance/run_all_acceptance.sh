#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/../.."

PY=".venv/bin/python"

if [ ! -x "$PY" ]; then
  echo "[FAIL] 未找到 .venv/bin/python"
  exit 1
fi

"$PY" scripts/acceptance/run_all_acceptance.py
