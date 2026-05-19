#!/usr/bin/env bash
# Legacy entry point - forwards to scripts/dev.sh.
# Prefer:  make dev   (or)   ./scripts/dev.sh
set -euo pipefail
exec "$(dirname "$0")/scripts/dev.sh" "$@"
