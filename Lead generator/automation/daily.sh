#!/usr/bin/env bash
# Daily lead-gen workflow.
#
# Usage:
#   ./daily.sh                              # default: warmtepomp + amsterdam + 25
#   ./daily.sh warmtepomp utrecht 50
#   ./daily.sh airco antwerpen 30 be
#
# Wat het doet:
#   1. Scrape <niche> + <location> via lead-radar
#   2. Import nieuwe leads in crm-light
#   3. Genereer outreach batch
#   4. Toon dashboard

set -euo pipefail

# Unbuffered Python output - zie progressie real-time
export PYTHONUNBUFFERED=1

NICHE="${1:-warmtepomp}"
LOCATION="${2:-amsterdam}"
MAX="${3:-25}"
COUNTRY="${4:-nl}"

SIGNATURE="${SIGNATURE:-Je naam}"
FROM_EMAIL="${FROM_EMAIL:-}"
FROM_COMPANY="${FROM_COMPANY:-}"

HERE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ROOT="$( cd "$HERE/.." && pwd )"

echo ""
echo "================================================================"
echo "  DAILY LEAD-GEN WORKFLOW"
echo "  $(date +'%Y-%m-%d %H:%M')"
echo "  Niche=$NICHE  Location=$LOCATION  Max=$MAX  Country=$COUNTRY"
echo "================================================================"

if ! command -v python3 &> /dev/null; then
    echo "[!] python3 niet gevonden - installeer Python 3.10+ eerst"
    exit 1
fi

if [ ! -f "$ROOT/lead-radar/requirements.txt" ]; then
    echo "[!] lead-radar/requirements.txt niet gevonden"
    exit 1
fi

if ! python3 -c "import requests, bs4, yaml, duckduckgo_search" 2>/dev/null; then
    echo ""
    echo "[setup] Eerste keer - installeer Python deps..."
    pip3 install -r "$ROOT/lead-radar/requirements.txt"
fi

python3 "$HERE/pipeline.py" \
    --niche "$NICHE" \
    --location "$LOCATION" \
    --country "$COUNTRY" \
    --max "$MAX" \
    --signature "$SIGNATURE" \
    --from-email "$FROM_EMAIL" \
    --from-company "$FROM_COMPANY"

echo ""
echo "================================================================"
echo "  KLAAR. Volgende stappen:"
echo "  1. Open outreach/outbox/batch_${NICHE}_${LOCATION}_$(date +%Y%m%d).txt"
echo "  2. Kopieer en verstuur emails handmatig (max 30/dag/mailbox)"
echo "  3. Log in CRM: python3 crm-light/crm.py log <id> --type email_sent --content 'v1'"
echo "================================================================"
echo ""
