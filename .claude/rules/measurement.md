# 측정 규칙

> NIC 환경: Mellanox ConnectX-6 200G, RoCE v2, MLNX_OFED 사전 설치 → `context/nic-environment.md`
>
> **본 파일은 다음 항목의 정본**: 측정 도구·호출 규약·파싱 규칙·`StartRequest`/`MeasurementEvent`/`NicTelemetry` 스키마·NIC 온도 임계값. 다른 문서는 본 파일 참조.

## `MEASUREMENT_TOOL` env vs API `tool` 필드 관계

- **`MEASUREMENT_TOOL` 환경변수**: 카테고리 기본값 — `perftest` / `iperf3` / `mock`
  - 운영 시 부팅 환경에 따라 결정 (NIC 부재 시 `mock`)
  - controller 프로세스 단위 default
- **API body `tool` 필드**: 서브툴 — `ib_write_bw` / `ib_read_lat` / `iperf3` / `mock`
  - `/api/start` 요청별로 override
  - 기본값은 `MEASUREMENT_TOOL` env에서 매핑 (perftest → `ib_write_bw`, 그 외 동일)

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

> ⚠️ **SSH IP vs RDMA IP 구분**: controller가 SSH로 접속하는 호스트는 `SERVER_{A,B}_HOST` (관리망 192.168.1.x). 그러나 perftest 명령의 client peer 인자는 **RDMA IP** (`SERVER_{A,B}_RDMA_IP`, RoCE 망 25.47.1.x)를 사용해야 함. 두 망 분리 환경에서 SSH IP를 인자로 넘기면 측정이 관리망으로 흐를 위험.

**Server A (RDMA peer 1)**:
```
# SSH: SERVER_A_HOST 로 접속 (관리망)
ib_write_bw -d <NIC_DEVICE_A> -F --report_gbits \
            -D <duration_sec> -x <RDMA_GID_INDEX> \
            -s <msg_size> -q <qp_count>
```

**Server B (RDMA peer 2, A의 RDMA IP 를 인자로)**:
```
# SSH: SERVER_B_HOST 로 접속 (관리망)
ib_write_bw -d <NIC_DEVICE_B> -F --report_gbits \
            -D <duration_sec> -x <RDMA_GID_INDEX> \
            -s <msg_size> -q <qp_count> <SERVER_A_RDMA_IP>
```

옵션 의미:
- `-F`: NUMA 자동 바인딩 비활성화 (수동 제어 우선)
- `--report_gbits`: 단위 Gb/s 통일
- `-D <sec>`: 총 측정 시간
- `-x <gid>`: RoCE v2 GID index (기본 3)
- `-s <bytes>`: 메시지 사이즈
- `-q <n>`: Queue Pair 수 (병렬도). 200G는 보통 1~4면 충분
- `-b` (선택): **bidirectional** — 양방향 동시 측정. 결과 BW는 양방향 합산값 (이상 시 ~380 Gb/s). 단방향(`-b` 없음) 시 ~190 Gb/s

> ⚠️ **BIDIR 출력 포맷 미검증**: `-b` 옵션 시 stdout 컬럼이 단방향과 동일한지(합산 단일 라인) 또는 두 라인으로 분리 출력되는지 실 NIC 환경에서 확인 필요. **Phase 1 PoC 시 fixture 캡처 필수** (`tests/fixtures/perftest_ib_write_bw_200g_bidir.txt`). 미검증 동안에는 합산 단일 라인 가정으로 구현, 실측 후 패치.

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

## 측정 흐름 (부하 + sysfs 폴링)

> ⚠️ **설계 변경**: 라이브 검증 결과 `ib_write_bw` 의 stdout 은 종료 시 1줄만 출력 (인터벌별 다중 라인 X). 실시간 시각화를 위해 **부하 도구와 측정 도구를 분리**:

```
1. controller → SSH(server-A): perftest server 백그라운드 기동 (부하만)
2. controller → SSH(server-B): perftest client 실행 (부하만)
3. controller: 별도 task 로 sysfs 카운터 5Hz 폴링:
       cat /sys/class/net/<iface>/statistics/tx_bytes
       cat /sys/class/net/<iface>/statistics/rx_bytes
   - 직전 값과 차분 → BW (Gb/s)
   - MeasurementEvent 로 yield → SSE
4. /api/stop 또는 perftest 정상 종료 시:
   a. perftest client/server SIGTERM (5s grace) → SIGKILL
   b. sysfs 폴링 task cancel
   c. SSH 세션 클로즈
5. state=IDLE
```

폴링 인터페이스:
- dg5W: `/sys/class/net/enp2s0f0np0/statistics/{tx_bytes,rx_bytes}`
- dg5R: `/sys/class/net/ens7f0np0/statistics/{tx_bytes,rx_bytes}`

차분 계산:
```python
bw_gbps = (curr_bytes - prev_bytes) * 8 / interval_sec / 1e9
```

`tx_bytes` 또는 `rx_bytes` 한쪽만 측정 (P2P 단방향이면 둘 합산은 중복). BIDIR 시 양쪽 합산.

iperf3 도 동일 흐름 사용 가능 (또는 기존 JSON 파싱 유지). perftest 와 일관된 흐름이 단순.

`ib_read_lat` (지연 측정) 은 BW 가 아니라 sysfs 폴링 무관 — 종료 후 stdout 1줄 파싱하여 1회 yield.

PID 추적: asyncssh `process` 객체 보관. fallback `pkill -f ib_write_bw`.

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

### sysfs 카운터 (실시간 BW, 모든 RDMA/TCP 도구 공통)

```python
def parse_sysfs_stats(prev_bytes: int, curr_bytes: int, interval_sec: float) -> float:
    """net statistics 차분 → Gb/s. (curr - prev) * 8 / interval / 1e9."""
    return (curr_bytes - prev_bytes) * 8 / interval_sec / 1e9
```

- 카운터 wraparound (64-bit unsigned overflow) 거의 일어나지 않으나 음수 방어
- 측정 인터페이스: `enp2s0f0np0` (dg5W) 또는 `ens7f0np0` (dg5R)
- 폴링은 한쪽 서버만 (P2P 양방향 BW 동일). BIDIR 모드면 양쪽 합산

### `ib_write_bw` 출력 (참고용 — 종료 시 1줄)

라이브 환경 실측 (2026-05-05):
```
 #bytes     #iterations    BW peak[Gb/sec]    BW average[Gb/sec]   MsgRate[Mpps]
 65536      1037502         0.00               181.32               0.345834
```

- 측정 종료 후 단일 라인. **실시간 시각화에는 sysfs 폴링** 사용
- 종료 시 평균 BW를 confirm 용도로 1회 yield (선택)
- 데이터 라인 정규식 (그대로): `r'^\s*(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*$'`
- 200G 환경 (MTU 9000) 기대: `bw_avg ≈ 195~199`. MTU 1024 시 ~181

### `ib_read_lat` 출력

```
 #bytes #iterations    t_min[usec]    t_max[usec]  t_typical[usec]    t_avg[usec]    t_stdev[usec]   99% percentile[usec]   99.9% percentile[usec]
 8       1000           1.45           2.10         1.55              1.58            0.05            1.78                   1.92
```

- `t_avg` → `lat_us` 필드
- `t_min`, `99% percentile` → 옵션으로 별도 필드 보관

### `iperf3 -J` 출력

**단방향 파싱**:
```python
result = json.loads(stdout)
for interval in result['intervals']:
    bps = interval['sum']['bits_per_second']
    bw_avg_gbps = bps / 1e9
```

**양방향 (`--bidir`) 파싱** — `sum` 대신 `sum_sent` + `sum_received` 사용:
```python
for interval in result['intervals']:
    sent = interval['sum_sent']['bits_per_second']
    recv = interval['sum_received']['bits_per_second']
    bw_avg_gbps = (sent + recv) / 1e9   # 합산
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
    tool_category: Literal["perftest", "iperf3", "mock"]                       # 카테고리
    sub_tool: Literal["ib_write_bw", "ib_read_lat", "iperf3", "mock"] | None   # 서브툴
```

> **명명 규약**: `StartRequest.tool` (= API body 필드) 은 **서브툴**(`ib_write_bw` 등)을 받음. `MeasurementEvent`에서는 동일 이름의 충돌을 피하기 위해 카테고리 필드를 `tool_category`로 명명.

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

## NIC IC + 광 모듈 온도 텔레메트리

측정 BW와 별도 채널로 양쪽 NIC의 (a) ASIC IC 온도, (b) 광 트랜시버 모듈 온도를 항상 폴링·발행. 측정 중일 때는 누적 시계열로, IDLE에서도 baseline 모니터링 표시.

### 측정 도구 — `sensors -j` (lm-sensors)

라이브 검증 결과 `lm-sensors` 가 IC + Module 둘 다 한 번의 호출로 노출. **sudo 불필요**.

```bash
sensors -j   # JSON 출력
```

출력 예 (mlx5 chip만 발췌):
```json
{
  "mlx5-pci-0200": {
    "asic":    {"temp1_input": 46.0, "temp1_crit": 105.0, "temp1_highest": 47.0},
    "Module0": {"temp2_input": 57.0, "temp2_crit":  70.0, "temp2_highest": 58.0}
  },
  "mlx5-pci-0201": {
    "asic":    {"temp1_input": 46.0, "temp1_crit": 105.0}
  }
}
```

- chip 이름: `mlx5-pci-<bus><slot><func>` (예: `mlx5-pci-0200` = PCIe 02:00.0)
- 한 NIC에 두 chip 노출 (포트 0, 포트 1). **`Module0` 키가 있는 chip = 트랜시버 연결된 활성 포트** → 자동 선택
- 필드:
  - IC ASIC 온도: `<chip>.asic.temp1_input` (°C)
  - Module 트랜시버: `<chip>.Module0.temp2_input` (°C)
  - 임계값: `temp1_crit` / `temp2_crit` 도 같이 노출 (옵션 활용)

### 파싱 (`parse_sensors_json`)

```python
def parse_sensors_json(
    text: str, pci_chip_prefix: str | None = None
) -> tuple[float | None, float | None]:
    """sensors -j → (ic_celsius, module_celsius). 실패 시 None."""
```

- `pci_chip_prefix`: 특정 chip 명시 (예: `"mlx5-pci-0200"`). 미지정 시 Module0 있는 chip 자동 선택
- 실패 / 키 부재 / 잘못된 JSON → `(None, None)` 반환 → UI 측에서 직전 값 유지

### 폴링 정책

- 주기: **1Hz** (BW 5Hz와 별도. 온도는 천천히 변함)
- 양쪽 서버 동시 polling: `sensors -j` 한 번 호출에 IC + Module 함께
- `nic_telemetry.py` 가 SSH 연결 1개씩 (양쪽 서버) — 측정 SSH와 별도 pool, fault isolation
- 실패 시 직전 값 유지 + UI는 "—°C"
- IDLE/RUNNING 무관 항상 동작 (시스템 health)

### 임계값 / 색상 코딩 (UI)

| 컴포넌트 | 정상 | 경고 | 위험 | 운영 한계 |
|---------|------|------|------|----------|
| NIC IC (ASIC) | < 75°C | 75 ~ 85°C | ≥ 85°C | ~105°C (sensors `temp1_crit`) |
| 광 모듈 (QSFP56) | < 65°C | 65 ~ 75°C | ≥ 75°C | ~70°C (sensors `temp2_crit`) |

> sensors 가 노출하는 `temp_crit` 값을 향후 동적 임계값으로 사용 가능. 현재는 정적 임계값.

### 폴링 정책

- 주기: **1Hz** (BW 10Hz와 별도. 온도는 천천히 변함)
- 4채널 동시 polling: A-IC, A-Module, B-IC, B-Module — asyncssh fan-out
- 실패 시: 직전 값 유지 + `error` 필드. UI는 "—°C"로 표시
- IDLE 상태에서도 항상 동작 (시스템 health 시각화)

### NicTelemetry 스키마

```python
class NicTelemetry(BaseModel):
    ts: datetime
    server_a_ic_c: float | None         # ASIC IC 온도
    server_b_ic_c: float | None
    server_a_module_c: float | None     # 광 트랜시버 모듈 온도
    server_b_module_c: float | None
    source: Literal["sensors", "mock"]
```

### SSE 이벤트

```
event: nic_temp
data: {
  "ts": "2026-05-04T12:00:00Z",
  "server_a_ic_c": 62.3, "server_b_ic_c": 64.1,
  "server_a_module_c": 41.5, "server_b_module_c": 43.0,
  "source": "mget_temp+ethtool"
}
```

`measurement` 이벤트와 분리. 측정 중·IDLE 모두 발행.

### 임계값 / 색상 코딩

| 컴포넌트 | 정상 | 경고 | 위험 | 운영 한계 |
|---------|------|------|------|----------|
| NIC IC (ASIC) | < 75°C | 75 ~ 85°C | ≥ 85°C | ~100°C |
| 광 모듈 (QSFP56) | < 65°C | 65 ~ 75°C | ≥ 75°C | ~80°C |

광 트랜시버는 IC보다 운영 한계가 낮으므로 임계값을 더 보수적으로 설정.

UI 색상:
- 정상: `accent` (cyan)
- 경고: `warning` (amber)
- 위험: `danger` (red)
- 측정 실패: muted "—°C"

### 액냉 (Liquid-Cooled) 표시

본 환경의 NIC IC 및 광 트랜시버 모두 **액냉 시스템**에 연결됨. UI에 명시적으로 "LIQUID-COOLED" 라벨 노출:
- 하드웨어 다이어그램의 서버 박스 상단
- 트랜시버 박스 내부

(이는 시각 요소이며, 실제 측정값에 영향을 주지 않음. 액냉 환경에서 IC/Module의 baseline·peak가 공냉 대비 낮게 나타나는 것이 정상)

### 데모 모드 (mock)

`MEASUREMENT_TOOL=mock` 또는 NIC 환경 부재 시:
- IC baseline: A 45°C, B 47°C
- IC running target: 70°C (UNI) / 73°C (BIDIR)
- Module baseline: A 36°C, B 38°C (액냉으로 IC보다 낮은 baseline)
- Module running target: 56°C (UNI) / 59°C (BIDIR)
- 1차 시간상수 τ=0.04로 점진 변화, σ≈0.4°C 가우시안 노이즈, 12초 주기 sine

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
