#!/usr/bin/env bash
# p2p-perf-monitor 제거. /etc/p2p-monitor (SSH 키·.env) 는 보존.

set -euo pipefail

SERVICE_NAME="p2p-monitor"
APP_DIR="/opt/p2p-monitor"

log()  { printf '\033[1;36m[uninstall]\033[0m %s\n' "$*"; }

[[ $EUID -eq 0 ]] || { echo "root 권한 필요" >&2; exit 1; }

log "systemd 비활성화 + 정지"
systemctl disable --now "${SERVICE_NAME}.service" 2>/dev/null || true

log "compose down"
if [[ -f "${APP_DIR}/docker-compose.yml" ]]; then
  ( cd "${APP_DIR}" && docker compose down --remove-orphans ) || true
fi

log "unit 제거 + reload"
rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
systemctl daemon-reload

log "이미지 정리 (p2p-monitor:latest)"
docker rmi p2p-monitor:latest 2>/dev/null || true

log "${APP_DIR} 제거"
rm -rf "${APP_DIR}"

log "완료 — /etc/p2p-monitor (키·.env) 는 보존됨. 완전 제거 원할 시 'rm -rf /etc/p2p-monitor'"
