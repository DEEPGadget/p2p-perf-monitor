# p2p-perf-monitor

서버 2대(각 1× Mellanox ConnectX-7 200G RoCE) 간 P2P 통신 성능을 실시간 측정·시각화하는 Web 기반 데모 도구. 전시회 시연 용도.

> `.claude/rules/` 6개 파일 전체가 system-reminder로 자동 로드됨. 아래 "→ rules/X" 표기는 위치 안내용.

## 핵심 원칙

- **단순함 우선**: 전시 부스에서 무인 가동 + 빠른 재시작·복구
- **시각적 임팩트**: 200G RoCE의 raw performance를 직관적으로 보여주는 화려·역동적 UI (참고: cloudflare speed test, awwwards Overwatch, nperf)
- **흑백 + 강조 1색**: 디자인 톤 흰색·검정 위주 + cyan 강조
- **LLM 미사용**: 측정·파싱·시각화는 결정론적 코드. 토큰 0
- **단일 세션**: DB 없음, 한 번에 1개 측정만. 전시용 단순성

## Architecture

```
[Browser — SvelteKit static]
  │  EventSource /api/stream
  v
[FastAPI on controller server (= Server A 또는 B 한쪽)]
  │  asyncssh
  ├─→ [Server A] perftest server  (ib_write_bw -d mlx5_0 ...)
  └─→ [Server B] perftest client  (ib_write_bw -d mlx5_0 ... <A_ip>)
        │ stdout 스트림
        v
   [parser] → MeasurementEvent → [SSE channel] → Browser 그래프 업데이트
```

- Controller: 두 서버 중 한 쪽이 겸함. 별도 머신 불필요
- 측정 도구: **`perftest` (RoCE/RDMA)** 메인 — `ib_write_bw`(BW), `ib_read_lat`(latency). **`iperf3` (TCP)** 옵션 — 비교 데모용
- NIC: ConnectX-7 200G, MLNX_OFED 사전 설치 → `context/nic-environment.md`
- 푸시: SSE 단방향. 컨트롤(start/stop/파라미터)은 일반 POST
- 상태: in-memory (`state.py`). 재시작 시 초기화

## Frontend Stack

- **SvelteKit** (Svelte 5) + **Vite** — static adapter, FastAPI가 빌드 결과 서빙
- **Tailwind CSS v4** — 흑백 톤 빠른 구현
- **ECharts v5** — 시계열 그래프 (트렌디한 룩, 풍부한 옵션)
- **GSAP** — 숫자 카운터 / 화면 전환 / 패킷 흐름 애니메이션
- **Lucide Icons** — 아이콘
- **Threlte** (Svelte+Three.js) — 옵션, 하드웨어 구성도 3D 업그레이드

UI/UX 상세 → `docs/ui-ux-spec.md`. 코드 룰 → `.claude/rules/frontend.md`

## Directory

```
app/                       Python 백엔드
  main.py                  FastAPI 엔트리 (정적 라우트 + /api/* 등록)
  api/
    measure.py             POST /api/start, /api/stop, GET /api/status
    stream.py              GET /api/stream (SSE)
  runner.py                asyncssh로 양쪽 서버 perftest 오케스트레이션
  parser.py                perftest/iperf3 stdout → MeasurementEvent
  state.py                 단일 세션 상태 + SSE pub/sub
  config.py                ENV 로딩
  schemas.py               Pydantic 모델

frontend/                  SvelteKit
  src/
    routes/
      +layout.svelte
      +page.svelte         단일 메인 페이지
    lib/
      components/
        Header.svelte
        HardwareDiagram.svelte
        KpiCards.svelte
        BandwidthChart.svelte
        ControlPanel.svelte
        StatusBadge.svelte
      stores/
        measurement.ts     Svelte store + SSE 구독
      utils/
        sse.ts
        format.ts
    app.css                Tailwind directives
  static/
    logo.svg
  svelte.config.js         (adapter-static)
  vite.config.ts
  tailwind.config.js
  package.json

tests/                     Python pytest
  test_parser.py
  test_runner.py
  test_api.py
  fixtures/
    perftest_*.txt
    iperf3_*.json

systemd/
  p2p-monitor.service

docs/
  implementation-plan.md
  ui-ux-spec.md

context/
  nic-environment.md       ConnectX-7 200G + MLNX_OFED 사전 조건

.claude/rules/
  code-style.md / api.md / measurement.md / frontend.md / security.md / testing.md

pyproject.toml             Python deps (uv)
Makefile
README.md
CLAUDE.md
handoff/current-state.md
```

상세 룰 → `.claude/rules/`

## Key Design Decisions

- **단일 controller + 양쪽 SSH**: 별도 agent 미배포. SSH 키 인증, 패스워드 금지 → `.claude/rules/security.md`
- **측정 출력 표준화**: perftest/iperf3 stdout → 단일 `MeasurementEvent` Pydantic 모델 → `.claude/rules/measurement.md`
- **SSE 단방향**: WebSocket 미사용. 컨트롤은 일반 POST → `.claude/rules/api.md`
- **SvelteKit static**: `adapter-static`으로 정적 빌드 → FastAPI가 `StaticFiles`로 서빙. Node 런타임 운영 환경에 둘 필요 없음 → `.claude/rules/frontend.md`
- **UI 톤**: 흑백 + cyan(#00d9ff) 강조. 5em+ 카운터 폰트. 모션 풀가속 → `docs/ui-ux-spec.md`
- **메모리 상태**: 한 세션, DB 없음. 재시작 시 초기화

## Commands

```bash
# Python BE 개발
uv sync
uv run uvicorn app.main:app --reload --port 8080
uv run pytest tests/ -x -q
uv run ruff check . && uv run ruff format --check .

# Frontend 개발
cd frontend
pnpm install
pnpm dev                              # http://localhost:5173 (Vite)
pnpm build                            # → frontend/build/ (FastAPI에서 서빙)
pnpm test                             # vitest

# 통합 (운영)
cd frontend && pnpm build && cd ..
uv run uvicorn app.main:app --host 0.0.0.0 --port 8080

# systemd 운영
make install
sudo systemctl enable --now p2p-monitor
sudo journalctl -u p2p-monitor -f

# 데모 모드 (실 NIC 없이 UI 검증)
MEASUREMENT_TOOL=mock uv run uvicorn app.main:app --reload

# 측정 도구 사전 검증 (수동)
ssh server-A "ib_write_bw -d mlx5_0 -F --report_gbits -D 60 &"
ssh server-B "ib_write_bw -d mlx5_0 -F --report_gbits -D 60 <server-A-ip>"
```

## 완료 워크플로우

1. `pytest tests/ -x -q` + `ruff check . && ruff format --check .` 통과
2. `cd frontend && pnpm test && pnpm build` 성공
3. `git add <관련파일>` → `git commit` → `git push -u origin <브랜치>`
4. `gh pr create --base main` (PR까지 자동, merge는 사용자 결정)

main 직접 push 금지. 브랜치 명명: `feature/`, `fix/`, `chore/`

## 환경변수

`.env` 참조. 필수:

| 변수 | 설명 | 예시 |
|------|------|------|
| `SERVER_A_HOST` | 서버 A SSH 호스트 (RDMA peer 1) | `10.x.x.10` |
| `SERVER_B_HOST` | 서버 B SSH 호스트 (RDMA peer 2) | `10.x.x.11` |
| `SSH_USER` | SSH 계정 | `deepgadget` |
| `SSH_KEY_PATH` | SSH private key 절대 경로 | `/etc/p2p-monitor/id_ed25519` |
| `SSH_KNOWN_HOSTS` | known_hosts 절대 경로 | `/etc/p2p-monitor/known_hosts` |
| `NIC_DEVICE_A` | Server A NIC 디바이스 | `mlx5_0` |
| `NIC_DEVICE_B` | Server B NIC 디바이스 | `mlx5_0` |
| `RDMA_GID_INDEX` | RoCE v2 GID index | `3` |
| `MEASUREMENT_TOOL` | `perftest` \| `iperf3` \| `mock` | `perftest` |
| `BIND_HOST` / `BIND_PORT` | FastAPI 바인드 | `0.0.0.0` / `8080` |

## 결정 대기 항목

| # | 항목 | 현재 가정 | 확정 시 영향 |
|---|------|----------|-------------|
| - | NIC GID index | 3 (RoCE v2 통상값) | `context/nic-environment.md` |
| - | MTU / Jumbo frame | 9000 (성능 최대치 가정) | 측정 명령 옵션 |
| - | 부스 디스플레이 해상도 | 1080p / 4K 둘 다 대응 | `docs/ui-ux-spec.md` |
| - | 회사 로고 SVG | 추후 제공 | `frontend/static/logo.svg` |

## 현재 구현 상태

> 진행 현황·다음 작업 → `handoff/current-state.md`

문서 단계 (1차 작성 완료, 교차검증 대기). GUI 목업 → `frontend/` 정적 페이지로 디자인 검증 진행.
구현 계획서 → `docs/implementation-plan.md`. UI/UX 사양 → `docs/ui-ux-spec.md`.

## Git Repo

`DEEPGadget/p2p-perf-monitor` (public)
