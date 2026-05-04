# 보안 규칙

> 본 파일은 프로젝트 한정. 워크스페이스 글로벌 보안 규칙 위.

## 위협 모델

- 운영 환경: **전시 부스 폐쇄망** 가정. 인증 없이 접근 허용
- 그러나 측정 도구는 **shell 명령 실행** 권한이 있는 SSH 세션을 사용 → 입력 sanitization 필수
- 서버 ↔ 컨트롤러 간 SSH 키가 노출되면 두 측정 서버의 root 또는 deepgadget 권한 손상 가능

## SSH 접근

- 인증 방식: **공개키만**. 패스워드 인증 금지
- 키 경로: `.env` `SSH_KEY_PATH` (절대경로). 권장 `/etc/p2p-monitor/id_ed25519`
- 키 파일 권한: 600. 부팅 시 검증, 미충족 시 거부 후 종료
- known_hosts 검증 필수:
  - `SSH_KNOWN_HOSTS` 환경변수로 명시 경로
  - asyncssh: `connect(known_hosts=os.environ['SSH_KNOWN_HOSTS'])`
  - **`StrictHostKeyChecking=no` 또는 `known_hosts=None` 금지**
- 키 회전 절차는 운영 문서(`README.md`)에 기록
- SSH 사용자: 측정 도구 실행에 필요한 최소 권한 계정 (root 비권장, `deepgadget` 정도)

## 시크릿 관리

- `.env`는 **git ignored**. `.env.example`만 커밋
- 로그·에러 응답에 `.env` 값 노출 금지
- 디버그/dump 엔드포인트 만들지 않음 (`/api/debug/env` 등)
- structlog 사용 시 민감 키 필터: `ssh_key_path`, `password`, `private_key`

## 입력 검증

- `/api/start` body는 **Pydantic 모델만** 받음
  - `model_config = ConfigDict(extra='forbid')` — 추가 필드 거부
- shell 명령 구성 시 사용자 입력은 **allowlist만 통과**:
  - `tool`: `Literal["ib_write_bw", "ib_read_lat", "iperf3", "mock"]`
  - `msg_size`: 명시 정수 리스트 (`[64, 1024, 8192, 65536, 262144, 1048576]`)
  - `duration_sec`: int 5..600
  - `qp_count`: int 1..16
  - `iperf3_streams`: int 1..32
- f-string으로 셸 명령 구성 금지. asyncssh **인자 리스트** 사용:

```python
# Good — 인자 분리
await conn.run(['ib_write_bw', '-d', device, '-F', '--report_gbits',
                '-D', str(duration), '-x', str(gid), '-s', str(msg_size),
                '-q', str(qp_count), peer_host])

# Bad — f-string 셸 구성 (금지)
await conn.run(f'ib_write_bw -d {device} -F -D {duration} {peer_host}')
```

- `device` 등 환경변수 값도 정규식 검증: `r'^mlx\d+_\d+$'`

## 네트워크 노출

- 기본: 폐쇄망 부스, 인증 없음
- 외부망 노출 시(예: 회사 데모 페이지) 운영 절차에서 추가 보호:
  - reverse proxy (nginx/caddy) + basic auth 또는 IP allowlist
  - FastAPI 자체에는 인증 미구현 (단순성 우선)
- FastAPI 바인드: `BIND_HOST=0.0.0.0`은 기본 허용. localhost만 노출 시 `127.0.0.1` 명시

## 측정 도구 권한

- `ib_write_bw` 등 perftest는 일반 사용자로 실행 가능 (RDMA 디바이스 권한만 있으면 됨)
- `iperf3`도 일반 사용자
- root 불필요. SSH 사용자가 RDMA 디바이스(`/dev/infiniband/*`) 접근 권한만 가지면 됨
- 권한 부족 시 → 운영 문서에 udev rule 또는 그룹 추가 안내

## 로그

- structlog (옵션) 또는 stdlib logging. 포맷: JSON 구조화
- ERROR 시 응답에 stdout/stderr tail은 200줄까지만
- 측정 stdout 전체는 `/var/log/p2p-monitor/<session_id>.log` 로컬 보관 (옵션)
- 다음 키는 마스킹 또는 제외:
  - `ssh_key_path`, `private_key`, `.env` 원문
  - 사용자 IP / 호스트 정보는 메트릭 외 노출 안 함

## 의존성

- 외부 패키지 추가 시 `pyproject.toml` (Python) / `package.json` (Frontend) 명시 + PR 본문에 사유
- GitHub Dependabot 알림은 PR 우선 처리
- npm postinstall 훅으로 외부 다운로드 받는 패키지 거부

## CSP (Content Security Policy) — 운영 추가 시

- `default-src 'self'`
- `script-src 'self'` (인라인 금지, hash 또는 nonce 필요 시 별도)
- `connect-src 'self'` (SSE 엔드포인트 자체 origin)
- `img-src 'self' data:` (SVG inline 허용)
- 외부 CDN 미사용이라 위 정책으로 충분

## 시연 시 주의

- 부스 디스플레이는 관람객에게 노출 — 호스트명/IP/내부 토폴로지 등 노출 가능
- `.env` 값 직접 표시 금지. 푸터의 NIC 디바이스명·OFED 버전 정도까지만 OK
- 화면 캡처 가능성 가정하고 작성
