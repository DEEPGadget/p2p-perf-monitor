# 구현 계획서

> 본 문서는 구현 순서·모듈별 인터페이스·검증 기준을 정의. 코드 룰은 `.claude/rules/`, 시각 디자인은 `docs/ui-ux-spec.md` 참조.

## 1. 원칙

- 백엔드 우선: parser → runner → API → SSE 순으로 단단히
- 프론트는 mock 모드로 디자인 먼저 검증, 통합은 후순위
- 각 Phase 완료 시 PR 1개 이상. main 직접 push 없음
- 모든 PR은 `pytest -m "not live"` + `ruff` + `pnpm test --run` + `pnpm build` 통과

## 2. Phase 개요

| Phase | 산출 | 완료 기준 |
|-------|------|----------|
| **0** | 문서 + 골격 | 본 계획서 + 룰 + CLAUDE.md 합의, 빈 디렉터리 + pyproject + package.json |
| **1** | 측정 PoC (CLI) | 두 서버에 SSH로 perftest 실행, stdout 파싱, JSON 출력 |
| **2** | FastAPI 백엔드 | `/api/start`, `/api/stop`, `/api/status`, `/api/stream` 동작 |
| **3** | SvelteKit 프론트 | mock 데이터로 모든 컴포넌트 렌더링 + 모션 |
| **4** | 통합 + 운영 | systemd, Makefile, README 시연 절차, 1080p 부스 1회 리허설 |
| **5** | 옵션 기능 | 메시지 사이즈 스윕, IB switch counter, 3D 다이어그램 등 |

## 3. Phase 0 — 문서 + 골격 (현재 단계)

### 산출물

- [x] `CLAUDE.md` (재작성 완료)
- [x] `.claude/rules/{code-style, api, measurement, frontend, security, testing}.md`
- [x] `docs/implementation-plan.md` (본 파일)
- [x] `docs/ui-ux-spec.md`
- [x] `context/nic-environment.md`
- [x] `handoff/current-state.md`
- [x] **GUI 목업** (`mockup/index.html` 단일 HTML, ManyCore 로고 적용, mock 데이터로 모든 컴포넌트·모션 검증, 사용자 승인 완료)
- [ ] `pyproject.toml` 초안 (의존성: fastapi, asyncssh, pydantic, uvicorn, structlog) — Phase 1 시작 시
- [ ] `frontend/package.json` 초안 (svelte, sveltekit, vite, tailwind, echarts, gsap, lucide) — Phase 3 시작 시

### 완료 기준

- 모든 문서가 1차 작성 완료 + 사용자 검토 완료
- GUI 목업 사용자 승인 완료
- arch-plan-reviewer / impl-plan-reviewer / harness-doc-reviewer 교차검증 1회 이상
- 검증 피드백 반영 PR 머지

## 4. Phase 1 — 측정 PoC

### 목표

두 서버에 SSH로 perftest 실행하고 stdout을 파싱해서 표준 스키마(MeasurementEvent)로 출력하는 CLI 스크립트.

### 산출물

```
app/
  __init__.py
  schemas.py             StartRequest, SessionStatus, MeasurementEvent, NicTelemetry
                         (스키마 필드 정의 정본 → rules/measurement.md)
  parser.py              parse_ib_write_bw_line, parse_ib_read_lat_line,
                         parse_iperf3_json (uni + bidir 모두)
  runner.py              run_session(req) -> AsyncIterator[MeasurementEvent]
                         + mock_session() (NIC 부재 시 generator)
  config.py              .env 로딩 — Settings(BaseSettings) 정의
                         필수 필드: SERVER_A_HOST, SERVER_B_HOST, SSH_USER,
                         SSH_KEY_PATH, SSH_KNOWN_HOSTS, NIC_DEVICE_A,
                         NIC_DEVICE_B, RDMA_GID_INDEX, MEASUREMENT_TOOL,
                         BIND_HOST, BIND_PORT, DEV_CORS
tests/
  conftest.py            mock asyncssh fixture, TestClient fixture
  fixtures/
    perftest_ib_write_bw_200g_uni.txt    (실측 캡처)
    perftest_ib_write_bw_200g_bidir.txt  (Phase 1 PoC 시 -b 옵션 캡처 필수)
    perftest_ib_read_lat.txt
    iperf3_tcp_8streams.json
    iperf3_tcp_bidir.json
  test_parser.py
  test_runner.py
scripts/
  poc.py                 CLI: python scripts/poc.py --tool ib_write_bw --duration 30
```

### 인터페이스

스키마 필드 정의 정본 → `.claude/rules/measurement.md` (`StartRequest` / `MeasurementEvent` / `NicTelemetry`).

함수 시그니처:

```python
# app/parser.py
def parse_ib_write_bw_line(line: str, bidir: bool = False) -> MeasurementEvent | None: ...
def parse_ib_read_lat_line(line: str) -> MeasurementEvent | None: ...
def parse_iperf3_json(text: str, bidir: bool = False) -> list[MeasurementEvent]:
    """bidir=True 시 sum_sent + sum_received 합산 (rules/measurement.md §iperf3 파싱)."""

# app/runner.py
async def run_session(req: StartRequest) -> AsyncIterator[MeasurementEvent]:
    """양쪽 서버에 SSH, 측정 실행, 라인 파싱 → 이벤트 yield."""

async def mock_session(req: StartRequest) -> AsyncIterator[MeasurementEvent]:
    """NIC 부재 환경용 generator (rules/measurement.md §데모 모드)."""
```

### 완료 기준

- `pytest tests/test_parser.py` 100% 통과 (snapshot 기반)
- `pytest tests/test_runner.py` mock SSH로 90% 이상 통과
- `python scripts/poc.py --tool mock --duration 5`로 5초간 이벤트 stdout 출력
- 실 NIC 환경에서 `--tool ib_write_bw --duration 10` 1회 라이브 검증 (수동)

### 위험·결정

- `asyncssh.connect`의 known_hosts 정책은 시작부터 strict. mock 환경에선 `~/.ssh/known_hosts` 사용
- perftest server-side 백그라운드 PID 추적: `asyncio.subprocess.Popen` 대신 asyncssh `process` 객체 보관
- **controller self-SSH 정책**: controller가 measurement peer 중 하나일 때 자기 자신에게도 **통일된 SSH로 연결** (subprocess 분기 없음). 이유: ① 코드 단순성, ② 자기 known_hosts 1회 등록 외 부담 없음, ③ 200G 측정 BW에 영향 없음(제어 채널만 ssh, 실 측정은 perftest 직접). 운영 시 `ssh-keyscan localhost >> ~/.ssh/known_hosts` 1회 실행 명시
- **BIDIR 출력 포맷 fixture 캡처 필수**: `ib_write_bw -b` 실행 시 stdout 컬럼이 단방향과 동일한지(합산 단일 라인 vs 두 라인 분리) 미검증. Phase 1 PoC에서 실 NIC fixture 캡처 후 `parse_ib_write_bw_line(line, bidir=True)` 분기 확정 — 미검증 시 합산 단일 라인 가정으로 구현, 실측 후 패치
- **mock_session 위치**: Phase 1 시작부터 `runner.py`에 통합 (별도 모듈 X). PoC 단계에서도 `tool=mock` 동작 가능해야 SSH 환경 부재 시 테스트 가능

## 5. Phase 2 — FastAPI 백엔드

### 목표

Phase 1 runner를 HTTP API로 노출. SSE 채널로 이벤트 스트림.

### 산출물

```
app/
  main.py                FastAPI app, 라우터 등록, /static 마운트, 라이프사이클
  api/
    __init__.py
    measure.py           POST /api/start, /api/stop, GET /api/status
    stream.py            GET /api/stream (SSE — measurement + nic_temp 통합 채널)
    health.py            GET /api/health
  state.py               단일 세션 상태 + asyncio.Queue 기반 pub/sub
  nic_telemetry.py       양쪽 서버 NIC IC + 광 모듈 온도 1Hz 폴링 (mget_temp + ethtool -m), nic_temp 이벤트 발행
tests/
  test_api.py            httpx + ASGI
  test_sse.py
  test_state.py
  test_nic_telemetry.py
```

### 인터페이스

**명명 규약**:
- `SessionStatus` (Pydantic 모델, `schemas.py`): 외부 API 응답 DTO
- `SessionState` (Literal/Enum, `state.py` 내부): 머신 상태값 (`idle` / `connecting` / `running` / `error`)
- 둘은 다른 개념. `SessionStatus.state: SessionState` 관계

```python
# app/schemas.py
class SessionStatus(BaseModel):
    state: Literal["idle", "connecting", "running", "error"] = "idle"
    tool: str | None = None
    started_at: datetime | None = None
    error: dict | None = None

# app/state.py
class SessionManager:
    async def start(self, req: StartRequest) -> SessionStatus
    async def stop(self) -> SessionStatus
    def status(self) -> SessionStatus
    async def subscribe(self) -> AsyncIterator[Event]   # SSE fan-out

# app/nic_telemetry.py
class NicTelemetryPoller:
    """NIC IC + Module 온도 폴링. 측정 SSH와 별도 connection pool 사용."""
    async def start(self) -> None: ...   # 1Hz 폴링 task 시작
    async def stop(self) -> None: ...
    def latest(self) -> NicTelemetry | None: ...

# app/api/measure.py
@router.post("/start", response_model=SessionStatus)
async def start(req: StartRequest, mgr: SessionManager = Depends()) -> SessionStatus: ...

# app/api/stream.py
@router.get("/stream")
async def stream(mgr: SessionManager = Depends()) -> StreamingResponse:
    return StreamingResponse(sse_generator(mgr), media_type="text/event-stream")
```

SSE 이벤트 타입·payload 정본 → `.claude/rules/api.md` §SSE 포맷.

### 완료 기준

- `/api/health` 200 OK
- `/api/start` (tool=mock) → 5초간 SSE `measurement` 이벤트 스트리밍 → `/api/stop`
- `nic_temp` SSE 이벤트는 IDLE/RUNNING 무관 항상 1Hz 발행 (`source: "mock"` 모드 포함)
- 동시 SSE 클라이언트 3개 이상 정상 동작
- 잘못된 입력 (`tool=foo`, `tool=ib_read_lat` + `bidir=true`) → 422
- 이미 RUNNING 상태에서 `/api/start` → 409 + 현재 상태
- NIC 온도 측정 실패(SSH timeout) 시 `server_a_ic_c=None` + 직전 값 유지
- `pytest tests/` 전체 통과

### 위험·결정

- **SSE 큐 정책**: 구독자별 `asyncio.Queue(maxsize=256)`, drop-oldest. 구독자 disconnect 시 즉시 cleanup. 30분 무 트래픽 클라이언트 자동 cleanup → 정책 정본 `rules/api.md` §큐/백프레셔
- heartbeat 15초 (`: ping\n\n`)
- **NIC 텔레메트리 SSH 분리**: `nic_telemetry.py`는 측정 SSH와 별도 `asyncssh.SSHClientConnection` 풀 사용. 측정 시작/종료 사이클과 무관하게 텔레메트리 연속성 보장. fault isolation 목적
- **mget_temp 권한**: 1차 sysfs hwmon (`/sys/class/hwmon/.../temp1_input`) 시도 → 실패 시 `sudo mget_temp` fallback. sudoers NOPASSWD 라인 정책 → `rules/security.md`
- mock generator는 `runner.py`에 `mock_session()` 함수로 통합 (Phase 1부터)
- **CI 워크플로우**: 본 Phase부터 `.github/workflows/ci.yml` 추가 — pytest + ruff (Phase 4 이전이지만 PR 검증에 필요)

## 6. Phase 3 — SvelteKit 프론트

### 목표

UI/UX 사양 구현. mock 백엔드와 통합하여 모든 화면·모션 검증.

### 산출물

```
frontend/
  src/
    routes/
      +layout.svelte
      +page.svelte
    lib/
      components/
        Header.svelte           로고 PNG + bar + 타이틀 (하단 정렬)
        StatusBadge.svelte      IDLE/CONNECTING/RUNNING/ERROR
        HardwareDiagram.svelte  SVG (서버×2 + 트랜시버×2 + IC/MOD overlay + packet flow)
        KpiCards.svelte         BW NOW/AVG/PEAK/LAT 4 카드 (라벨 좌측 accent bar)
        BandwidthChart.svelte   ECharts 시계열 (Y축 동적 200/400)
        NicTempPanel.svelte     4 타일 (IC/MOD × dg5W/dg5R) + 4-line 시계열
        ControlPanel.svelte     Tool/MsgSize/Duration/Direction/Start
      stores/
        measurement.svelte.ts   BW 이벤트
        nic_telemetry.svelte.ts NIC IC + Module 4채널 (1Hz)
        session.svelte.ts       세션 상태
      utils/
        sse.ts
        format.ts
        api.ts
      types/
        api.ts                   백엔드 Pydantic 모델 1:1
    app.css
  static/
    manycore_logo_white.png      mockup/ 에서 이동
    manycore_logo_black.png
    fonts/...
  svelte.config.js
  tailwind.config.js
  vite.config.ts
  package.json
```

### 작업 순서

1. **스캐폴드**: `pnpm create svelte@latest frontend` (skeleton + TS + adapter-static), `mockup/manycore_logo_*.png` → `frontend/static/`로 이동
2. **디자인 토큰**: `tailwind.config.js`에 색상·폰트 등록 (mockup의 CSS 변수 그대로 이식), `app.css`에 폰트 @font-face
3. **stores**: `measurement.svelte.ts` (BW 이벤트 버퍼 + KPI 파생값), `nic_telemetry.svelte.ts` (4채널 IC/MOD), `session.svelte.ts` (상태)
4. **utils**: `sse.ts` (EventSource 래퍼, `measurement` + `nic_temp` + `status` + `error` 4 이벤트 분기), `format.ts` (Gbps/µs/°C 포매터), `api.ts` (start/stop)
5. **컴포넌트**: mockup 구현 그대로 포팅 — Header → StatusBadge → HardwareDiagram → KpiCards → BandwidthChart → NicTempPanel → ControlPanel
6. **모션**: 각 컴포넌트에 GSAP 통합. UI/UX 사양 §7 timelines + mockup 코드의 timeline 그대로 이식
7. **통합**: `+page.svelte`에서 모든 컴포넌트 조립
8. **테스트**: utils 단위 테스트, 컴포넌트 렌더링 테스트, mockup 시각 회귀 비교 (수동)

### 완료 기준

- `pnpm dev`로 localhost:5173에서 mock 모드 정상 동작
- `pnpm build` 후 `frontend/build/` 정적 파일 생성, FastAPI에 마운트해서 동일 동작
- 1080p 화면에서 레이아웃 깨짐 없음
- 모션 60fps 유지 (Chrome DevTools Performance)
- **mockup 1차 결과물과 시각 일관성 확인** (헤더 정렬, 4채널 타일, 트랜시버 박스, BIDIR 모드 토글 등 모두 재현)

### 위험·결정

- Svelte 5 runes API 안정성: 정식 릴리즈 사용 (`svelte@^5`)
- ECharts dynamic import (SSR 회피): `onMount`에서 import
- adapter-static + 동적 라우트 없음 → fallback `index.html` 충분
- **Tailwind CSS v4 + SvelteKit 호환성** — v4는 PostCSS 통합 방식이 v3와 다름. `pnpm create svelte`가 생성하는 기본 `package.json`의 의존성과 충돌 여부를 스캐폴드 직후 검증 필요. 충돌 시 v3로 다운그레이드 검토 (vite-plugin-svelte v4와 안정 조합 우선)

## 7. Phase 4 — 통합 + 운영 (Docker Compose 패키징)

### 목표

부스 시연을 위한 운영 자동화. **Docker Compose** 채택 (의존성 격리 + inspection-system과 동일 패턴 + 재시작 단순).

### 패키징 아키텍처

```
controller-host (dg5W 또는 dg5R 한 쪽 겸함)
  │
  ├─ docker (이미 설치 가정)
  ├─ /etc/p2p-monitor/        SSH 키, known_hosts, .env  (호스트 측)
  ├─ /var/log/p2p-monitor/    컨테이너 로그
  └─ systemd: p2p-monitor.service → docker compose up 호출

Container: p2p-monitor (single)
  ├─ Python 3.12 slim + uv (multi-stage 빌드)
  ├─ Frontend SvelteKit 빌드 결과 정적 서빙 (8080)
  ├─ asyncssh — host의 측정 도구는 SSH로 호출 (컨테이너에 OFED 불필요)
  └─ volumes:
       /etc/p2p-monitor (ro)
       /var/log/p2p-monitor (rw)
```

### 산출물

```
Dockerfile                     multi-stage:
                                 stage 1) node + pnpm — frontend build
                                 stage 2) python:3.12-slim + uv sync + frontend/build 복사
docker-compose.yml             단일 서비스, restart: unless-stopped, 8080:8080,
                               volumes (/etc, /var/log), env_file: .env
systemd/
  p2p-monitor.service          ExecStart: docker compose -f /opt/p2p-monitor/docker-compose.yml up
                               ExecStop: docker compose down
                               Restart: always
Makefile                       install / run / demo / build / logs / restart / down
scripts/
  install.sh                   1회 setup:
                                 1. /etc/p2p-monitor/ 디렉터리 생성, 권한 700
                                 2. SSH 키 생성 (ssh-keygen -t ed25519)
                                 3. ssh-copy-id (PW로 1회 → dg5W, dg5R)
                                 4. ssh-keyscan known_hosts 등록
                                 5. .env 인터랙티브 입력 (또는 기존 .env 사용)
                                 6. docker compose pull/build
                                 7. systemctl enable --now p2p-monitor
                                 8. health-check.sh 호출
  health-check.sh              부팅 후 /api/health 30초 polling, exit 0/1
  uninstall.sh
README.md                      설치·시연·트러블슈팅 절차
.github/workflows/ci.yml       (Phase 2 시 추가됨, Phase 4에서 Docker build 단계 추가)
```

### 작업 순서

1. **Dockerfile + docker-compose.yml** — multi-stage 빌드, 로컬에서 `docker compose build` 검증
2. **install.sh / health-check.sh** — fresh VM 또는 컨테이너에서 시뮬레이션 검증
3. **systemd unit** — docker compose wrapper. User는 root (docker 권한)
4. **Makefile** — 운영 명령 단축
5. **README 운영 절차**:
   - 사전 조건: docker 설치, controller 호스트 (dg5W 또는 dg5R 한 쪽), 양쪽 서버 RoCE 동작, SSH 패스워드 1회 가용
   - 설치: `sudo bash scripts/install.sh`
   - 데모: `make demo` (MEASUREMENT_TOOL=mock 으로 컨테이너 띄움)
   - 시연 절차 (부팅 자동시작 → IDLE 표시 → SPACE/UI → START → STOP)
   - 트러블슈팅: SSH 키 / 컨테이너 로그 / health-check 실패
6. **CI Docker 빌드 단계 추가**: PR마다 `docker compose build` 성공 검증
7. **1080p 디스플레이 리허설**:
   - 자동 부팅 → systemd 자동 시작 → 화면 IDLE
   - 키보드/마우스 컨트롤 검증
   - **30분 무인 가동** 안정성 확인 (메모리 / SSE 누수 / SSH 연결 안정)

### 완료 기준

- `docker compose up` 시 정상 기동 (컨테이너 healthy, 8080 응답)
- systemd reboot 후 docker compose 자동 시작
- CI 모든 PR에서 `docker compose build` 통과
- README 절차대로 fresh 머신에서 동작 재현 가능
- 1080p 부스 환경 30분 무인 가동 안정 (메모리·SSE·SSH 누수 없음)

## 8. Phase 5 — 옵션 기능 (시간 여유 시)

| 기능 | 우선순위 | 비고 |
|------|---------|------|
| 메시지 사이즈 스윕 (`-s 64..1M`) | 높음 | 시각적 임팩트 큼 |
| IB switch counter 수집 | 중 | 스위치 경유 토폴로지 가정 |
| 측정 결과 PNG 캡처 | 중 | 시연 후 관람객에게 제공 |
| 3D 하드웨어 다이어그램 (Threlte) | 중 | 시각 임팩트 |
| 다국어 (영어 토글) | 낮음 | 해외 전시 |
| QR 코드로 실시간 결과 공유 | 낮음 | 관람객 모바일 |

## 9. 마일스톤 / 일정 (가이드)

> 실제 일정은 사용자 확정 후 갱신.

| 단계 | 추정 (개발일) | 누적 |
|------|--------------|------|
| Phase 0 (문서) | 1 | 1 |
| Phase 1 (PoC) | 2 | 3 |
| Phase 2 (백엔드) | 2 | 5 |
| Phase 3 (프론트) | 3~4 | 8~9 |
| Phase 4 (통합) | 1~2 | 9~11 |
| Phase 5 (옵션) | 가변 | — |

## 10. 의존성 합의

### Python (`pyproject.toml`)

```
[project]
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.32",
  "asyncssh>=2.18",
  "pydantic>=2.10",
  "pydantic-settings>=2.6",
  "structlog>=24.4",
]
[dependency-groups]
dev = [
  "pytest>=8.3",
  "pytest-asyncio>=0.24",
  "pytest-cov>=5.0",
  "httpx>=0.28",
  "ruff>=0.8",
]
```

### Frontend (`package.json`)

```
"dependencies": {
  "svelte": "^5",
  "@sveltejs/kit": "^2",
  "@sveltejs/adapter-static": "^3",
  "echarts": "^5",
  "gsap": "^3",
  "lucide-svelte": "^0.460"
},
"devDependencies": {
  "vite": "^5",
  "@sveltejs/vite-plugin-svelte": "^4",
  "typescript": "^5",
  "tailwindcss": "^4",
  "vitest": "^2",
  "@testing-library/svelte": "^5",
  "jsdom": "^25"
}
```

## 11. 교차검증 대상

본 계획서가 1차 완성된 후 다음 에이전트 검토를 받고 피드백 반영:

- **arch-plan-reviewer**: 아키텍처(단일 controller, SSE, mock generator) 설계 적정성
- **impl-plan-reviewer**: 모듈 분할·인터페이스 일관성, Phase 의존 그래프
- **harness-doc-reviewer**: 룰 파일 + CLAUDE.md + 본 계획서의 일관성·중복

검토 후 차이가 있으면 본 문서 갱신 → 다시 검증 (사용자가 "이후 몇 번의 구현문서 교차검증 후 구현 시작" 명시).
