# API 규칙

> 워크스페이스 `rules/api.md` 위에 프로젝트 한정 규칙. 충돌 시 본 파일 우선.
> 데이터 스키마 정본 → `.claude/rules/measurement.md` (`MeasurementEvent` / `NicTelemetry`)

## 라우터 구조

- `app/api/measure.py`: 측정 제어 (start/stop/status)
- `app/api/stream.py`: 실시간 이벤트 (SSE — 4 이벤트 통합 채널)
- `app/api/health.py`: health 체크
- 신규 라우터는 `app/api/<area>.py`로 추가하고 `main.py`에서 `include_router(prefix="/api")`

## 엔드포인트 컨벤션

| Method | Path | 역할 | 응답 |
|--------|------|------|------|
| GET    | `/api/status` | 현재 세션 상태 | `SessionStatus` JSON |
| POST   | `/api/start`  | 측정 시작 | `SessionStatus` JSON |
| POST   | `/api/stop`   | 측정 중지 | `SessionStatus` JSON |
| GET    | `/api/stream` | 실시간 SSE (4 이벤트) | `text/event-stream` |
| GET    | `/api/health` | 헬스체크 (SSH 미시도, FastAPI alive만) | `{"ok": true}` |

- 경로는 항상 `/api/` prefix
- POST body는 Pydantic 모델(`StartRequest`)로 검증. raw dict 금지
- 응답도 Pydantic 모델(`SessionStatus`)로 직렬화. `JSONResponse(dict)` 금지
- **명명 단일화**: 응답·status 모델은 `SessionStatus`로 통일. `state.py`의 내부 머신 enum은 `SessionState`로 구분 — 둘은 다른 개념(외부 응답 DTO vs 내부 상태값)

## 동시성 정책

- 단일 세션. 이미 RUNNING 상태에서 `/api/start` → `409 Conflict` + 현재 상태 반환
- `/api/stop`은 idempotent. IDLE 상태에서 호출해도 200
- SSE 클라이언트는 다중 허용 (브라우저 여러 개 연결 가능)

## SSE 포맷

`/api/stream` 단일 채널에서 **4종 이벤트** 발행:

```
event: measurement
data: {"ts":"2026-05-04T12:00:00Z","msg_size":65536,"iterations":5000,
       "bw_peak_gbps":198.45,"bw_avg_gbps":197.82,"msg_rate_mpps":0.378,
       "lat_us":null,"lat_p99_us":null,"tool":"perftest","sub_tool":"ib_write_bw"}

event: nic_temp
data: {"ts":"2026-05-04T12:00:00Z","server_a_ic_c":62.3,"server_b_ic_c":64.1,
       "server_a_module_c":41.5,"server_b_module_c":43.0,"source":"mget_temp+ethtool"}

event: status
data: {"state":"running","tool":"ib_write_bw","started_at":"2026-05-04T11:59:00Z","error":null}

event: error
data: {"code":"ssh_timeout","host":"10.x.x.10","message":"connect timeout 3s"}
```

발행 정책:
- `measurement`: 측정 중에만 발행. perftest/iperf3/mock 출력 1라인당 1 이벤트 (10Hz 수준)
- `nic_temp`: **IDLE/RUNNING 무관 항상 1Hz 발행** — 시스템 health 시각화
- `status`: 상태 전이 시점에만 (`idle`→`connecting`→`running`→`idle`/`error`)
- `error`: SSH·측정 도구·텔레메트리 실패 시. 발행 후에도 SSE 채널 유지(다음 시도 가능)
- 페이로드는 `data:` 1줄 JSON. 멀티라인 금지
- heartbeat: 15초마다 `: ping\n\n` 코멘트 라인 (연결 유지용)

스키마 필드 정의 → `.claude/rules/measurement.md`. SSE 페이로드는 해당 Pydantic 모델 `model_dump_json()` 결과.

### 큐 / 백프레셔 정책

- 구독자별 `asyncio.Queue(maxsize=256)`
- 큐 가득 시 **drop-oldest** (가장 오래된 이벤트 폐기) — 느린 클라이언트 때문에 publisher 정지하지 않음
- 클라이언트 disconnect 감지 시 즉시 `task_done()` + 큐 cleanup (메모리 누수 방지)
- 30분 무 트래픽 클라이언트는 자동 cleanup (idle timeout)

## 에러 처리

### HTTP 응답 에러 코드

| 상황 | HTTP | 응답 body |
|------|------|----------|
| 입력 검증 실패 | 422 | FastAPI 기본 |
| SSH 연결 실패 | 503 | `{"code":"ssh_unreachable","host":"..."}` |
| 이미 RUNNING 상태 | 409 | `{"code":"already_running","current":SessionStatus}` |
| `bidir=true` + `tool=ib_read_lat` | 422 | `{"code":"bidir_not_supported","tool":"ib_read_lat"}` |
| 측정 도구 실행 실패 | 500 | `{"code":"measure_failed","stderr_tail":"..."}` |

### SSE 이벤트 에러 코드 카탈로그

| code | 발생 |
|------|------|
| `ssh_unreachable` | SSH connect 실패 (네트워크·DNS) |
| `ssh_timeout` | SSH 명령 timeout |
| `ssh_auth_failed` | 키 인증 실패 |
| `measure_failed` | perftest/iperf3 비정상 종료, RDMA QP 에러 등 |
| `temp_polling_failed` | mget_temp/ethtool 폴링 실패 (직전 값 유지) |
| `parse_failed` | 측정 도구 출력 파싱 실패 |

신규 코드 추가 시 본 표를 갱신.

### 응답·로그 보안

- 에러 메시지에 password·키·환경변수 값 포함 금지 → `.claude/rules/security.md`
- `stderr_tail`은 200줄까지만 (보안 + payload 크기)

## CORS

- 운영: 동일 origin (FastAPI가 정적 + API 모두 서빙) → CORS 비활성
- 개발: `DEV_CORS=1` 환경변수 시 `localhost:5173` 허용 (Vite dev)
