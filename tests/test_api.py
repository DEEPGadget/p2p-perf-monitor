"""FastAPI endpoint tests — httpx + ASGITransport (no real server)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import httpx
import pytest

from app.main import create_app


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    """ASGI app 직접 + lifespan 실행."""
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        # lifespan 수동 trigger (httpx ASGITransport 는 자동 호출 안 함)
        async with app.router.lifespan_context(app):
            yield c


class TestHealth:
    async def test_health_returns_200(self, client: httpx.AsyncClient) -> None:
        r = await client.get("/api/health")
        assert r.status_code == 200
        assert r.json() == {"ok": True}


class TestStatus:
    async def test_status_idle_at_start(self, client: httpx.AsyncClient) -> None:
        r = await client.get("/api/status")
        assert r.status_code == 200
        assert r.json()["state"] == "idle"


class TestStartStop:
    async def test_start_mock_then_stop(self, client: httpx.AsyncClient) -> None:
        r = await client.post("/api/start", json={"tool": "mock", "duration_sec": 5})
        assert r.status_code == 200
        body = r.json()
        assert body["state"] in ("connecting", "running")
        assert body["tool"] == "mock"

        # 잠시 대기 후 running 확인
        await asyncio.sleep(0.3)
        r = await client.get("/api/status")
        assert r.json()["state"] in ("running", "connecting")

        # stop
        r = await client.post("/api/stop")
        assert r.status_code == 200
        assert r.json()["state"] == "idle"

    async def test_invalid_tool_returns_422(self, client: httpx.AsyncClient) -> None:
        r = await client.post("/api/start", json={"tool": "unknown"})
        assert r.status_code == 422

    async def test_extra_field_returns_422(self, client: httpx.AsyncClient) -> None:
        r = await client.post("/api/start", json={"tool": "mock", "unknown_field": 1})
        assert r.status_code == 422

    async def test_bidir_with_ib_read_lat_returns_422(self, client: httpx.AsyncClient) -> None:
        r = await client.post("/api/start", json={"tool": "ib_read_lat", "bidir": True})
        assert r.status_code == 422

    async def test_already_running_returns_409(self, client: httpx.AsyncClient) -> None:
        r1 = await client.post("/api/start", json={"tool": "mock", "duration_sec": 10})
        assert r1.status_code == 200

        r2 = await client.post("/api/start", json={"tool": "mock", "duration_sec": 10})
        assert r2.status_code == 409
        body = r2.json()
        assert body["detail"]["code"] == "already_running"

        await client.post("/api/stop")

    async def test_stop_when_idle_is_idempotent(self, client: httpx.AsyncClient) -> None:
        r = await client.post("/api/stop")
        assert r.status_code == 200
        assert r.json()["state"] == "idle"
