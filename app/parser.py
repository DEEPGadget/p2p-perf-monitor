"""perftest / iperf3 stdout → MeasurementEvent. Spec → rules/measurement.md."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime

from app.schemas import MeasurementEvent

# ib_write_bw 데이터 라인:
#  #bytes  #iterations  BW peak[Gb/sec]  BW average[Gb/sec]  MsgRate[Mpps]
_IB_BW_LINE = re.compile(r"^\s*(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*$")

# ib_read_lat 데이터 라인:
#  #bytes #iter  t_min  t_max  t_typical  t_avg  t_stdev  99%  99.9%
_IB_LAT_LINE = re.compile(
    r"^\s*(\d+)\s+(\d+)\s+"
    r"([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+"
    r"([\d.]+)\s+([\d.]+)\s*$"
)

# iperf3 default --length (200G 환경에서 기본 사용)
_IPERF3_DEFAULT_MSG_SIZE = 131072


def _now() -> datetime:
    return datetime.now(UTC)


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

    bw_peak/bw_avg는 0.0 (lat 측정에선 의미 없음). lat_us = t_avg, lat_p99_us = 99%.
    """
    m = _IB_LAT_LINE.match(line)
    if not m:
        return None
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
