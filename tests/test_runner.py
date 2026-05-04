"""runner tests — mock_session 위주. 실 SSH 검증은 @pytest.mark.live."""

from __future__ import annotations

import pytest

from app.runner import mock_session, run_session
from app.schemas import StartRequest

# pyproject 의 asyncio_mode=auto 가 async 테스트 자동 처리.
# sync 함수 (Validation 등) 는 mark 적용 안 됨.


async def _collect(req: StartRequest, max_events: int = 1000) -> list:
    out = []
    async for evt in mock_session(req):
        out.append(evt)
        if len(out) >= max_events:
            break
    return out


class TestMockSession:
    async def test_uni_5s_yields_around_50_events(self) -> None:
        req = StartRequest(tool="mock", duration_sec=5)
        events = await _collect(req)
        # 10Hz × 5s = 50 events. 타이머 오차 허용 +/- 10
        assert 35 <= len(events) <= 55

    async def test_uni_bw_around_187(self) -> None:
        req = StartRequest(tool="mock", duration_sec=5)
        events = await _collect(req)
        avg_bw = sum(e.bw_avg_gbps for e in events) / len(events)
        # 187 ± 진폭 8 + noise σ=1.5 → 평균은 ~187 부근
        assert 175 <= avg_bw <= 199

    async def test_bidir_bw_around_374(self) -> None:
        req = StartRequest(tool="mock", duration_sec=5, bidir=True)
        events = await _collect(req)
        avg_bw = sum(e.bw_avg_gbps for e in events) / len(events)
        # BIDIR baseline 374 ± 14 ± noise
        assert 350 <= avg_bw <= 396

    async def test_bw_capped(self) -> None:
        req = StartRequest(tool="mock", duration_sec=5)
        events = await _collect(req, max_events=20)
        assert len(events) > 0
        # cap 199 (UNI)
        assert all(e.bw_avg_gbps <= 199.0 for e in events)
        assert all(e.bw_avg_gbps >= 0.0 for e in events)

    async def test_event_schema_fields(self) -> None:
        req = StartRequest(tool="mock", duration_sec=5)
        events = await _collect(req, max_events=5)
        assert len(events) > 0
        evt = events[0]
        assert evt.tool_category == "mock"
        assert evt.sub_tool == "mock"
        assert evt.lat_us is None  # ib_write_bw mock 이라 lat 없음
        assert evt.msg_size == 65536  # default

    async def test_lat_session_yields_lat_us(self) -> None:
        req = StartRequest(tool="ib_read_lat", duration_sec=5)
        # ib_read_lat 은 mock 직접 호출 (run_session 통해서는 mock 분기 X)
        events: list = []
        async for evt in mock_session(req):
            events.append(evt)
            if len(events) >= 5:
                break
        assert all(e.lat_us is not None for e in events)
        assert all(1.0 <= e.lat_us <= 2.5 for e in events)
        assert all(e.bw_avg_gbps == 0.0 for e in events)


class TestRunSessionDispatch:
    async def test_mock_tool_dispatches_to_mock_session(self) -> None:
        req = StartRequest(tool="mock", duration_sec=5)
        events: list = []
        async for evt in run_session(req):
            events.append(evt)
            if len(events) >= 3:
                break
        assert len(events) >= 1
        assert events[0].tool_category == "mock"

    async def test_non_mock_without_settings_raises(self) -> None:
        req = StartRequest(tool="ib_write_bw", duration_sec=5)
        with pytest.raises(ValueError, match="Settings required"):
            async for _ in run_session(req, settings=None):
                pass


class TestStartRequestBidirCompat:
    """bidir + ib_read_lat 422 거부 (rules/measurement.md §측정 옵션)."""

    def test_ib_read_lat_with_bidir_raises(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="bidir"):
            StartRequest(tool="ib_read_lat", bidir=True)

    def test_ib_read_lat_without_bidir_ok(self) -> None:
        req = StartRequest(tool="ib_read_lat", bidir=False)
        assert req.tool == "ib_read_lat"

    def test_ib_write_bw_with_bidir_ok(self) -> None:
        req = StartRequest(tool="ib_write_bw", bidir=True)
        assert req.bidir is True


# ─────────────────────────── 실 SSH (수동/CI 옵트인) ───────────────────────────


@pytest.mark.live
class TestPerftestLive:
    """실 NIC 환경에서만 동작. CI 기본 제외."""

    async def test_ib_write_bw_5s_yields_events(self) -> None:
        from app.config import Settings

        settings = Settings()  # type: ignore[call-arg]
        req = StartRequest(tool="ib_write_bw", duration_sec=5)
        events: list = []
        async for evt in run_session(req, settings):
            events.append(evt)
        assert len(events) > 0
        # 200G NIC peak 90% 이상 (~180 Gb/s) 검증
        max_bw = max(e.bw_avg_gbps for e in events)
        assert max_bw >= 150.0
