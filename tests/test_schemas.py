"""Schema validation tests. Spec → app/schemas.py."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import (
    ALLOWED_MSG_SIZES,
    ErrorEvent,
    MeasurementEvent,
    NicTelemetry,
    SessionStatus,
    StartRequest,
)


class TestStartRequest:
    def test_default_returns_ib_write_bw_uni_60s(self) -> None:
        req = StartRequest()
        assert req.tool == "ib_write_bw"
        assert req.duration_sec == 60
        assert req.msg_size == 65536
        assert req.qp_count == 4
        assert req.iperf3_streams == 8
        assert req.bidir is False

    def test_extra_field_forbidden_raises(self) -> None:
        with pytest.raises(ValidationError):
            StartRequest.model_validate({"tool": "ib_write_bw", "unknown_field": 1})

    def test_invalid_tool_raises(self) -> None:
        with pytest.raises(ValidationError):
            StartRequest.model_validate({"tool": "ib_unknown"})

    def test_msg_size_disallowed_raises(self) -> None:
        with pytest.raises(ValidationError):
            StartRequest(msg_size=12345)

    @pytest.mark.parametrize("size", ALLOWED_MSG_SIZES)
    def test_msg_size_allowlist_passes(self, size: int) -> None:
        req = StartRequest(msg_size=size)
        assert req.msg_size == size

    @pytest.mark.parametrize("dur", [4, 0, -1, 601, 9999])
    def test_duration_out_of_range_raises(self, dur: int) -> None:
        with pytest.raises(ValidationError):
            StartRequest(duration_sec=dur)

    @pytest.mark.parametrize("dur", [5, 60, 600])
    def test_duration_in_range_passes(self, dur: int) -> None:
        req = StartRequest(duration_sec=dur)
        assert req.duration_sec == dur

    @pytest.mark.parametrize("qp", [0, 17, -1])
    def test_qp_count_out_of_range_raises(self, qp: int) -> None:
        with pytest.raises(ValidationError):
            StartRequest(qp_count=qp)

    @pytest.mark.parametrize("streams", [0, 33, -1])
    def test_iperf3_streams_out_of_range_raises(self, streams: int) -> None:
        with pytest.raises(ValidationError):
            StartRequest(iperf3_streams=streams)

    def test_bidir_flag_passes(self) -> None:
        req = StartRequest(bidir=True)
        assert req.bidir is True


class TestSessionStatus:
    def test_default_is_idle(self) -> None:
        s = SessionStatus()
        assert s.state == "idle"
        assert s.tool is None
        assert s.started_at is None
        assert s.error is None

    def test_running_state(self) -> None:
        s = SessionStatus(state="running", tool="ib_write_bw")
        assert s.state == "running"
        assert s.tool == "ib_write_bw"

    def test_invalid_state_raises(self) -> None:
        with pytest.raises(ValidationError):
            SessionStatus.model_validate({"state": "unknown"})


class TestMeasurementEvent:
    def test_minimal_perftest_event(self) -> None:
        evt = MeasurementEvent(
            ts="2026-05-04T12:00:00Z",  # type: ignore[arg-type]
            msg_size=65536,
            bw_peak_gbps=198.45,
            bw_avg_gbps=197.82,
            tool_category="perftest",
            sub_tool="ib_write_bw",
        )
        assert evt.bw_avg_gbps == 197.82
        assert evt.lat_us is None
        assert evt.iterations is None

    def test_iperf3_event_no_perftest_fields(self) -> None:
        evt = MeasurementEvent(
            ts="2026-05-04T12:00:00Z",  # type: ignore[arg-type]
            msg_size=131072,
            bw_peak_gbps=170.0,
            bw_avg_gbps=165.0,
            tool_category="iperf3",
            sub_tool="iperf3",
        )
        assert evt.msg_rate_mpps is None
        assert evt.iterations is None

    def test_lat_event_includes_p99(self) -> None:
        evt = MeasurementEvent(
            ts="2026-05-04T12:00:00Z",  # type: ignore[arg-type]
            msg_size=8,
            iterations=1000,
            bw_peak_gbps=0.0,
            bw_avg_gbps=0.0,
            lat_us=1.58,
            lat_p99_us=1.78,
            tool_category="perftest",
            sub_tool="ib_read_lat",
        )
        assert evt.lat_us == 1.58
        assert evt.lat_p99_us == 1.78

    def test_invalid_tool_category_raises(self) -> None:
        with pytest.raises(ValidationError):
            MeasurementEvent.model_validate(
                {
                    "ts": "2026-05-04T12:00:00Z",
                    "msg_size": 64,
                    "bw_peak_gbps": 1.0,
                    "bw_avg_gbps": 1.0,
                    "tool_category": "invalid",
                    "sub_tool": "ib_write_bw",
                }
            )


class TestNicTelemetry:
    def test_all_channels_present(self) -> None:
        t = NicTelemetry(
            ts="2026-05-04T12:00:00Z",  # type: ignore[arg-type]
            server_a_ic_c=62.3,
            server_b_ic_c=64.1,
            server_a_module_c=41.5,
            server_b_module_c=43.0,
            source="sensors",
        )
        assert t.server_a_ic_c == 62.3
        assert t.source == "sensors"

    def test_failed_channel_keeps_none(self) -> None:
        t = NicTelemetry(
            ts="2026-05-04T12:00:00Z",  # type: ignore[arg-type]
            server_a_ic_c=None,
            server_b_ic_c=64.1,
            server_a_module_c=None,
            server_b_module_c=43.0,
            source="sensors",
        )
        assert t.server_a_ic_c is None
        assert t.server_a_module_c is None

    def test_invalid_source_raises(self) -> None:
        with pytest.raises(ValidationError):
            NicTelemetry.model_validate(
                {
                    "ts": "2026-05-04T12:00:00Z",
                    "server_a_ic_c": 60.0,
                    "server_b_ic_c": 60.0,
                    "server_a_module_c": 40.0,
                    "server_b_module_c": 40.0,
                    "source": "unknown_source",
                }
            )


class TestErrorEvent:
    def test_minimal_error(self) -> None:
        e = ErrorEvent(code="ssh_unreachable", message="connect failed")
        assert e.code == "ssh_unreachable"
        assert e.host is None

    def test_with_host_and_stderr(self) -> None:
        e = ErrorEvent(
            code="measure_failed",
            message="ib_write_bw exited 1",
            host="server-A",
            stderr_tail="Failed to modify QP",
        )
        assert e.host == "server-A"
        assert e.stderr_tail == "Failed to modify QP"

    def test_invalid_code_raises(self) -> None:
        with pytest.raises(ValidationError):
            ErrorEvent.model_validate({"code": "unknown_code", "message": "x"})
