#!/usr/bin/env bash
# p2p-perf-monitor 1회 setup (controller=dg5W 가정)
#
# 정본 절차 → docs/implementation-plan.md §Phase 4
# 실행: sudo bash scripts/install.sh
#
# 멱등성 보장 — 이미 존재하는 키/호스트 항목은 skip.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

ETC_DIR="/etc/p2p-monitor"
APP_DIR="/opt/p2p-monitor"
SERVICE_NAME="p2p-monitor"
KEY_NAME="p2p_monitor_ed25519"
KNOWN_HOSTS_NAME="known_hosts_p2p"

SSH_USER="${SSH_USER:-deepgadget}"
SERVER_A_HOST="${SERVER_A_HOST:-192.168.1.166}"   # dg5W
SERVER_B_HOST="${SERVER_B_HOST:-192.168.1.204}"   # dg5R

log()  { printf '\033[1;36m[install]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[install]\033[0m %s\n' "$*" >&2; }
err()  { printf '\033[1;31m[install]\033[0m %s\n' "$*" >&2; exit 1; }

require_root() {
  [[ $EUID -eq 0 ]] || err "root 권한 필요. 'sudo bash scripts/install.sh' 로 실행."
}

check_prereqs() {
  command -v docker >/dev/null || err "docker 가 설치되어 있지 않다."
  docker compose version >/dev/null 2>&1 || err "docker compose v2 가 필요하다."
  command -v systemctl >/dev/null || err "systemctl 가 필요하다."
  command -v ssh-keygen >/dev/null || err "openssh-client 필요."
}

prepare_etc() {
  log "/etc/p2p-monitor 준비 (700, root:root)"
  install -d -m 700 -o root -g root "${ETC_DIR}"
}

generate_key() {
  local key="${ETC_DIR}/${KEY_NAME}"
  if [[ -f "${key}" ]]; then
    log "SSH 키 이미 존재 — skip (${key})"
    return
  fi
  log "SSH 키 생성 (${key})"
  ssh-keygen -t ed25519 -N '' -C "p2p-monitor@$(hostname)" -f "${key}"
  chmod 600 "${key}"
}

copy_id_if_needed() {
  local host="$1"
  local key="${ETC_DIR}/${KEY_NAME}"
  if ssh -i "${key}" -o BatchMode=yes -o StrictHostKeyChecking=no \
        -o ConnectTimeout=5 "${SSH_USER}@${host}" 'true' 2>/dev/null; then
    log "키 인증 OK (${host}) — skip"
    return
  fi
  warn "키 인증 실패 → ssh-copy-id (${host}). 패스워드 입력 필요."
  ssh-copy-id -i "${key}.pub" -o StrictHostKeyChecking=no "${SSH_USER}@${host}"
}

scan_known_hosts() {
  local kh="${ETC_DIR}/${KNOWN_HOSTS_NAME}"
  log "known_hosts 갱신 (${kh})"
  : > "${kh}.tmp"
  for h in "${SERVER_A_HOST}" "${SERVER_B_HOST}"; do
    ssh-keyscan -t ed25519,rsa "${h}" >>"${kh}.tmp" 2>/dev/null || warn "ssh-keyscan ${h} 실패"
  done
  mv "${kh}.tmp" "${kh}"
  chmod 600 "${kh}"
}

write_env_if_missing() {
  local env="${ETC_DIR}/.env"
  if [[ -f "${env}" ]]; then
    log ".env 이미 존재 — skip (${env})"
    return
  fi
  log ".env 템플릿 생성 (${env}) — 필요 시 수동 편집"
  cat > "${env}" <<EOF
SERVER_A_HOST=${SERVER_A_HOST}
SERVER_B_HOST=${SERVER_B_HOST}
SSH_USER=${SSH_USER}
# 컨테이너 내부 절대경로 (compose 가 SSH_KEY_PATH/SSH_KNOWN_HOSTS env 로 override 하지만 호환을 위해 기재)
SSH_KEY_PATH=${ETC_DIR}/${KEY_NAME}
SSH_KNOWN_HOSTS=${ETC_DIR}/${KNOWN_HOSTS_NAME}

SERVER_A_RDMA_IP=25.47.1.10
SERVER_B_RDMA_IP=25.47.1.11

NIC_DEVICE_A=mlx5_0
NIC_DEVICE_B=mlx5_0

SERVER_A_NETDEV=enp2s0f0np0
SERVER_B_NETDEV=ens7f0np0

RDMA_GID_INDEX_A=3
RDMA_GID_INDEX_B=5
RDMA_MTU=9000

MEASUREMENT_TOOL=perftest
BIND_HOST=0.0.0.0
BIND_PORT=8080
LOG_LEVEL=INFO
EOF
  chmod 600 "${env}"
}

deploy_app_dir() {
  log "/opt/p2p-monitor 동기화 (compose / Dockerfile / app / frontend / scripts)"
  install -d -m 755 "${APP_DIR}"
  # 빌드에 필요한 파일만 복사 — .dockerignore 와 동일 정책으로 최소 set
  rsync -a --delete \
    --exclude '.git/' --exclude '.svelte-kit/' --exclude 'node_modules/' \
    --exclude 'frontend/build/' --exclude '.venv/' --exclude '__pycache__/' \
    --exclude 'tests/' --exclude 'mockup/' --exclude 'docs/' \
    --exclude 'handoff/' --exclude 'context/' --exclude '.env*' \
    "${REPO_ROOT}/" "${APP_DIR}/"
}

build_and_enable() {
  log "docker compose build"
  ( cd "${APP_DIR}" && docker compose build )

  log "systemd unit 설치"
  install -m 644 "${REPO_ROOT}/systemd/p2p-monitor.service" \
    /etc/systemd/system/p2p-monitor.service
  systemctl daemon-reload
  systemctl enable --now "${SERVICE_NAME}.service"
}

run_health_check() {
  log "health-check.sh 실행"
  bash "${SCRIPT_DIR}/health-check.sh"
}

main() {
  require_root
  check_prereqs
  prepare_etc
  generate_key
  copy_id_if_needed "${SERVER_A_HOST}"
  copy_id_if_needed "${SERVER_B_HOST}"
  scan_known_hosts
  write_env_if_missing
  deploy_app_dir
  build_and_enable
  run_health_check
  log "완료 — http://$(hostname -I | awk '{print $1}'):8080"
}

main "$@"
