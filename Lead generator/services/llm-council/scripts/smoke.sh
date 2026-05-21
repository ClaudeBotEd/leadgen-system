#!/usr/bin/env bash
# Smoke-test a running llm-council backend.
# Usage:  ./scripts/smoke.sh [base_url]
#         BASE_URL defaults to http://127.0.0.1:8001
set -euo pipefail

BASE="${1:-http://127.0.0.1:${LLM_COUNCIL_PORT:-8001}}"

step() { printf "\n=== %s\n" "$1"; }

PY=${PYTHON:-python3}

step "GET ${BASE}/health"
curl -fsS "${BASE}/health" | "$PY" -m json.tool

step "GET ${BASE}/health/live"
curl -fsS "${BASE}/health/live" | "$PY" -m json.tool

step "GET ${BASE}/health/ready"
curl -fsS "${BASE}/health/ready" | "$PY" -m json.tool

step "POST ${BASE}/api/conversations"
CONV=$(curl -fsS -X POST "${BASE}/api/conversations" \
  -H 'Content-Type: application/json' -d '{}')
echo "$CONV" | "$PY" -m json.tool
ID=$(echo "$CONV" | "$PY" -c "import json,sys;print(json.load(sys.stdin)['id'])")

step "GET ${BASE}/api/conversations/${ID}"
curl -fsS "${BASE}/api/conversations/${ID}" | "$PY" -m json.tool

step "DELETE ${BASE}/api/conversations/${ID}"
curl -fsS -X DELETE "${BASE}/api/conversations/${ID}" -o /dev/null -w "status=%{http_code}\n"

echo
echo "Smoke test passed."
