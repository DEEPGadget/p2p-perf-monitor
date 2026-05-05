#!/usr/bin/env bash
# /api/health 30초 polling. 정상 시 0, 실패 시 1.

set -euo pipefail

URL="${HEALTH_URL:-http://127.0.0.1:8080/api/health}"
TIMEOUT="${HEALTH_TIMEOUT_SEC:-30}"

log()  { printf '\033[1;36m[health]\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31m[health]\033[0m %s\n' "$*" >&2; exit 1; }

deadline=$(( SECONDS + TIMEOUT ))
while (( SECONDS < deadline )); do
  if curl -fsS --max-time 2 "${URL}" >/dev/null 2>&1; then
    log "OK — ${URL}"
    exit 0
  fi
  sleep 1
done
fail "timeout — ${URL} (${TIMEOUT}s)"
