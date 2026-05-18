#!/bin/bash
# Lead Radar — heartbeat: alert when launchd pipelines go silent.
#
# Runs every 4h via com.leadradar.heartbeat.plist. Checks mtime of:
#   - apify.log    (threshold: 30 hours, FB runs 4x/day)
#   - consumer.log (threshold: 8 hours, consumer runs 3x/day)
#
# Missing log or too-old mtime triggers a Telegram alert.
#
# Env overrides (used by tests):
#   HEARTBEAT_LOGS_DIR=/path/to/logs (default: <repo>/logs)
#   HEARTBEAT_DRY_RUN=1              (skip actual curl POST)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

LOGS_DIR="${HEARTBEAT_LOGS_DIR:-$REPO_ROOT/logs}"
DRY_RUN="${HEARTBEAT_DRY_RUN:-0}"

# Source .env for Telegram credentials, unless they're already in env (test path).
if [[ -z "${TELEGRAM_BOT_TOKEN:-}" || -z "${TELEGRAM_CHAT_ID:-}" ]]; then
  if [[ -f "$REPO_ROOT/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$REPO_ROOT/.env"
    set +a
  fi
fi

# Parallel arrays (bash 3.2 compat on macOS default shell).
NAMES=("apify" "consumer")
THRESHOLDS_H=(30 8)

NOW_EPOCH="$(date +%s)"
ALERTS=()

for i in 0 1; do
  name="${NAMES[$i]}"
  threshold_h="${THRESHOLDS_H[$i]}"
  threshold_s=$(( threshold_h * 3600 ))
  log_path="$LOGS_DIR/${name}.log"

  if [[ ! -f "$log_path" ]]; then
    echo "ALERT: $name log missing at $log_path"
    ALERTS+=("$name: log file missing")
    continue
  fi

  # macOS-compatible mtime in epoch seconds.
  mtime_epoch="$(stat -f %m "$log_path")"
  age_s=$(( NOW_EPOCH - mtime_epoch ))
  age_h=$(( age_s / 3600 ))

  if (( age_s > threshold_s )); then
    echo "ALERT: $name silent for ${age_h}h (threshold ${threshold_h}h)"
    ALERTS+=("$name: silent for ${age_h}h (threshold ${threshold_h}h)")
  else
    echo "OK: $name last activity ${age_h}h ago"
  fi
done

if [[ ${#ALERTS[@]} -eq 0 ]]; then
  echo "OK: all pipelines healthy"
  exit 0
fi

# Build alert message.
hostname_short="$(hostname -s 2>/dev/null || echo "mac")"
msg="🚨 Lead Radar heartbeat — pipeline silent on ${hostname_short}"$'\n\n'
for a in "${ALERTS[@]}"; do
  msg+="  • $a"$'\n'
done
msg+=$'\n'"Logs: $LOGS_DIR"

if [[ "$DRY_RUN" == "1" ]]; then
  echo "DRY_RUN: would send Telegram alert:"
  echo "$msg"
  exit 0
fi

if [[ -z "${TELEGRAM_BOT_TOKEN:-}" || -z "${TELEGRAM_CHAT_ID:-}" ]]; then
  echo "WARN: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing — cannot send alert" >&2
  exit 1
fi

# Plain text — no parse_mode (avoid MarkdownV2 escape hell, per Plan A fix c95cee2).
curl -sS \
  --max-time 10 \
  -X POST \
  "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -d "chat_id=${TELEGRAM_CHAT_ID}" \
  --data-urlencode "text=${msg}" \
  > /dev/null

echo "Heartbeat alert sent to Telegram"
exit 0
