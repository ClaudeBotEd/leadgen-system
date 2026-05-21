#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTDIR="$REPO_ROOT/data/proof_sprint_2026-05-20/consumer/rehearsal_warmtepomp"
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

mkdir -p "$OUTDIR"
cd "$REPO_ROOT"

export LEAD_RADAR_SPREADSHEET_ID="$LEAD_RADAR_REHEARSAL_SPREADSHEET_ID"
export LEAD_RADAR_GS_CREDENTIALS="$CREDENTIALS"
export LEAD_RADAR_SHEETS_OPP_FLOOR=40
export LEAD_RADAR_LLM_BUDGET_EUR=3.00

CANONICAL_SOURCES="$(python3 -c 'from consumer.sources import PROOF_SPRINT_SOURCES; print(",".join(PROOF_SPRINT_SOURCES))')"

echo "Running warmtepomp official proof-sprint rehearsal"
echo "Sources: $CANONICAL_SOURCES"
echo "Outdir: $OUTDIR"
echo "Log: $OUTDIR/run.log"
echo

set +e
python3 run_consumer.py \
  --niche warmtepomp \
  --sources "$CANONICAL_SOURCES" \
  --max-age-days 14 \
  --sheets \
  --no-telegram \
  --outdir "$OUTDIR" \
  2>&1 | tee "$OUTDIR/run.log"
CONSUMER_STATUS=${PIPESTATUS[0]}
set -e

echo
echo "Rehearsal command finished with exit code $CONSUMER_STATUS"
echo "Next steps:"
echo "1. Inspect $OUTDIR/run.log"
echo "2. Review exported CSV/JSON in $OUTDIR"
echo "3. Check rehearsal Sheet tabs for HOT/ALL/OPPORTUNITIES rows"
echo "4. Record metrics in data/proof_sprint_2026-05-20/metrics.md"

exit "$CONSUMER_STATUS"
