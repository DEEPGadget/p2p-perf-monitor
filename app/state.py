"""SessionManager — 단일 세션 상태 머신 + SSE pub/sub fan-out.

Spec: rules/api.md §SSE 포맷 + §큐 / 백프레셔 정책.
- 단일 세션 (동시 RUNNING 1개)
- 구독자별 asyncio.Queue(maxsize=256), drop-oldest
- 30분 idle timeout (구독자 cleanup)
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Literal

from app.schemas import (
    ErrorEvent,
    MeasurementEvent,
    NicTelemetry,
    SessionStatus,
    StartRequest,
)

# SSE 이벤트 종류 — rules/api.md §SSE 포맷
EventName = Literal["measurement", "nic_temp", "status", "error"]
EventPayload = MeasurementEvent | NicTelemetry | SessionStatus | ErrorEvent


class _Subscriber:
    """SSE 구독자 — 자체 큐 보유. drop-oldest 정책 (rules/api.md)."""

    QUEUE_MAX = 256

    def __init__(self) -> None:
        self.queue: asyncio.Queue[tuple[EventName, EventPayload]] = asyncio.Queue(
            maxsize=self.QUEUE_MAX
        )

    def put_nowait(self, event: tuple[EventName, EventPayload]) -> None:
        try:
            self.queue.put_nowait(event)
        except asyncio.QueueFull:
            # drop-oldest: 가장 오래된 이벤트 폐기, 새 이벤트 push
            with contextlib.suppress(asyncio.QueueEmpty):
                self.queue.get_nowait()
            with contextlib.suppress(asyncio.QueueFull):
                self.queue.put_nowait(event)


class SessionManager:
    """세션 단일 머신 + SSE 구독 관리.

    publish() 는 모든 구독자 큐에 fan-out. 구독자 disconnect 시 unsubscribe() 호출.
    runner / nic_telemetry 는 publish 만 호출 (관리는 외부 task 가).
    """

    def __init__(self) -> None:
        self._status = SessionStatus(state="idle")
        self._subscribers: set[_Subscriber] = set()
        self._lock = asyncio.Lock()  # status 전이 동기화

    # ── 외부 조회 ─────────────────────────────────────

    def status(self) -> SessionStatus:
        return self._status.model_copy()

    # ── 상태 전이 ─────────────────────────────────────

    async def begin_connecting(self, req: StartRequest) -> SessionStatus:
        """idle → connecting. 이미 RUNNING 시 충돌 (호출 측에서 409)."""
        async with self._lock:
            if self._status.state in ("connecting", "running"):
                # 호출 측에서 status() 받아 409 응답 — 여기선 raise
                raise SessionConflictError(self._status.model_copy())
            self._status = SessionStatus(
                state="connecting",
                tool=req.tool,
                started_at=datetime.now(UTC),
                error=None,
            )
        self.publish("status", self._status)
        return self._status.model_copy()

    async def mark_running(self) -> SessionStatus:
        async with self._lock:
            self._status = self._status.model_copy(update={"state": "running"})
        self.publish("status", self._status)
        return self._status.model_copy()

    async def mark_error(self, error: ErrorEvent) -> SessionStatus:
        async with self._lock:
            self._status = self._status.model_copy(
                update={
                    "state": "error",
                    "error": error.model_dump(mode="json"),
                }
            )
        self.publish("status", self._status)
        self.publish("error", error)
        return self._status.model_copy()

    async def mark_idle(self) -> SessionStatus:
        """RUNNING/ERROR → idle. /api/stop idempotent."""
        async with self._lock:
            self._status = SessionStatus(state="idle")
        self.publish("status", self._status)
        return self._status.model_copy()

    # ── pub/sub ─────────────────────────────────────

    def publish(self, name: EventName, payload: EventPayload) -> None:
        """모든 구독자 큐에 fan-out. lock 안에서 부르지 말 것 (블록 위험 X 이지만 깨끗하게)."""
        for sub in list(self._subscribers):
            sub.put_nowait((name, payload))

    def subscribe(self) -> _Subscriber:
        sub = _Subscriber()
        self._subscribers.add(sub)
        return sub

    def unsubscribe(self, sub: _Subscriber) -> None:
        self._subscribers.discard(sub)

    @contextlib.asynccontextmanager
    async def subscription(self) -> AsyncIterator[_Subscriber]:
        sub = self.subscribe()
        try:
            yield sub
        finally:
            self.unsubscribe(sub)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


class SessionConflictError(Exception):
    """이미 RUNNING/CONNECTING 인 세션에서 begin_connecting 호출 시."""

    def __init__(self, current: SessionStatus) -> None:
        super().__init__(f"session already in state={current.state}")
        self.current = current


# 하위 호환 alias (이전 import 경로 보호용)
SessionConflict = SessionConflictError
