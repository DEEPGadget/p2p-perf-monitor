# 측정 규칙

> NIC 환경: Mellanox ConnectX-7 200G, RoCE v2, MLNX_OFED 사전 설치 → `context/nic-environment.md`

## 지원 도구

| 도구 | 통신 방식 | 우선순위 | 비고 |
|------|----------|---------|------|
| `ib_write_bw` (perftest) | RDMA Write — RoCE | **메인** | NIC peak BW 시각화 |
| `ib_read_lat` (perftest) | RDMA Read — RoCE | **메인** | sub-µs 지연 시각화 |
| `iperf3` | TCP | 옵션 (비교 데모) | RDMA 대비 GAP 보여주기 좋음 |
| `mock` (내부 generator) | 사인파+노이즈 | 데모 모드 | NIC 없는 환경 UI 검증 |

`ib_send_bw` 메시지 사이즈 스윕은 v1 이후 기능 (Phase 5).

## perftest 호출 규약

### `ib_write_bw` 양방향 실행

**Server A (RDMA peer 1)**:
```
ib_write_bw -d <NIC_DEVICE_A> -F --report_gbits \
            -D <duration_sec> -x <RDMA_GID_INDEX> \
            -s <msg_size> -q <qp_count>
```

**Server B (RDMA peer 2, A의 IP를 인자로)**:
```
ib_write_bw -d <NIC_DEVICE_B> -F --report_gbits \
            -D <duration_sec> -x <RDMA_GID_INDEX> \
            -s <msg_size> -q <qp_count> <SERVER_A_HOST>
```

옵션 의미:
- `-F`: NUMA 자동 바인딩 비활성화 (수동 제어 우선)
- `--report_gbits`: 단위 Gb/s 통일
- `-D <sec>`: 총 측정 시간
- `-x <gid>`: RoCE v2 GID index (기본 3)
- `-s <bytes>`: 메시지 사이즈
- `-q <n>`: Queue Pair 수 (병렬도). 200G는 보통 1~4면 충분
- `-b` (선택): **bidirectional** — 양방향 동시 측정. 결과 BW는 양방향 합산값 (이상 시 ~380 Gb/s). 단방향(`-b` 없음) 시 ~190 Gb/s

### `ib_read_lat` (지연 측정)

```
# Server A (server)
ib_read_lat -d <DEV> -F -x <GID> -D <sec>
# Server B (client)
ib_read_lat -d <DEV> -F -x <GID> -D <sec> <SERVER_A_HOST>
```

`--report_gbits` 미지원 — latency는 µs 단위 출력.

### iperf3 호출 규약

```
# Server A
iperf3 -s -p 5201 -1
# Server B (단방향)
iperf3 -c <SERVER_A_HOST> -p 5201 -t <duration_sec> -P <streams> -J
# Server B (양방향)
iperf3 -c <SERVER_A_HOST> -p 5201 -t <duration_sec> -P <streams> --bidir -J
```

- `-J`: JSON 출력 강제 (파싱 단순화)
- `-P <n>`: 병렬 스트림 (200G TCP는 다중 스트림 필수, 4~8 권장)
- `-1`: server 1회 세션 후 종료
- `--bidir`: bidirectional. 결과 JSON에 `intervals[].sum_sent` + `intervals[].sum_received` 합산 필요

## 프로세스 라이프사이클

```
1. controller → SSH(server-A): server 모드 백그라운드 기동
2. controller: 200ms 대기 (server 리스닝 확인)
3. controller → SSH(server-B): client 실행 (server-A IP 인자)
4. controller: client stdout 라인 단위 수신 → parser → SSE 발행
5. /api/stop 또는 client 정상 종료 시:
   a. client 채널: SIGTERM 송신, 5초 grace, 미종료 시 SIGKILL
   b. server-A 채널: 동일하게 종료
   c. SSH 세션 클로즈
6. 양 채널 종료 확인 후 state=IDLE
```

PID 추적은 asyncssh `process` 객체 보관. 명시적 종료 미보장 환경 대비 `pkill -f ib_write_bw` fallback.

## 실패 처리

- SSH 연결 timeout (3초): `error` SSE + state=ERROR. 양쪽 채널 정리
- server-A 기동 후 5초 내 client 미연결: server-A 종료, ERROR 발행
- stderr RDMA 에러 패턴 매칭 → ERROR + tail 200줄
  - `Failed to modify QP`
  - `Couldn't allocate MR`
  - `Failed to register MR`
  - `Couldn't post receive`
- iperf3 실패: `error` 필드 (JSON) 우선 확인

## 파싱 규칙

### `ib_write_bw` 출력

```
---------------------------------------------------------------------------------------
                    RDMA_Write BW Test
 Dual-port       : OFF		Device         : mlx5_0
 Number of qps   : 1		Transport type : IB
 ...
---------------------------------------------------------------------------------------
 #bytes     #iterations    BW peak[Gb/sec]    BW average[Gb/sec]   MsgRate[Mpps]
 65536      5000           198.45             197.82               0.378
 65536      5000           198.50             197.78               0.378
```

- 헤더 / `---` / 빈 줄 / `#bytes`: 무시
- 데이터 라인 정규식: `r'^\s*(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*$'`
- 200G 환경 기대값: `bw_peak ≈ 195~199`, `bw_avg ≈ 190~198`

### `ib_read_lat` 출력

```
 #bytes #iterations    t_min[usec]    t_max[usec]  t_typical[usec]    t_avg[usec]    t_stdev[usec]   99% percentile[usec]   99.9% percentile[usec]
 8       1000           1.45           2.10         1.55              1.58            0.05            1.78                   1.92
```

- `t_avg` → `lat_us` 필드
- `t_min`, `99% percentile` → 옵션으로 별도 필드 보관

### `iperf3 -J` 출력

JSON 파싱:
```python
result = json.loads(stdout)
for interval in result['intervals']:
    bps = interval['sum']['bits_per_second']
    bw_avg_gbps = bps / 1e9
```

`bw_peak_gbps`는 intervals 내 max.

## MeasurementEvent 스키마 (Pydantic)

```python
class MeasurementEvent(BaseModel):
    ts: datetime                       # UTC ISO8601
    msg_size: int                      # bytes
    iterations: int | None
    bw_peak_gbps: float
    bw_avg_gbps: float
    msg_rate_mpps: float | None        # iperf3 fallback에선 None
    lat_us: float | None               # ib_read_lat 모드에서만
    lat_p99_us: float | None
    tool: Literal["perftest", "iperf3", "mock"]
    sub_tool: Literal["ib_write_bw", "ib_read_lat", "iperf3", "mock"] | None
```

- 단위 통일: 대역폭 Gb/s, 지연 µs, 사이즈 bytes
- 미지원 필드는 None
- 모든 도구·서브도구 출력은 본 스키마로 정규화. 프론트는 단일 스키마만 다룸

## 측정 옵션 (사용자 노출)

`/api/start` body로 변경 가능:

| 필드 | 타입 | 기본 | 제약 |
|------|------|-----|------|
| `tool` | enum | `ib_write_bw` | `ib_write_bw` \| `ib_read_lat` \| `iperf3` \| `mock` |
| `duration_sec` | int | 60 | 5..600 |
| `msg_size` | int | 65536 | allowlist `[64, 1024, 8192, 65536, 262144, 1048576]` (perftest 한정) |
| `qp_count` | int | 1 | 1..16 (perftest 한정) |
| `iperf3_streams` | int | 8 | 1..32 (iperf3 한정) |
| `bidir` | bool | `false` | `ib_read_lat`은 미지원(latency는 양방향 의미 없음) — runner에서 거부 |

**bidir 처리**:
- `ib_write_bw`: client 측 명령에 `-b` 추가
- `iperf3`: client 측 명령에 `--bidir` 추가
- `mock`: generator가 양방향 합산값 모사 (~380 Gb/s avg)
- `ib_read_lat`: bidir=true 시 422 응답 (의미 없음)

임의 shell 인자 주입 금지 → `.claude/rules/security.md`

## 데모 모드 (`mock`)

`MEASUREMENT_TOOL=mock` 또는 `/api/start` body `tool="mock"`.

`runner.py`에서 SSH 미사용. 200G NIC 동작을 모사하는 generator:
- 단방향 (`bidir=false`):
  - `bw_avg_gbps`: 사인파(주기 30s, 평균 187, 진폭 8) + 가우시안 노이즈(σ=1.5), cap 199
- 양방향 (`bidir=true`):
  - `bw_avg_gbps`: 사인파(주기 30s, 평균 374, 진폭 14) + 가우시안 노이즈(σ=2.5), cap 396
- `bw_peak_gbps`: avg + uniform(0.5, 1.5)
- `lat_us`: 1.5 ~ 2.0 사이 noise (단방향 한정)
- 발행 주기: 10Hz

UI/UX 디자인 검증 + NIC 없는 환경 시연용.
