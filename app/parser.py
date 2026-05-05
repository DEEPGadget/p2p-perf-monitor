"""perftest / iperf3 stdout → MeasurementEvent. Spec → rules/measurement.md."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime

from app.schemas import MeasurementEvent

# ib_write_bw 데이터 라인:
#  #bytes  #iterations  BW peak[Gb/sec]  BW average[Gb/sec]  MsgRate[Mpps]
_IB_BW_LINE = re.compile(r"^\s*(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*$")

# ib_read_lat 데이터 라인 — 두 가지 모드:
#  (A) `-n <iter>` (iterations): 9 컬럼
#      #bytes #iter  t_min  t_max  t_typical  t_avg  t_stdev  99%  99.9%
#  (B) `-D <sec>`   (duration):  4 컬럼
#      #bytes #iter  t_avg[usec]  tps average
# 라이브 검증 결과 우리는 (B) 사용 중 → 둘 다 매치하도록 분리.
_IB_LAT_LINE_FULL = re.compile(
    r"^\s*(\d+)\s+(\d+)\s+"
    r"([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+"
    r"([\d.]+)\s+([\d.]+)\s*$"
)
_IB_LAT_LINE_DUR = re.compile(
    r"^\s*(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s*$"
)

# iperf3 default --length (200G 환경에서 기본 사용)
_IPERF3_DEFAULT_MSG_SIZE = 131072


def _now() -> datetime:
    return datetime.now(UTC)


def parse_sysfs_stats(prev_bytes: int, curr_bytes: int, interval_sec: float) -> float:
    """net statistics 카운터 차분 → Gb/s.

    `/sys/class/net/<iface>/statistics/{tx,rx}_bytes` 두 번 읽어 차분 ÷ 시간.
    Counter wraparound 거의 없으나 음수 결과는 0으로 방어.
    interval_sec ≤ 0 도 0 반환.
    """
    if interval_sec <= 0:
        return 0.0
    delta = curr_bytes - prev_bytes
    if delta < 0:
        delta = 0
    return delta * 8 / interval_sec / 1e9


_VALID_SUB_TOOLS = ("ib_write_bw", "ib_read_lat", "iperf3", "mock")
_PERFTEST_SUBS = ("ib_write_bw", "ib_read_lat")


def parse_sensors_json(
    text: str, pci_chip_prefix: str | None = None
) -> tuple[float | None, float | None]:
    """`sensors -j` 출력 → (asic_ic_celsius, module_celsius).

    mlx5 chip 중 `Module0` 키가 있는 chip = 사용 중인 포트 (트랜시버 연결됨).
    pci_chip_prefix 가 주어지면 해당 chip 만 매칭 (예: "mlx5-pci-0200").

    실패 / 키 부재 시 None 반환 (UI 측에서 직전 값 유지).
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None, None
    if not isinstance(data, dict):
        return None, None

    candidates: list[tuple[str, dict]] = []
    for chip_name, body in data.items():
        if not isinstance(body, dict):
            continue
        if not chip_name.startswith("mlx5-pci-"):
            continue
        if pci_chip_prefix and not chip_name.startswith(pci_chip_prefix):
            continue
        candidates.append((chip_name, body))

    if not candidates:
        return None, None

    # Module0 키가 있는 chip 우선 (활성 포트). 없으면 첫 매치
    selected = next(((c, b) for c, b in candidates if "Module0" in b), candidates[0])
    body = selected[1]

    ic: float | None = None
    asic = body.get("asic")
    if isinstance(asic, dict):
        v = asic.get("temp1_input")
        if isinstance(v, (int, float)):
            ic = float(v)

    module: float | None = None
    mod = body.get("Module0")
    if isinstance(mod, dict):
        v = mod.get("temp2_input")
        if isinstance(v, (int, float)):
            module = float(v)

    return ic, module


def make_sysfs_event(
    bw_gbps: float,
    msg_size: int,
    sub_tool: str,
    ts: datetime | None = None,
) -> MeasurementEvent:
    """sysfs 폴링 결과 → MeasurementEvent (1초 단위 평균이라 peak=avg)."""
    sub = sub_tool if sub_tool in _VALID_SUB_TOOLS else None
    if sub in _PERFTEST_SUBS:
        category = "perftest"
    elif sub == "iperf3":
        category = "iperf3"
    else:
        category = "mock"
    return MeasurementEvent(
        ts=ts or _now(),
        msg_size=msg_size,
        iterations=None,
        bw_peak_gbps=bw_gbps,
        bw_avg_gbps=bw_gbps,
        msg_rate_mpps=None,
        lat_us=None,
        lat_p99_us=None,
        tool_category=category,  # type: ignore[arg-type]
        sub_tool=sub,  # type: ignore[arg-type]
    )


def parse_ib_write_bw_line(
    line: str,
    bidir: bool = False,
    ts: datetime | None = None,
) -> MeasurementEvent | None:
    """`ib_write_bw` stdout 한 라인 파싱.

    헤더·구분선·빈 줄은 None 반환. 데이터 라인만 MeasurementEvent 반환.

    `bidir=True` (ib_write_bw -b) 시 출력 컬럼이 단방향과 동일한지(합산 단일
    라인)는 실 NIC 환경에서 fixture 캡처 후 검증 필요
    (rules/measurement.md §perftest 호출 규약). 현재는 합산 단일 라인 가정.

    Args:
        line: stdout 한 줄.
        bidir: 양방향 측정 여부. 현 구현은 분기 차이 없음 (실측 후 보강).
        ts: 명시적 timestamp (테스트용). 미지정 시 현재 시각.
    """
    m = _IB_BW_LINE.match(line)
    if not m:
        return None
    msg_size, iterations, bw_peak, bw_avg, msg_rate = m.groups()
    return MeasurementEvent(
        ts=ts or _now(),
        msg_size=int(msg_size),
        iterations=int(iterations),
        bw_peak_gbps=float(bw_peak),
        bw_avg_gbps=float(bw_avg),
        msg_rate_mpps=float(msg_rate),
        tool_category="perftest",
        sub_tool="ib_write_bw",
    )


def parse_ib_read_lat_line(line: str, ts: datetime | None = None) -> MeasurementEvent | None:
    """`ib_read_lat` stdout 한 라인 파싱.

    iterations 모드 (9 컬럼) → t_avg + p99 채움.
    duration   모드 (4 컬럼) → t_avg, p99=None.
    bw_peak/bw_avg 는 0.0 (lat 측정에선 의미 없음).
    """
    m = _IB_LAT_LINE_FULL.match(line)
    if m:
        bytes_, iters, _t_min, _t_max, _t_typical, t_avg, _t_stdev, p99, _p99_9 = m.groups()
        return MeasurementEvent(
            ts=ts or _now(),
            msg_size=int(bytes_),
            iterations=int(iters),
            bw_peak_gbps=0.0,
            bw_avg_gbps=0.0,
            lat_us=float(t_avg),
            lat_p99_us=float(p99),
            tool_category="perftest",
            sub_tool="ib_read_lat",
        )
    m = _IB_LAT_LINE_DUR.match(line)
    if m:
        bytes_, iters, t_avg, _tps = m.groups()
        return MeasurementEvent(
            ts=ts or _now(),
            msg_size=int(bytes_),
            iterations=int(iters),
            bw_peak_gbps=0.0,
            bw_avg_gbps=0.0,
            lat_us=float(t_avg),
            lat_p99_us=None,
            tool_category="perftest",
            sub_tool="ib_read_lat",
        )
    return None


def parse_iperf3_json(
    text: str, bidir: bool = False, ts: datetime | None = None
) -> list[MeasurementEvent]:
    """`iperf3 -J` 출력 (JSON 텍스트) → 인터벌별 MeasurementEvent 리스트.

    bidir=True 시 `sum_sent` + `sum_received` 합산 (rules/measurement.md §파싱 규칙).
    실패 케이스 (`{"error": ...}` 또는 invalid JSON): 빈 리스트.
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []

    if "error" in data:
        return []

    base_ts = ts or _now()
    intervals = data.get("intervals") or []
    events: list[MeasurementEvent] = []

    for iv in intervals:
        if bidir:
            sent = (iv.get("sum_sent") or {}).get("bits_per_second", 0)
            recv = (iv.get("sum_received") or {}).get("bits_per_second", 0)
            bps = sent + recv
        else:
            bps = (iv.get("sum") or {}).get("bits_per_second", 0)
        if bps <= 0:
            continue
        bw_gbps = bps / 1e9
        events.append(
            MeasurementEvent(
                ts=base_ts,
                msg_size=_IPERF3_DEFAULT_MSG_SIZE,
                bw_peak_gbps=bw_gbps,
                bw_avg_gbps=bw_gbps,
                tool_category="iperf3",
                sub_tool="iperf3",
            )
        )
    return events
