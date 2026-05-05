"""NIC IC + 광 트랜시버 모듈 온도 1Hz 폴링.

Spec: rules/measurement.md §NIC IC + 광 모듈 온도 텔레메트리.
- sensors -j 한 번 호출에 IC + Module 둘 다 추출
- 양쪽 서버 동시 폴링 (asyncio.gather)
- 측정 SSH 와 별도 connection pool (fault isolation)
- IDLE/RUNNING 무관 항상 동작
- mock 모드: NIC 부재 환경용 generator
"""

from __future__ import annotations

import asyncio
import contextlib
import math
import random
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import asyncssh

from app.parser import parse_sensors_json
from app.schemas import NicTelemetry

if TYPE_CHECKING:
    from app.config import Settings
    from app.state import SessionManager


_POLL_INTERVAL = 1.0  # 1Hz


class NicTelemetryPoller:
    """SessionManager.publish('nic_temp', ...) 를 1Hz 호출.

    `start()` 로 task 기동, `stop()` 으로 cancel + cleanup.
    `mock=True` 시 SSH 미사용 — UI 단독 검증용.
    """

    def __init__(
        self,
        manager: SessionManager,
        settings: Settings | None = None,
        *,
        mock: bool = False,
    ) -> None:
        self._mgr = manager
        self._settings = settings
        self._mock = mock or settings is None
        self._task: asyncio.Task[None] | None = None
        self._last: NicTelemetry | None = None
        # mock 누적 상태 (mockup 과 동일 baseline / target)
        self._mock_state = {"ic_a": 45.0, "ic_b": 47.0, "mod_a": 36.0, "mod_b": 38.0}

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._task = asyncio.create_task(self._loop(), name="nic_telemetry_poll")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(BaseException):
            await self._task
        self._task = None

    def latest(self) -> NicTelemetry | None:
        return self._last

    # ── internal ──────────────────────────────────────────────

    async def _loop(self) -> None:
        if self._mock:
            await self._mock_loop()
        else:
            await self._real_loop()

    async def _mock_loop(self) -> None:
        """mockup index.html 의 generator 와 동일 식 (1차 시간상수 + sine + noise)."""
        try:
            while True:
                self._step_mock()
                evt = NicTelemetry(
                    ts=datetime.now(UTC),
                    server_a_ic_c=round(self._mock_state["ic_a"], 1),
                    server_b_ic_c=round(self._mock_state["ic_b"], 1),
                    server_a_module_c=round(self._mock_state["mod_a"], 1),
                    server_b_module_c=round(self._mock_state["mod_b"], 1),
                    source="mock",
                )
                self._last = evt
                self._mgr.publish("nic_temp", evt)
                await asyncio.sleep(_POLL_INTERVAL)
        except asyncio.CancelledError:
            raise

    def _step_mock(self) -> None:
        """IDLE baseline. 측정 중 부하 가산은 추후 (running 상태 감지 + offset)."""
        # 단순화: 약간의 sine + noise 만. running 시 부하 모사는 SessionManager 상태 기반 추후
        phase = datetime.now(UTC).timestamp() / 12.0
        for k, target in (("ic_a", 45.0), ("ic_b", 47.0), ("mod_a", 36.0), ("mod_b", 38.0)):
            sine = math.sin(phase + hash(k) % 4) * 1.0
            noise = (random.random() - 0.5) * 0.4  # noqa: S311
            self._mock_state[k] += (target + sine - self._mock_state[k]) * 0.1 + noise
            self._mock_state[k] = max(25.0, min(95.0, self._mock_state[k]))

    async def _real_loop(self) -> None:
        """양쪽 서버에 SSH, sensors -j 1Hz 폴링.

        매 호출마다 connect — 1Hz 라 부담 적고 fault recovery 자동.
        측정 SSH 와 별도 connection (fault isolation 충족).
        """
        assert self._settings is not None
        ssh_kw = {
            "username": self._settings.ssh_user,
            "client_keys": [str(self._settings.ssh_key_path)],
            "known_hosts": str(self._settings.ssh_known_hosts),
        }
        host_a = self._settings.server_a_host
        host_b = self._settings.server_b_host

        try:
            while True:
                results = await asyncio.gather(
                    self._read_one(host_a, ssh_kw),
                    self._read_one(host_b, ssh_kw),
                    return_exceptions=True,
                )
                a_result = results[0] if not isinstance(results[0], BaseException) else (None, None)
                b_result = results[1] if not isinstance(results[1], BaseException) else (None, None)
                ic_a, mod_a = a_result  # type: ignore[misc]
                ic_b, mod_b = b_result  # type: ignore[misc]

                evt = NicTelemetry(
                    ts=datetime.now(UTC),
                    server_a_ic_c=ic_a,
                    server_b_ic_c=ic_b,
                    server_a_module_c=mod_a,
                    server_b_module_c=mod_b,
                    source="sensors",
                )
                self._last = evt
                self._mgr.publish("nic_temp", evt)
                await asyncio.sleep(_POLL_INTERVAL)
        except asyncio.CancelledError:
            raise

    async def _read_one(self, host: str, ssh_kw: dict) -> tuple[float | None, float | None]:
        """호스트에서 sensors -j 한 번 실행 → (ic, module). 실패 시 (None, None)."""
        try:
            async with asyncssh.connect(host, **ssh_kw) as conn:
                result = await conn.run("sensors -j", check=False)
                stdout = result.stdout if isinstance(result.stdout, str) else ""
                return parse_sensors_json(stdout)
        except (OSError, asyncssh.Error):
            return None, None
