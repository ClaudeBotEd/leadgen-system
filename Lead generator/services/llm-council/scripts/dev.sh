#!/usr/bin/env bash
# Start backend + frontend in parallel for local development.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Friendly pre-flight check.
if [ ! -f .env.local ] && [ ! -f .env ]; then
  echo "[dev] No .env / .env.local found. Copy .env.example to .env.local before running."
  echo "      cp .env.example .env.local"
  echo
fi

cleanup() {
  echo
  echo "[dev] Stopping..."
  kill ${BACKEND_PID:-0} ${FRONTEND_PID:-0} 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "[dev] Backend  -> http://localhost:${LLM_COUNCIL_PORT:-8001}"
uv run uvicorn backend.main:app \
  --host "${LLM_COUNCIL_HOST:-0.0.0.0}" \
  --port "${LLM_COUNCIL_PORT:-8001}" \
  --reload &
BACKEND_PID=$!

sleep 2

echo "[dev] Frontend -> http://localhost:5173"
(cd frontend && npm run dev) &
FRONTEND_PID=$!

wait
