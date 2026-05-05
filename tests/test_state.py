"""SessionManager + SSE pub/sub tests."""

from __future__ import annotations

import asyncio

import pytest

from app.schemas import ErrorEvent, MeasurementEvent, StartRequest
from app.state import SessionConflict, SessionManager


def _make_event() -> MeasurementEvent:
    return MeasurementEvent(
        ts="2026-05-05T12:00:00Z",  # type: ignore[arg-type]
        msg_size=65536,
        bw_peak_gbps=190.0,
        bw_avg_gbps=188.0,
        tool_category="perftest",
        sub_tool="ib_write_bw",
    )


class TestSessionManagerLifecycle:
    async def test_initial_state_is_idle(self) -> None:
        mgr = SessionManager()
        assert mgr.status().state == "idle"

    async def test_begin_connecting_transitions(self) -> None:
        mgr = SessionManager()
        req = StartRequest()
        s = await mgr.begin_connecting(req)
        assert s.state == "connecting"
        assert s.tool == "ib_write_bw"
        assert s.started_at is not None

    async def test_begin_connecting_when_running_raises(self) -> None:
        mgr = SessionManager()
        await mgr.begin_connecting(StartRequest())
        await mgr.mark_running()
        with pytest.raises(SessionConflict) as exc:
            await mgr.begin_connecting(StartRequest())
        assert exc.value.current.state == "running"

    async def test_mark_running_then_idle(self) -> None:
        mgr = SessionManager()
        await mgr.begin_connecting(StartRequest())
        await mgr.mark_running()
        assert mgr.status().state == "running"
        await mgr.mark_idle()
        assert mgr.status().state == "idle"

    async def test_mark_error(self) -> None:
        mgr = SessionManager()
        await mgr.begin_connecting(StartRequest())
        await mgr.mark_error(ErrorEvent(code="ssh_timeout", message="x"))
        assert mgr.status().state == "error"
        assert mgr.status().error == {
            "code": "ssh_timeout",
            "message": "x",
            "host": None,
            "stderr_tail": None,
        }

    async def test_mark_idle_after_error_recovers(self) -> None:
        mgr = SessionManager()
        await mgr.begin_connecting(StartRequest())
        await mgr.mark_error(ErrorEvent(code="ssh_unreachable", message="x"))
        await mgr.mark_idle()
        # 다시 시작 가능
        s = await mgr.begin_connecting(StartRequest())
        assert s.state == "connecting"


class TestSubscriberFanout:
    async def test_subscribe_unsubscribe(self) -> None:
        mgr = SessionManager()
        assert mgr.subscriber_count == 0
        sub = mgr.subscribe()
        assert mgr.subscriber_count == 1
        mgr.unsubscribe(sub)
        assert mgr.subscriber_count == 0

    async def test_publish_fans_out_to_all(self) -> None:
        mgr = SessionManager()
        s1 = mgr.subscribe()
        s2 = mgr.subscribe()
        s3 = mgr.subscribe()

        evt = _make_event()
        mgr.publish("measurement", evt)

        for s in (s1, s2, s3):
            name, payload = await s.queue.get()
            assert name == "measurement"
            assert payload == evt

    async def test_status_publish_on_transitions(self) -> None:
        mgr = SessionManager()
        sub = mgr.subscribe()
        await mgr.begin_connecting(StartRequest())
        await mgr.mark_running()
        await mgr.mark_idle()

        events = []
        for _ in range(3):
            events.append(await asyncio.wait_for(sub.queue.get(), timeout=1.0))

        names = [e[0] for e in events]
        states = [e[1].state for e in events]  # type: ignore[union-attr]
        assert names == ["status", "status", "status"]
        assert states == ["connecting", "running", "idle"]


class TestDropOldest:
    async def test_drop_oldest_when_queue_full(self) -> None:
        mgr = SessionManager()
        sub = mgr.subscribe()
        sub.queue._maxsize = 3  # 테스트용 작은 큐

        # 4개 push → 첫 번째 drop, 마지막 3개 남음
        for i in range(4):
            evt = MeasurementEvent(
                ts="2026-05-05T12:00:00Z",  # type: ignore[arg-type]
                msg_size=65536,
                bw_peak_gbps=float(i),
                bw_avg_gbps=float(i),
                tool_category="mock",
                sub_tool="mock",
            )
            sub.put_nowait(("measurement", evt))

        # 큐에 3개 (1, 2, 3)
        values = []
        while not sub.queue.empty():
            _, p = sub.queue.get_nowait()
            values.append(p.bw_avg_gbps)  # type: ignore[union-attr]
        assert values == [1.0, 2.0, 3.0]


class TestSubscriptionContextManager:
    async def test_subscription_auto_cleanup(self) -> None:
        mgr = SessionManager()
        async with mgr.subscription() as sub:
            assert mgr.subscriber_count == 1
            mgr.publish("measurement", _make_event())
            name, _ = await sub.queue.get()
            assert name == "measurement"
        assert mgr.subscriber_count == 0
