"""POST /api/start, POST /api/stop, GET /api/status."""

from __future__ import annotations

import asyncio
import contextlib

from fastapi import APIRouter, HTTPException, Request

from app.runner import run_session
from app.schemas import ErrorEvent, SessionStatus, StartRequest
from app.state import SessionConflictError, SessionManager

router = APIRouter()


def _mgr(request: Request) -> SessionManager:
    return request.app.state.session_manager


@router.get("/status", response_model=SessionStatus)
async def get_status(request: Request) -> SessionStatus:
    return _mgr(request).status()


@router.post("/start", response_model=SessionStatus)
async def start(req: StartRequest, request: Request) -> SessionStatus:
    mgr = _mgr(request)
    settings = request.app.state.settings

    try:
        await mgr.begin_connecting(req)
    except SessionConflictError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "already_running",
                "current": e.current.model_dump(mode="json"),
            },
        ) from e

    async def _measurement_task() -> None:
        try:
            await mgr.mark_running()
            async for evt in run_session(req, settings):
                mgr.publish("measurement", evt)
            await mgr.mark_idle()
        except asyncio.CancelledError:
            await mgr.mark_idle()
            raise
        except Exception as exc:
            await mgr.mark_error(
                ErrorEvent(
                    code="measure_failed",
                    message=f"{type(exc).__name__}: {exc}",
                )
            )

    request.app.state.measurement_task = asyncio.create_task(
        _measurement_task(), name="measurement"
    )
    return mgr.status()


@router.post("/stop", response_model=SessionStatus)
async def stop(request: Request) -> SessionStatus:
    """idempotent: IDLE/ERROR 상태에서도 200 + state=idle."""
    mgr = _mgr(request)
    task: asyncio.Task | None = getattr(request.app.state, "measurement_task", None)
    if task is not None and not task.done():
        task.cancel()
        with contextlib.suppress(BaseException):
            await asyncio.wait_for(task, timeout=8.0)
    request.app.state.measurement_task = None
    return await mgr.mark_idle()
