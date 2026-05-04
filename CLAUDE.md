# p2p-perf-monitor

서버 2대(각 1× Mellanox ConnectX-7 200G RoCE) 간 P2P 통신 성능을 실시간 측정·시각화하는 Web 기반 데모 도구. 전시회 시연 용도.

> `.claude/rules/` 6개 파일 전체가 system-reminder로 자동 로드됨. 본문의 "→ rules/X" 또는 "→ docs/X" 표기는 정본 위치 안내용 (실제 내용은 자동 로드되거나 on-demand로 읽음).

## 정본 파일 매핑

drift 방지를 위해 각 카테고리의 단일 정본 파일을 명시. 갱신 시 정본 파일만 수정하고 다른 문서는 참조만.

| 카테고리 | 정본 파일 | 갱신 시점 |
|---------|----------|----------|
| 디렉터리 구조 (전체 트리) | `CLAUDE.md` (본 파일) | Phase 1·3 시작 시 |
| 측정 명령·파싱 규약·`MeasurementEvent`/`NicTelemetry` 스키마 | `.claude/rules/measurement.md` | API/스키마 변경 시 |
| API 엔드포인트·SSE 이벤트·에러 코드·큐 정책 | `.claude/rules/api.md` | API 변경 시 |
| 보안 정책 (SSH·sudo·시크릿) | `.claude/rules/security.md` | 위협 모델 변경 시 |
| FE 코드 컨벤션 | `.claude/rules/frontend.md` | 라이브러리·룰 변경 시 |
| 디자인 토큰·색상 팔레트·와이어프레임·모션 | `docs/ui-ux-spec.md` | mockup·디자인 변경 시 |
| NIC 온도 임계값 | `.claude/rules/measurement.md` §임계값 | 부스 실측 후 |
| NIC·서버·트랜시버 환경 가정 | `context/nic-environment.md` | 환경 결정 시 |
| Phase별 산출물·일정·인터페이스 | `docs/implementation-plan.md` | Phase 시작 시 |
| 테스트 도구·fixture·커버리지·CI | `.claude/rules/testing.md` | 테스트 정책 변경 시 |
| 결정 완료/대기 사항 + 진행 상태 | `handoff/current-state.md` | 매 PR / 결정 시 |

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
        StatusBadge.svelte
        HardwareDiagram.svelte    SVG (서버·트랜시버·NIC IC overlay·packet flow)
        KpiCards.svelte           BW NOW/AVG/PEAK/LAT 4 카드
        BandwidthChart.svelte     ECharts 시계열
        NicTempPanel.svelte       4 타일 (IC/MOD × dg5W/dg5R) + 4-line 시계열
        ControlPanel.svelte       Tool/MsgSize/Duration/Direction/Start
      stores/
        measurement.svelte.ts     BW 이벤트 store
        nic_telemetry.svelte.ts   NIC IC + Module 온도 store (1Hz)
        session.svelte.ts         IDLE/CONNECTING/RUNNING/ERROR
      utils/
        sse.ts
        format.ts
        api.ts
      types/
        api.ts                    백엔드 Pydantic 모델 1:1 매핑
    app.css                Tailwind directives + 디자인 토큰
  static/
    manycore_logo_white.png       다크 헤더용 (현재 사용)
    manycore_logo_black.png       라이트 배경 대비용 (보관)
    fonts/                        Inter, JetBrains Mono — self-hosted
  svelte.config.js         (adapter-static)
  vite.config.ts
  tailwind.config.js
  tsconfig.json
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
- **UI 톤**: 흑백 + cyan(#00d9ff) 강조. KPI 카드 폰트 72px. 모션 풀가속 → `docs/ui-ux-spec.md` §6.4
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
| `MEASUREMENT_TOOL` | 카테고리 default — `perftest` \| `iperf3` \| `mock`. API body의 `tool` 필드(서브툴)와 구분 → `.claude/rules/measurement.md` | `perftest` |
| `BIND_HOST` / `BIND_PORT` | FastAPI 바인드 | `0.0.0.0` / `8080` |

## 결정 대기 항목

→ `handoff/current-state.md` "결정 대기 항목" 섹션에서 통합 관리.

## 현재 구현 상태

> 진행 현황·다음 작업 → `handoff/current-state.md`

**Phase 0 진행 중 (문서 + GUI 목업 완료, 교차검증 대기)**:
- 문서 1차 작성 완료 (CLAUDE.md / `.claude/rules/`×6 / `docs/`×2 / `context/`×1 / `handoff/`)
- GUI 목업 완료 (`mockup/index.html` 단일 HTML, ManyCore 로고 적용, mock 데이터로 모든 컴포넌트·모션 검증)
- 코드(app/, frontend/) 미작성 — Phase 1부터 시작

구현 계획서 → `docs/implementation-plan.md`. UI/UX 사양 → `docs/ui-ux-spec.md`.

## Git Repo

`DEEPGadget/p2p-perf-monitor` (public)
