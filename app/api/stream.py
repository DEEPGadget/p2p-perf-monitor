"""GET /api/stream — SSE 4 events (measurement / nic_temp / status / error).

Spec: rules/api.md §SSE 포맷 + §큐 / 백프레셔 정책.
heartbeat: 15초마다 ': ping\\n\\n' 코멘트 라인.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.state import SessionManager

router = APIRouter()

_HEARTBEAT_INTERVAL = 15.0


def _mgr(request: Request) -> SessionManager:
    return request.app.state.session_manager


async def _sse_generator(mgr: SessionManager) -> AsyncIterator[bytes]:
    """구독자 큐에서 이벤트 받아 SSE 라인 yield. timeout 시 heartbeat."""
    async with mgr.subscription() as sub:
        while True:
            try:
                name, payload = await asyncio.wait_for(sub.queue.get(), timeout=_HEARTBEAT_INTERVAL)
                data = payload.model_dump_json()
                yield f"event: {name}\ndata: {data}\n\n".encode()
            except TimeoutError:
                yield b": ping\n\n"


@router.get("/stream")
async def stream(request: Request) -> StreamingResponse:
    return StreamingResponse(
        _sse_generator(_mgr(request)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # nginx 등 reverse proxy buffering 회피
        },
    )
