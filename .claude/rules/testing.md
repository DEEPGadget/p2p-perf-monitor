# 테스트 규칙

## Python (백엔드)

### 도구

- `pytest` + `pytest-asyncio`
- `httpx` (FastAPI ASGI 직접 호출)
- mock: `unittest.mock` stdlib만 (`pytest-mock` 등 추가 패키지 도입 금지)
- coverage: `pytest --cov=app --cov-report=term-missing`

### 디렉터리

```
tests/
  conftest.py            공통 fixture (TestClient, mock asyncssh 등)
  test_parser.py         perftest/iperf3 출력 파싱 (snapshot)
  test_runner.py         SSH 오케스트레이션 (asyncssh mock)
  test_api.py            /api/* 엔드포인트
  test_sse.py            SSE 채널 (이벤트 발행/구독 단위)
  test_state.py          state 머신 (IDLE → RUNNING → IDLE/ERROR)
  fixtures/
    perftest_ib_write_bw_200g_uni.txt    실측 캡처 (단방향)
    perftest_ib_write_bw_200g_bidir.txt  실측 캡처 (`-b` 옵션, Phase 1 필수)
    perftest_ib_read_lat.txt
    iperf3_tcp_8streams.json             단방향
    iperf3_tcp_bidir.json                `--bidir` 옵션
    iperf3_failed.json                   에러 케이스
```

> Fixture 목록 정본은 본 파일. `docs/implementation-plan.md` Phase 1 산출물도 동일.

### 명령

```bash
uv run pytest tests/ -x -q              # 빠른 피드백
uv run pytest tests/ -v --cov=app       # 상세 + coverage
uv run pytest tests/ -m "not live"      # CI 기본 (라이브 NIC 제외)
uv run pytest tests/ -m live            # 실 NIC 환경에서만
```

### 마커

- `@pytest.mark.live`: 실 NIC + 두 서버 SSH 가능. CI 제외, self-hosted runner에서만
- `@pytest.mark.slow`: 30초 이상 소요. 별도 실행

### 작성 원칙

- 명명: `test_<대상>_<조건>_<기대>`
  - 예: `test_parser_ib_write_bw_normal_returns_event`
  - 예: `test_runner_ssh_timeout_emits_error_event`
- arrange / act / assert 분리
- mock은 가능한 한 좁게. SSH 전체 mock보다 `asyncssh.connect` 만 patch
- snapshot: 실제 측정 도구 출력을 `tests/fixtures/`에 캡처 → parser 호출 → dict 비교
  - 200G 환경 실측 캡처를 우선. 추정값으로 fixture 만들지 말 것

### 커버리지 목표

| 영역 | 목표 |
|------|------|
| `app/parser.py` | 100% (결정론적 파싱) |
| `app/api/*` | 80%+ |
| `app/runner.py` | 60%+ (실 SSH는 라이브 마커로 보강) |
| `app/state.py` | 90%+ |
| 전체 | 75%+ |

CI 임계값 강제는 v1 이후. 초기엔 수치 보고만.

## Frontend (TypeScript)

### 도구

- `vitest` (Vite 통합)
- `@testing-library/svelte` (컴포넌트 테스트)
- `@playwright/test` (E2E, 옵션)

### 디렉터리

```
frontend/
  src/
    lib/
      utils/
        format.test.ts
        sse.test.ts
      components/
        KpiCards.test.ts
        BandwidthChart.test.ts
  tests-e2e/             (옵션, Phase 4 이후)
    home.spec.ts
```

### 명령

```bash
cd frontend
pnpm test                # vitest watch 모드
pnpm test --run          # 1회 실행 (CI)
pnpm test:e2e            # playwright
```

### 작성 원칙

- 유틸 함수(`format.ts`, `sse.ts`): 단위 테스트 100%
- 컴포넌트: 렌더링·상호작용 위주. 시각 회귀(visual regression)는 Phase 4 이후
- 모션·애니메이션은 테스트 대상 외 (수동 검증)

## CI

- GitHub Actions 워크플로우 `.github/workflows/ci.yml`
- 매 PR 실행:
  - Python: `ruff check`, `ruff format --check`, `pytest -m "not live"`
  - Frontend: `pnpm install --frozen-lockfile`, `pnpm test --run`, `pnpm build`
- 라이브 테스트: self-hosted runner 또는 `workflow_dispatch` 수동 트리거

## 통합 테스트 (라이브)

- 실 NIC 환경에서만:
  - `pytest -m live tests/test_integration_*.py`
- 절차:
  1. 두 서버 SSH 가능, ConnectX-6 동작 확인
  2. `MEASUREMENT_TOOL=perftest uv run uvicorn app.main:app --port 8080`
  3. `/api/start` POST → SSE 구독 → 60초 측정 → `/api/stop`
  4. 마지막 이벤트 `bw_avg_gbps > 150` 검증 (200G NIC peak 90% 이상)

## 데모 모드 검증

- `MEASUREMENT_TOOL=mock` 으로 항상 동작 가능
- CI에서 통합 smoke test로 `tool=mock` 시나리오 1회 실행 (5초)
