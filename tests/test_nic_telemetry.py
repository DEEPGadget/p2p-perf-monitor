"""NicTelemetryPoller tests — mock 위주, 실 SSH 는 라이브 마커."""

from __future__ import annotations

import asyncio

import pytest

from app.nic_telemetry import NicTelemetryPoller
from app.schemas import NicTelemetry
from app.state import SessionManager


class TestMockPolling:
    async def test_publishes_nic_temp_events(self) -> None:
        mgr = SessionManager()
        sub = mgr.subscribe()
        poller = NicTelemetryPoller(mgr, settings=None, mock=True)
        await poller.start()
        try:
            # 첫 이벤트 (1Hz 라 ~1초 안에 도착)
            name, payload = await asyncio.wait_for(sub.queue.get(), timeout=2.5)
            assert name == "nic_temp"
            assert isinstance(payload, NicTelemetry)
            assert payload.source == "mock"
            assert payload.server_a_ic_c is not None
            assert 25.0 <= payload.server_a_ic_c <= 95.0
            assert payload.server_a_module_c is not None
        finally:
            await poller.stop()

    async def test_baseline_around_45c_ic_38c_module(self) -> None:
        mgr = SessionManager()
        sub = mgr.subscribe()
        poller = NicTelemetryPoller(mgr, mock=True)
        await poller.start()
        try:
            # 3개 샘플 평균 (1Hz 라 ~3초)
            samples = []
            for _ in range(3):
                _, p = await asyncio.wait_for(sub.queue.get(), timeout=2.5)
                samples.append(p)
            ic_a = sum(s.server_a_ic_c for s in samples) / 3  # type: ignore[misc]
            mod_a = sum(s.server_a_module_c for s in samples) / 3  # type: ignore[misc]
            # baseline 45 ± 5, mod 36 ± 5
            assert 38 < ic_a < 55
            assert 30 < mod_a < 45
        finally:
            await poller.stop()

    async def test_latest_returns_recent_event(self) -> None:
        mgr = SessionManager()
        poller = NicTelemetryPoller(mgr, mock=True)
        assert poller.latest() is None
        await poller.start()
        try:
            await asyncio.sleep(1.5)
            latest = poller.latest()
            assert latest is not None
            assert latest.source == "mock"
        finally:
            await poller.stop()

    async def test_stop_cancels_task(self) -> None:
        mgr = SessionManager()
        poller = NicTelemetryPoller(mgr, mock=True)
        await poller.start()
        await poller.stop()
        # stop 후 추가 이벤트 발행 안 됨
        sub = mgr.subscribe()
        await asyncio.sleep(1.5)
        assert sub.queue.empty()

    async def test_double_start_is_idempotent(self) -> None:
        mgr = SessionManager()
        poller = NicTelemetryPoller(mgr, mock=True)
        await poller.start()
        await poller.start()  # 두 번째 호출 무시
        await asyncio.sleep(0.1)
        await poller.stop()


@pytest.mark.live
class TestLivePolling:
    """실 NIC 환경. CI 제외."""

    async def test_sensors_returns_non_none_temps(self) -> None:
        from app.config import Settings

        mgr = SessionManager()
        sub = mgr.subscribe()
        settings = Settings()  # type: ignore[call-arg]
        poller = NicTelemetryPoller(mgr, settings=settings, mock=False)
        await poller.start()
        try:
            # 라이브: SSH connect + sensors 호출 ~2-3초 + 1Hz 폴링 = ~5초 첫 이벤트
            _, payload = await asyncio.wait_for(sub.queue.get(), timeout=10.0)
            assert payload.source == "sensors"  # type: ignore[union-attr]
            # 실 NIC 라면 IC 30~80°C, Module 30~70°C 범위
            assert payload.server_a_ic_c is not None  # type: ignore[union-attr]
            assert 20 < payload.server_a_ic_c < 100  # type: ignore[union-attr]
        finally:
            await poller.stop()
