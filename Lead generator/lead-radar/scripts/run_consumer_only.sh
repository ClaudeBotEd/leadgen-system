#!/bin/bash
# Lead Radar — consumer-pipeline-only wrapper (no FB Apify).
#
# Launchd entry point: loads .env, runs run_consumer.py --daily restricted
# to the 10 non-FB sources, logs to stdout/stderr (launchd captures via
# StandardOutPath/StandardErrorPath).
#
# Exits 0 on full success, non-zero if pipeline fails. Distinguish from
# scripts/run_apify_pipeline.sh which also drains the FB queue.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

if [[ ! -f .env ]]; then
  echo "FATAL: $REPO_ROOT/.env missing — needed for Sheets + LLM keys" >&2
  exit 2
fi

# Export every var from .env into the environment for this process.
set -a
# shellcheck disable=SC1091
source .env
set +a

VENV_PY="$REPO_ROOT/.venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
  echo "FATAL: venv python not found at $VENV_PY" >&2
  exit 2
fi

# Non-FB sources — the FB Apify path runs under its own launchd agent.
NON_FB_SOURCES="reddit,reddit_new,tweakers,bouwinfo,bouwinfo_forum,klusidee_forum,ouders_forum,google,marktplaats,2dehands"

echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) Consumer-only pipeline begin ==="

# Fail-fast env check (added by Plan A Task 2)
"$VENV_PY" run_consumer.py --daily --sources "$NON_FB_SOURCES" --check-env-only

echo "--- Running run_consumer.py --daily --sources ${NON_FB_SOURCES} ---"
"$VENV_PY" run_consumer.py --daily --sources "$NON_FB_SOURCES"

echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) Consumer-only pipeline end (ok) ==="
