# p2p-perf-monitor

ManyCore DeepGadget 서버 2대(`dg5W-H200NVL-4` / `dg5R-PRO6000SE-8`) 간 200G RoCE P2P 통신 성능을 실시간 측정·시각화하는 Web 기반 데모 도구. 전시회 시연 용도.

## 목적

- 두 서버에 각각 Mellanox ConnectX-6 200G NIC 장착, RoCE v2 P2P 링크
- `perftest`(RDMA) + `iperf3`(TCP) 실시간 대역폭·지연 측정
- NIC IC + 광 트랜시버 모듈 온도 4채널 텔레메트리 (액냉)
- 웹 브라우저에서 실시간 시각화 (1080p 부스 디스플레이, 흑백 + cyan 톤)

## 기술 스택

- **백엔드**: FastAPI + asyncssh + structlog (Python)
- **프론트**: SvelteKit + Tailwind v4 + ECharts + GSAP (TypeScript)
- **푸시**: SSE 단방향 (4 이벤트: `measurement` / `nic_temp` / `status` / `error`)
- **운영**: systemd, 단일 controller (양쪽 SSH 트리거), 폐쇄망 부스

## 상태

Phase 1~3 완료 — 측정 PoC, FastAPI/SSE 백엔드, SvelteKit 프론트, 라이브 RoCE v2 ~190 Gb/s 검증.
Phase 4 진행 중 — Docker Compose + systemd 패키징.
상세 → `handoff/current-state.md`. 구현 계획 → `docs/implementation-plan.md`.

## 운영 (Phase 4)

### 사전 조건

- controller 호스트: **dg5W** (자기 자신 + dg5R 양쪽으로 SSH 측정 트리거)
- `docker` + `docker compose` v2 설치, `systemd` 사용 가능
- 양쪽 서버 RoCE 동작 확인, dg5W 에서 dg5R 로 패스워드 SSH 1회 가용

### 설치

```bash
sudo bash scripts/install.sh
```

수행 내용:

1. `/etc/p2p-monitor/` 생성 (700, root)
2. SSH 키 생성 (`~~/etc/p2p-monitor/p2p_monitor_ed25519`) — 이미 있으면 skip
3. `ssh-copy-id` (PW 1회 → dg5W, dg5R) — 키 인증 OK 면 skip
4. `ssh-keyscan` → `known_hosts_p2p`
5. `.env` 템플릿 — 이미 있으면 skip
6. `/opt/p2p-monitor/` 동기화 + `docker compose build`
7. `systemctl enable --now p2p-monitor`
8. `/api/health` 30초 polling

### 운영 명령

```bash
make logs        # journalctl -u p2p-monitor -f
make restart     # systemctl restart
make ps          # 컨테이너 상태
make health      # /api/health 폴링
make demo        # MEASUREMENT_TOOL=mock 으로 띄움 (NIC 부재 시연)
make uninstall   # systemd disable + 이미지·앱 디렉터리 제거 (/etc/p2p-monitor 보존)
```

### 산출물

| 파일 | 역할 |
|------|------|
| `Dockerfile` | multi-stage (node frontend build → python:3.12-slim runtime, uv) |
| `docker-compose.yml` | 단일 서비스, 8080:8080, `/etc/p2p-monitor` ro 마운트, journald 로깅 |
| `systemd/p2p-monitor.service` | foreground compose wrapper, `Restart=always` |
| `scripts/install.sh` | 1회 setup (멱등) |
| `scripts/health-check.sh` | `/api/health` 30초 polling |
| `scripts/uninstall.sh` | systemd 비활성화 + 이미지·앱 디렉터리 제거 |
| `Makefile` | 운영 단축 명령 |

CI 에서 `docker build` + 컨테이너 health smoke test 자동 검증 (`.github/workflows/ci.yml`).

## 디렉터리

자세한 구조는 `CLAUDE.md` §Directory 참조. 정본 파일 매핑 표는 `CLAUDE.md` 상단.

## 라이선스

TBD
