# API 규칙

> 워크스페이스 `rules/api.md` 위에 프로젝트 한정 규칙. 충돌 시 본 파일 우선.

## 라우터 구조

- `app/api/measure.py`: 측정 제어 (start/stop/status)
- `app/api/stream.py`: 실시간 이벤트 (SSE)
- 신규 라우터는 `app/api/<area>.py` 로 추가하고 `main.py`에서 `include_router(prefix="/api")`

## 엔드포인트 컨벤션

| Method | Path | 역할 | 응답 |
|--------|------|------|------|
| GET    | `/api/status` | 현재 세션 상태 | `SessionStatus` JSON |
| POST   | `/api/start`  | 측정 시작 | `SessionStatus` JSON |
| POST   | `/api/stop`   | 측정 중지 | `SessionStatus` JSON |
| GET    | `/api/stream` | 측정 이벤트 SSE | `text/event-stream` |
| GET    | `/api/health` | 헬스체크 (SSH 미시도, FastAPI alive만) | `{"ok": true}` |

- 경로는 항상 `/api/` prefix
- POST body는 Pydantic 모델로 검증. raw dict 금지
- 응답도 Pydantic 모델로 직렬화. `JSONResponse(dict)` 금지

## 동시성 정책

- 단일 세션. 이미 RUNNING 상태에서 `/api/start` 호출 시 `409 Conflict` + 현재 상태 반환
- `/api/stop`은 idempotent. IDLE 상태에서 호출해도 200
- SSE 클라이언트는 다중 허용 (브라우저 여러 개 연결 가능)

## SSE 포맷

```
event: measurement
data: {"ts": "2026-05-04T12:00:00Z", "bw_gbps": 187.4, "lat_us": 1.8, ...}

event: status
data: {"state": "running", "tool": "perftest", "started_at": "..."}

event: error
data: {"code": "ssh_timeout", "message": "Server B not reachable"}
```

- 이벤트 타입은 `measurement` / `status` / `error` 3종으로 한정
- 각 이벤트는 `data:` 1줄 JSON. 멀티라인 금지
- heartbeat: 15초마다 `: ping` 코멘트 라인 (연결 유지용)

## 에러 처리

- 입력 검증 실패: FastAPI 기본 422 사용
- SSH 연결 실패: `503 Service Unavailable` + `{"code": "ssh_unreachable", "host": "..."}`
- 측정 도구 실행 실패: `500 Internal Server Error` + `{"code": "measure_failed", "stderr_tail": "..."}`
- 에러 메시지에 password·키·환경변수 값 포함 금지 → `.claude/rules/security.md`

## CORS

- 운영: 동일 origin (FastAPI가 정적 + API 모두 서빙) → CORS 비활성
- 개발 모드: localhost 다른 포트에서 프론트 띄울 시만 `dev` 환경변수로 활성화
