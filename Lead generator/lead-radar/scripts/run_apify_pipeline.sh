#!/bin/bash
# Lead Radar — Apify scrape + pipeline drain wrapper.
#
# Launchd / cron entry point: loads .env, runs the Apify Groups collector,
# then drains the resulting queue through run_consumer.py --daily.
#
# Exits 0 on full success, non-zero if either stage fails. Logs to stdout/
# stderr so launchd's StandardOutPath/StandardErrorPath captures everything.
set -euo pipefail

# Walk up to repo root from this script's location so cron/launchd can call
# us with any CWD.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

if [[ ! -f .env ]]; then
  echo "FATAL: $REPO_ROOT/.env missing — needed for APIFY_API_TOKEN" >&2
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

echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) Apify pipeline run begin ==="

echo "--- stage 1/2: Apify groups collect (--niche all) ---"
"$VENV_PY" -m consumer.sources.facebook.runner apify --niche all

echo "--- stage 2/2: pipeline drain (run_consumer --daily) ---"
"$VENV_PY" run_consumer.py --daily

echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) Apify pipeline run end (ok) ==="
