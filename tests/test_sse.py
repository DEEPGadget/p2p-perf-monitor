"""SSE 채널 — _sse_generator 직접 테스트 (ASGI stream 통합은 수동 검증)."""

from __future__ import annotations

import asyncio

from app.api.stream import _sse_generator
from app.schemas import MeasurementEvent, NicTelemetry, SessionStatus
from app.state import SessionManager


async def _take(gen, n: int, timeout: float = 5.0) -> list[bytes]:
    """generator 에서 n 개 chunk 수집."""
    out: list[bytes] = []

    async def _drain() -> None:
        async for chunk in gen:
            out.append(chunk)
            if len(out) >= n:
                break

    await asyncio.wait_for(_drain(), timeout=timeout)
    return out


class TestSseGenerator:
    async def test_publishes_status_event(self) -> None:
        mgr = SessionManager()
        gen = _sse_generator(mgr)

        async def _publish() -> None:
            await asyncio.sleep(0.05)
            mgr.publish("status", SessionStatus(state="running", tool="ib_write_bw"))

        publisher = asyncio.create_task(_publish())
        chunks = await _take(gen, 1)
        await publisher
        await gen.aclose()

        text = chunks[0].decode()
        assert text.startswith("event: status\n")
        assert "data: " in text
        assert '"state":"running"' in text
        assert text.endswith("\n\n")

    async def test_measurement_event_payload(self) -> None:
        mgr = SessionManager()
        gen = _sse_generator(mgr)

        evt = MeasurementEvent(
            ts="2026-05-05T00:00:00Z",  # type: ignore[arg-type]
            msg_size=65536,
            bw_peak_gbps=200.0,
            bw_avg_gbps=188.0,
            tool_category="perftest",
            sub_tool="ib_write_bw",
        )

        async def _publish() -> None:
            await asyncio.sleep(0.05)
            mgr.publish("measurement", evt)

        publisher = asyncio.create_task(_publish())
        chunks = await _take(gen, 1)
        await publisher
        await gen.aclose()

        text = chunks[0].decode()
        assert text.startswith("event: measurement\n")
        assert '"bw_avg_gbps":188.0' in text

    async def test_multiple_subscribers_fanout(self) -> None:
        mgr = SessionManager()
        gen1 = _sse_generator(mgr)
        gen2 = _sse_generator(mgr)
        gen3 = _sse_generator(mgr)

        async def _publish() -> None:
            await asyncio.sleep(0.05)
            mgr.publish(
                "nic_temp",
                NicTelemetry(
                    ts="2026-05-05T00:00:00Z",  # type: ignore[arg-type]
                    server_a_ic_c=46.0,
                    server_b_ic_c=38.0,
                    server_a_module_c=57.0,
                    server_b_module_c=46.0,
                    source="sensors",
                ),
            )

        publisher = asyncio.create_task(_publish())
        c1, c2, c3 = await asyncio.gather(_take(gen1, 1), _take(gen2, 1), _take(gen3, 1))
        await publisher
        for g in (gen1, gen2, gen3):
            await g.aclose()

        for chunks in (c1, c2, c3):
            assert b"event: nic_temp" in chunks[0]
            assert b'"server_a_ic_c":46.0' in chunks[0]
