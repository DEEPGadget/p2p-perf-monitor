"""parser tests — fixture snapshot + edge case. Spec → app/parser.py."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.parser import (
    make_sysfs_event,
    parse_ib_read_lat_line,
    parse_ib_write_bw_line,
    parse_iperf3_json,
    parse_sysfs_stats,
)
from app.schemas import MeasurementEvent

FIXTURES = Path(__file__).parent / "fixtures"
FIXED_TS = datetime(2026, 5, 4, 12, 0, 0, tzinfo=UTC)


# ─────────────────────────── ib_write_bw ───────────────────────────


class TestParseIbWriteBwLine:
    def test_data_line_parses_to_event(self) -> None:
        line = " 65536      5000           198.45             197.82               0.378"
        evt = parse_ib_write_bw_line(line, ts=FIXED_TS)
        assert evt is not None
        assert evt.msg_size == 65536
        assert evt.iterations == 5000
        assert evt.bw_peak_gbps == pytest.approx(198.45)
        assert evt.bw_avg_gbps == pytest.approx(197.82)
        assert evt.msg_rate_mpps == pytest.approx(0.378)
        assert evt.tool_category == "perftest"
        assert evt.sub_tool == "ib_write_bw"

    @pytest.mark.parametrize(
        "line",
        [
            "",
            "---------------------------------------------------------",
            " #bytes     #iterations    BW peak[Gb/sec]    BW average[Gb/sec]   MsgRate[Mpps]",
            " local address: LID 0000 QPN 0x0123 PSN 0xabcdef RKey 0x012345",
            " Number of qps   : 1		Transport type : IB",
            " GID index       : 3",
        ],
    )
    def test_non_data_line_returns_none(self, line: str) -> None:
        assert parse_ib_write_bw_line(line) is None

    def test_fixture_uni_yields_4_events(self) -> None:
        text = (FIXTURES / "perftest_ib_write_bw_200g_uni.txt").read_text()
        events = [
            evt
            for line in text.splitlines()
            if (evt := parse_ib_write_bw_line(line, ts=FIXED_TS)) is not None
        ]
        assert len(events) == 4
        assert all(e.msg_size == 65536 for e in events)
        assert all(195 <= e.bw_avg_gbps <= 199 for e in events)

    def test_fixture_bidir_yields_3_events_around_376g(self) -> None:
        text = (FIXTURES / "perftest_ib_write_bw_200g_bidir.txt").read_text()
        events = [
            evt
            for line in text.splitlines()
            if (evt := parse_ib_write_bw_line(line, bidir=True, ts=FIXED_TS)) is not None
        ]
        assert len(events) == 3
        # BIDIR 합산 ~376 Gb/s
        assert all(370 <= e.bw_avg_gbps <= 380 for e in events)

    def test_explicit_ts_propagated(self) -> None:
        evt = parse_ib_write_bw_line(
            " 65536      5000           198.45             197.82               0.378",
            ts=FIXED_TS,
        )
        assert evt is not None
        assert evt.ts == FIXED_TS


# ─────────────────────────── ib_read_lat ───────────────────────────


class TestParseIbReadLatLine:
    def test_data_line_parses_to_event(self) -> None:
        line = (
            " 8       1000           1.45           2.10         1.55              "
            "1.58            0.05            1.78                   1.92"
        )
        evt = parse_ib_read_lat_line(line, ts=FIXED_TS)
        assert evt is not None
        assert evt.msg_size == 8
        assert evt.iterations == 1000
        assert evt.lat_us == pytest.approx(1.58)
        assert evt.lat_p99_us == pytest.approx(1.78)
        assert evt.bw_peak_gbps == 0.0
        assert evt.bw_avg_gbps == 0.0
        assert evt.tool_category == "perftest"
        assert evt.sub_tool == "ib_read_lat"

    def test_header_line_returns_none(self) -> None:
        line = " #bytes #iterations    t_min[usec]    t_max[usec]"
        assert parse_ib_read_lat_line(line) is None

    def test_bw_line_does_not_match_lat(self) -> None:
        # ib_write_bw 5컬럼 라인은 9컬럼 lat regex에 매칭 안 됨
        line = " 65536      5000           198.45             197.82               0.378"
        assert parse_ib_read_lat_line(line) is None

    def test_fixture_yields_one_event(self) -> None:
        text = (FIXTURES / "perftest_ib_read_lat.txt").read_text()
        events = [
            evt
            for line in text.splitlines()
            if (evt := parse_ib_read_lat_line(line, ts=FIXED_TS)) is not None
        ]
        assert len(events) == 1
        assert events[0].lat_us == pytest.approx(1.58)


# ─────────────────────────── iperf3 ───────────────────────────


class TestParseIperf3Json:
    def test_uni_fixture_yields_3_intervals(self) -> None:
        text = (FIXTURES / "iperf3_tcp_8streams.json").read_text()
        events = parse_iperf3_json(text, ts=FIXED_TS)
        assert len(events) == 3
        # 약 171.8 Gb/s
        assert all(170 <= e.bw_avg_gbps <= 173 for e in events)
        assert all(e.tool_category == "iperf3" for e in events)

    def test_bidir_fixture_sums_sent_and_received(self) -> None:
        text = (FIXTURES / "iperf3_tcp_bidir.json").read_text()
        events = parse_iperf3_json(text, bidir=True, ts=FIXED_TS)
        assert len(events) == 2
        # 88 + 86 = 174 Gb/s 부근
        assert all(170 <= e.bw_avg_gbps <= 178 for e in events)

    def test_failed_fixture_returns_empty(self) -> None:
        text = (FIXTURES / "iperf3_failed.json").read_text()
        events = parse_iperf3_json(text)
        assert events == []

    def test_invalid_json_returns_empty(self) -> None:
        assert parse_iperf3_json("not json {") == []
        assert parse_iperf3_json("") == []

    def test_no_intervals_returns_empty(self) -> None:
        assert parse_iperf3_json('{"intervals": []}') == []

    def test_zero_bps_interval_skipped(self) -> None:
        text = '{"intervals": [{"sum": {"bits_per_second": 0}}]}'
        assert parse_iperf3_json(text) == []

    def test_bidir_uses_sum_not_sum_sent(self) -> None:
        # bidir=False 인데 sum 만 있고 sum_sent/recv 없으면 sum 사용
        text = '{"intervals": [{"sum": {"bits_per_second": 100000000000.0}}]}'
        events = parse_iperf3_json(text, bidir=False, ts=FIXED_TS)
        assert len(events) == 1
        assert events[0].bw_avg_gbps == pytest.approx(100.0)

    def test_bidir_missing_sum_received_treats_as_zero(self) -> None:
        text = '{"intervals": [{"sum_sent": {"bits_per_second": 50000000000.0}}]}'
        events = parse_iperf3_json(text, bidir=True, ts=FIXED_TS)
        assert len(events) == 1
        assert events[0].bw_avg_gbps == pytest.approx(50.0)


# ─────────────────────────── 회귀: 모든 헤더 라인 무시 ───────────────────────────


class TestHeaderIgnoreRegression:
    """fixture 전체를 라인별로 파싱하면 헤더 0개·데이터만 반환되는지."""

    def test_uni_fixture_full_parse_filters_headers(self) -> None:
        text = (FIXTURES / "perftest_ib_write_bw_200g_uni.txt").read_text()
        results: list[MeasurementEvent | None] = [
            parse_ib_write_bw_line(line) for line in text.splitlines()
        ]
        non_none = [r for r in results if r is not None]
        assert len(non_none) == 4
        # 4 데이터 라인 외 ~25 헤더 라인 모두 None
        none_count = sum(1 for r in results if r is None)
        assert none_count >= 20


# ─────────────────────────── sysfs stats (Phase 2 측정 흐름) ───────────────────────────


class TestParseSysfsStats:
    def test_normal_diff_to_gbps(self) -> None:
        # 1초간 200Gb/s = 25,000,000,000 bytes
        bw = parse_sysfs_stats(0, 25_000_000_000, 1.0)
        assert bw == pytest.approx(200.0)

    def test_zero_diff(self) -> None:
        assert parse_sysfs_stats(1000, 1000, 1.0) == 0.0

    def test_negative_diff_clamped_zero(self) -> None:
        # 카운터 wraparound 또는 reset
        assert parse_sysfs_stats(2000, 1000, 1.0) == 0.0

    def test_zero_interval_returns_zero(self) -> None:
        assert parse_sysfs_stats(0, 100, 0.0) == 0.0

    def test_negative_interval_returns_zero(self) -> None:
        assert parse_sysfs_stats(0, 100, -0.5) == 0.0

    def test_5hz_polling_interval(self) -> None:
        # 0.2초 동안 5GB → 200Gbps
        bw = parse_sysfs_stats(0, 5_000_000_000, 0.2)
        assert bw == pytest.approx(200.0)

    def test_181gbps_realistic(self) -> None:
        # 라이브 측정 1초간 ~22.66 GB
        bw = parse_sysfs_stats(0, 22_665_000_000, 1.0)
        assert 181.0 < bw < 182.0


class TestMakeSysfsEvent:
    def test_perftest_event(self) -> None:
        evt = make_sysfs_event(181.5, msg_size=65536, sub_tool="ib_write_bw", ts=FIXED_TS)
        assert evt.tool_category == "perftest"
        assert evt.sub_tool == "ib_write_bw"
        assert evt.bw_peak_gbps == 181.5
        assert evt.bw_avg_gbps == 181.5
        assert evt.lat_us is None
        assert evt.iterations is None

    def test_iperf3_event(self) -> None:
        evt = make_sysfs_event(150.0, msg_size=131072, sub_tool="iperf3", ts=FIXED_TS)
        assert evt.tool_category == "iperf3"
        assert evt.sub_tool == "iperf3"

    def test_mock_event(self) -> None:
        evt = make_sysfs_event(187.0, msg_size=65536, sub_tool="mock", ts=FIXED_TS)
        assert evt.tool_category == "mock"
        assert evt.sub_tool == "mock"
