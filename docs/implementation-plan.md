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
- [ ] `pyproject.toml` 초안 (의존성: fastapi, asyncssh, pydantic, uvicorn, structlog)
- [ ] `frontend/package.json` 초안 (svelte, sveltekit, vite, tailwind, echarts, gsap, lucide)
- [ ] GUI 목업 (정적 HTML 또는 SvelteKit 페이지) — 디자인 검증

### 완료 기준

- 모든 문서가 1차 작성 완료 + 사용자 검토 완료
- arch-plan-reviewer / impl-plan-reviewer / harness-doc-reviewer 교차검증 1회 이상
- 검증 피드백 반영 PR 머지

## 4. Phase 1 — 측정 PoC

### 목표

두 서버에 SSH로 perftest 실행하고 stdout을 파싱해서 표준 스키마(MeasurementEvent)로 출력하는 CLI 스크립트.

### 산출물

```
app/
  __init__.py
  schemas.py             MeasurementEvent, StartRequest, SessionStatus
  parser.py              parse_ib_write_bw_line, parse_ib_read_lat_line, parse_iperf3_json
  runner.py              run_perftest_session(config) -> AsyncIterator[MeasurementEvent]
  config.py              load .env
tests/
  fixtures/
    perftest_ib_write_bw_200g.txt    (가능하면 실측, 없으면 합성)
    perftest_ib_read_lat.txt
    iperf3_tcp_8streams.json
  test_parser.py
  test_runner.py
scripts/
  poc.py                 CLI: python scripts/poc.py --tool ib_write_bw --duration 30
```

### 인터페이스

```python
# app/schemas.py
class StartRequest(BaseModel):
    tool: Literal["ib_write_bw", "ib_read_lat", "iperf3", "mock"] = "ib_write_bw"
    duration_sec: int = Field(60, ge=5, le=600)
    msg_size: int = 65536           # allowlist 검증 별도
    qp_count: int = 1
    iperf3_streams: int = 8
    bidir: bool = False              # ib_write_bw / iperf3 한정. ib_read_lat 시 422
    model_config = ConfigDict(extra="forbid")

class MeasurementEvent(BaseModel):
    ts: datetime
    msg_size: int
    iterations: int | None
    bw_peak_gbps: float
    bw_avg_gbps: float
    msg_rate_mpps: float | None
    lat_us: float | None
    lat_p99_us: float | None
    tool: Literal["perftest", "iperf3", "mock"]
    sub_tool: Literal["ib_write_bw", "ib_read_lat", "iperf3", "mock"] | None

class NicTelemetry(BaseModel):
    """양쪽 NIC IC + 광 트랜시버 모듈 온도. 측정 BW와 별도 채널, 1Hz 폴링."""
    ts: datetime
    server_a_ic_c: float | None         # ASIC IC 온도
    server_b_ic_c: float | None
    server_a_module_c: float | None     # 광 트랜시버 모듈 온도 (QSFP56)
    server_b_module_c: float | None
    source: Literal["mget_temp+ethtool", "sysfs+ethtool", "mlxlink", "mock"]

# app/parser.py
def parse_ib_write_bw_line(line: str) -> MeasurementEvent | None: ...
def parse_ib_read_lat_line(line: str) -> MeasurementEvent | None: ...
def parse_iperf3_json(text: str) -> list[MeasurementEvent]: ...

# app/runner.py
async def run_session(req: StartRequest) -> AsyncIterator[MeasurementEvent]:
    """양쪽 서버에 SSH, 측정 실행, 라인 파싱 → 이벤트 yield."""
```

### 완료 기준

- `pytest tests/test_parser.py` 100% 통과 (snapshot 기반)
- `pytest tests/test_runner.py` mock SSH로 90% 이상 통과
- `python scripts/poc.py --tool mock --duration 5`로 5초간 이벤트 stdout 출력
- 실 NIC 환경에서 `--tool ib_write_bw --duration 10` 1회 라이브 검증 (수동)

### 위험·결정

- `asyncssh.connect`의 known_hosts 정책은 시작부터 strict. mock 환경에선 `~/.ssh/known_hosts` 사용
- perftest server-side 백그라운드 PID 추적: `asyncio.subprocess.Popen` 대신 asyncssh `process` 객체 보관

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

```python
# app/state.py
class SessionState(BaseModel):
    state: Literal["idle", "connecting", "running", "error"] = "idle"
    tool: str | None = None
    started_at: datetime | None = None
    error: dict | None = None

class SessionManager:
    async def start(self, req: StartRequest) -> SessionState
    async def stop(self) -> SessionState
    def status(self) -> SessionState
    async def subscribe(self) -> AsyncIterator[Event]   # SSE용

# app/api/measure.py
@router.post("/start", response_model=SessionStatus)
async def start(req: StartRequest, mgr: SessionManager = Depends()) -> SessionStatus: ...

# app/api/stream.py
@router.get("/stream")
async def stream(mgr: SessionManager = Depends()) -> StreamingResponse:
    return StreamingResponse(sse_generator(mgr), media_type="text/event-stream")
```

### 완료 기준

- `/api/health` 200 OK
- `/api/start` (tool=mock) → 5초간 SSE `measurement` 이벤트 스트리밍 → `/api/stop`
- `nic_temp` SSE 이벤트는 IDLE/RUNNING 무관 항상 1Hz 발행 (`source: "mock"` 모드 포함)
- 동시 SSE 클라이언트 3개 이상 정상 동작
- 잘못된 입력 (`tool=foo`) → 422
- 이미 RUNNING 상태에서 `/api/start` → 409 + 현재 상태
- NIC 온도 측정 실패(SSH timeout) 시 `server_a_chip_c=None` + 직전 값 유지
- `pytest tests/` 전체 통과

### 위험·결정

- SSE는 `asyncio.Queue` 기반 fan-out. 구독자 disconnect 시 cleanup 필수 (메모리 누수 방지)
- heartbeat 15초 (`: ping\n\n`)
- mock generator는 `runner.py`에 `mock_session()` 함수로 통합 (별도 모듈 불필요)

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
        Header.svelte / StatusBadge.svelte
        HardwareDiagram.svelte
        KpiCards.svelte
        BandwidthChart.svelte
        ControlPanel.svelte
      stores/
        measurement.svelte.ts
        session.svelte.ts
      utils/
        sse.ts
        format.ts
        api.ts
      types/
        api.ts
    app.css
  static/
    logo.svg
    fonts/...
  svelte.config.js
  tailwind.config.js
  vite.config.ts
  package.json
```

### 작업 순서

1. **스캐폴드**: `pnpm create svelte@latest frontend` (skeleton + TS + adapter-static)
2. **디자인 토큰**: `tailwind.config.js`에 색상·폰트 등록, `app.css`에 폰트 @font-face
3. **stores**: `measurement.svelte.ts` (이벤트 버퍼 + KPI 파생값), `session.svelte.ts` (상태)
4. **utils**: `sse.ts` (EventSource 래퍼), `format.ts` (Gbps/µs 포매터), `api.ts` (start/stop)
5. **컴포넌트**: 위에서 아래 순으로 — Header → StatusBadge → HardwareDiagram → KpiCards → BandwidthChart → ControlPanel
6. **모션**: 각 컴포넌트에 GSAP 통합. UI/UX 사양 §7 timelines 구현
7. **통합**: `+page.svelte`에서 모든 컴포넌트 조립
8. **테스트**: utils 단위 테스트, 컴포넌트 렌더링 테스트

### 완료 기준

- `pnpm dev`로 localhost:5173에서 mock 모드 정상 동작
- `pnpm build` 후 `frontend/build/` 정적 파일 생성, FastAPI에 마운트해서 동일 동작
- 1080p 화면에서 레이아웃 깨짐 없음
- 모션 60fps 유지 (Chrome DevTools Performance)

### 위험·결정

- Svelte 5 runes API 안정성: 정식 릴리즈 사용 (`svelte@^5`)
- ECharts dynamic import (SSR 회피): `onMount`에서 import
- adapter-static + 동적 라우트 없음 → fallback `index.html` 충분

## 7. Phase 4 — 통합 + 운영

### 목표

부스 시연을 위한 운영 자동화.

### 산출물

```
systemd/
  p2p-monitor.service
Makefile
README.md (시연 절차)
.env.example
.github/workflows/ci.yml
scripts/
  install.sh           OFED 설치 검증, perftest 동작 확인, systemd 등록
  health-check.sh      부팅 후 /api/health 확인
```

### 작업 순서

1. systemd unit 작성 (User=p2p-monitor, ExecStart=uvicorn, Restart=always)
2. Makefile 작성 (`install`, `run`, `demo`, `test`, `lint`, `build`)
3. CI 워크플로우 (Python lint+test, Frontend test+build)
4. README 운영 절차:
   - 사전 조건 (OFED, NIC, SSH 키)
   - 설치 (`make install`)
   - 데모 모드 (`make demo`)
   - 실 측정 (`/api/start` POST 또는 UI 버튼)
   - 트러블슈팅
5. 1080p 디스플레이 1회 리허설:
   - 자동 부팅 → 서비스 자동 시작 → 화면에 IDLE 표시
   - 키보드 SPACE → START → 측정 → STOP
   - 30분 무인 가동 안정성 확인

### 완료 기준

- systemd reboot 후 자동 시작
- CI 모든 PR에서 통과
- README 절차대로 fresh 머신에서 동작 재현 가능
- 1080p 부스 환경 30분 무인 가동 안정

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
dev = ["pytest>=8.3", "pytest-asyncio>=0.24", "httpx>=0.28", "ruff>=0.8"]
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
  "vitest": "^2"
}
```

## 11. 교차검증 대상

본 계획서가 1차 완성된 후 다음 에이전트 검토를 받고 피드백 반영:

- **arch-plan-reviewer**: 아키텍처(단일 controller, SSE, mock generator) 설계 적정성
- **impl-plan-reviewer**: 모듈 분할·인터페이스 일관성, Phase 의존 그래프
- **harness-doc-reviewer**: 룰 파일 + CLAUDE.md + 본 계획서의 일관성·중복

검토 후 차이가 있으면 본 문서 갱신 → 다시 검증 (사용자가 "이후 몇 번의 구현문서 교차검증 후 구현 시작" 명시).
