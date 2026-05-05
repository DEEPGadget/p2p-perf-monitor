"""FastAPI app entry — lifespan + 라우터 등록.

Spec: rules/api.md, CLAUDE.md §Architecture.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, measure, stream
from app.config import Settings
from app.nic_telemetry import NicTelemetryPoller
from app.state import SessionManager

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Settings 로드 + SessionManager + NicTelemetryPoller 기동."""
    settings = Settings()  # type: ignore[call-arg]
    app.state.settings = settings

    mgr = SessionManager()
    app.state.session_manager = mgr
    app.state.measurement_task = None

    is_mock = settings.measurement_tool == "mock"
    poller = NicTelemetryPoller(
        mgr,
        settings if not is_mock else None,
        mock=is_mock,
    )
    app.state.nic_poller = poller
    await poller.start()
    log.info("startup: nic telemetry poller started (mock=%s)", is_mock)

    try:
        yield
    finally:
        await poller.stop()
        task: asyncio.Task | None = getattr(app.state, "measurement_task", None)
        if task is not None and not task.done():
            task.cancel()
            with contextlib.suppress(BaseException):
                await task
        log.info("shutdown: cleaned up")


def create_app() -> FastAPI:
    app = FastAPI(
        title="p2p-perf-monitor",
        version="0.1.0",
        description="200G ConnectX-6 RoCE P2P 성능 실시간 측정·시각화 (전시 데모).",
        lifespan=lifespan,
    )

    # 운영 시 dev_cors=False 면 CORS 비활성. dev_cors=True 시 Vite dev server 허용
    settings_for_cors = Settings()  # type: ignore[call-arg]
    if settings_for_cors.dev_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(health.router, prefix="/api")
    app.include_router(measure.router, prefix="/api")
    app.include_router(stream.router, prefix="/api")

    return app


app = create_app()
