#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CREDENTIALS="$REPO_ROOT/.credentials/google_sheets.json"

if [[ -z "${LEAD_RADAR_REHEARSAL_SPREADSHEET_ID:-}" ]]; then
  echo "ERROR: missing LEAD_RADAR_REHEARSAL_SPREADSHEET_ID." >&2
  echo "Set LEAD_RADAR_REHEARSAL_SPREADSHEET_ID to the rehearsal Google Sheet ID." >&2
  exit 1
fi

if [[ ! -f "$CREDENTIALS" ]]; then
  echo "ERROR: Google Sheets credentials not found: $CREDENTIALS" >&2
  exit 1
fi

if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "WARNING: ANTHROPIC_API_KEY is missing; LLM verification may be skipped." >&2
  echo "Continuing in 3 seconds..." >&2
  sleep 3
fi

TIMESTAMP="$(date +%Y-%m-%dT%H-%M-%S)"
OUTROOT="$REPO_ROOT/data/proof_sprint_2026-05-20/consumer/full_rehearsal_${TIMESTAMP}"

mkdir -p "$OUTROOT"
cd "$REPO_ROOT"

export LEAD_RADAR_SPREADSHEET_ID="$LEAD_RADAR_REHEARSAL_SPREADSHEET_ID"
export LEAD_RADAR_GS_CREDENTIALS="$CREDENTIALS"
export LEAD_RADAR_SHEETS_OPP_FLOOR=40
export LEAD_RADAR_LLM_BUDGET_EUR=3.00

NICHES="$(python3 - <<'PY'
from pathlib import Path

import yaml

cfg = yaml.safe_load(Path("consumer/queries.yaml").read_text(encoding="utf-8")) or {}
for niche in (cfg.get("niches") or {}):
    print(niche)
PY
)"

SOURCES="$(python3 - <<'PY'
from consumer.sources import PROOF_SPRINT_SOURCES

print(",".join(PROOF_SPRINT_SOURCES))
PY
)"

echo "Running full proof-sprint rehearsal"
echo "Sources: $SOURCES"
echo "Outroot: $OUTROOT"
echo

for niche in $NICHES; do
  NICHE_DIR="$OUTROOT/$niche"
  mkdir -p "$NICHE_DIR"

  echo "Running niche: $niche"
  echo "Outdir: $NICHE_DIR"
  echo "Log: $NICHE_DIR/run.log"

  set +e
  python3 run_consumer.py \
    --niche "$niche" \
    --sources "$SOURCES" \
    --max-age-days 14 \
    --sheets \
    --no-telegram \
    --outdir "$NICHE_DIR" \
    2>&1 | tee "$NICHE_DIR/run.log"
  CONSUMER_STATUS=${PIPESTATUS[0]}
  set -e

  printf "%s\n" "$CONSUMER_STATUS" > "$NICHE_DIR/.exit_code"
  echo "Niche $niche finished with exit code $CONSUMER_STATUS"
  echo
done

set +e
python3 scripts/summarize_rehearsal_results.py "$OUTROOT"
SUMMARY_STATUS=$?
set -e

if [[ "$SUMMARY_STATUS" -ne 0 ]]; then
  echo "ERROR: summary generation failed with exit code $SUMMARY_STATUS" >&2
fi

echo "Summary: $OUTROOT/summary.md"
echo "Machine summary: $OUTROOT/summary.json"

exit 0
