"""측정 세션 실행. Spec → rules/measurement.md, rules/security.md.

흐름:
- BW 측정 (ib_write_bw, iperf3): perftest/iperf3 부하 + sysfs 카운터 5Hz 폴링
  → 부하 도구 stdout 무시. sysfs 차분 = 실시간 BW.
- LAT 측정 (ib_read_lat): perftest stdout 파싱 (1줄, 종료 시).
- mock: NIC 부재 환경용 generator.
"""

from __future__ import annotations

import asyncio
import math
import random
import shlex
from collections.abc import AsyncIterator
from contextlib import suppress
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import asyncssh

from app.parser import make_sysfs_event, parse_ib_read_lat_line, parse_sysfs_stats
from app.schemas import MeasurementEvent

if TYPE_CHECKING:
    from app.config import Settings
    from app.schemas import StartRequest


# ─────────────────────────── 진입점 ───────────────────────────


async def run_session(
    req: StartRequest, settings: Settings | None = None
) -> AsyncIterator[MeasurementEvent]:
    """`/api/start` 메인 진입점. tool 별 분기."""
    if req.tool == "mock":
        async for evt in mock_session(req):
            yield evt
        return

    if settings is None:
        raise ValueError("Settings required for non-mock tools")

    if req.tool == "ib_read_lat":
        async for evt in _run_perftest_lat(req, settings):
            yield evt
        return

    if req.tool in ("ib_write_bw", "iperf3"):
        async for evt in _run_with_sysfs(req, settings):
            yield evt
        return

    raise ValueError(f"unknown tool: {req.tool}")


# ─────────────────────────── mock generator ───────────────────────────


async def mock_session(req: StartRequest) -> AsyncIterator[MeasurementEvent]:
    """200G NIC + RoCE 동작 모사 (10Hz). Spec: rules/measurement.md §데모 모드."""
    if req.tool == "ib_read_lat":
        async for evt in _mock_lat_session(req):
            yield evt
        return

    interval = 0.1
    base_avg = 374.0 if req.bidir else 187.0
    amplitude = 14.0 if req.bidir else 8.0
    sigma = 2.5 if req.bidir else 1.5
    cap = 396.0 if req.bidir else 199.0

    loop = asyncio.get_running_loop()
    start = loop.time()
    end = start + req.duration_sec

    while loop.time() < end:
        elapsed = loop.time() - start
        sine = math.sin((elapsed / 30.0) * 2 * math.pi) * amplitude
        noise = (random.random() + random.random() + random.random() - 1.5) * sigma  # noqa: S311
        bw_avg = max(0.0, min(cap, base_avg + sine + noise))
        bw_peak = bw_avg + random.uniform(0.5, 1.5)  # noqa: S311

        yield MeasurementEvent(
            ts=datetime.now(UTC),
            msg_size=req.msg_size,
            iterations=None,
            bw_peak_gbps=bw_peak,
            bw_avg_gbps=bw_avg,
            msg_rate_mpps=None,
            lat_us=None,
            lat_p99_us=None,
            tool_category="mock",
            sub_tool="mock",
        )
        await asyncio.sleep(interval)


async def _mock_lat_session(req: StartRequest) -> AsyncIterator[MeasurementEvent]:
    """ib_read_lat mock — 1.5~2.0µs, 10Hz."""
    interval = 0.1
    loop = asyncio.get_running_loop()
    start = loop.time()
    end = start + req.duration_sec

    while loop.time() < end:
        lat = 1.5 + random.uniform(0.0, 0.5)  # noqa: S311
        yield MeasurementEvent(
            ts=datetime.now(UTC),
            msg_size=8,
            iterations=None,
            bw_peak_gbps=0.0,
            bw_avg_gbps=0.0,
            msg_rate_mpps=None,
            lat_us=lat,
            lat_p99_us=lat + random.uniform(0.05, 0.2),  # noqa: S311
            tool_category="mock",
            sub_tool="mock",
        )
        await asyncio.sleep(interval)


# ─────────────────────────── 부하 명령 빌더 ───────────────────────────


def _build_ib_write_bw_args(
    req: StartRequest, settings: Settings, peer_rdma: str | None
) -> list[str]:
    """`ib_write_bw` 명령 인자. allowlist 검증된 값만 사용.

    `-m 4096` (RoCE path MTU): perftest default 1024 → ConnectX-6 HCA max 4096 으로
    명시. 라이브 측정 188 → 196 Gb/s (라인 레이트 98%) 향상.
    """
    args = [
        "ib_write_bw",
        "-d",
        settings.nic_device_a if peer_rdma is None else settings.nic_device_b,
        "-F",
        "--report_gbits",
        "-D",
        str(req.duration_sec),
        "-x",
        str(settings.rdma_gid_index),
        "-m",
        "4096",
        "-s",
        str(req.msg_size),
        "-q",
        str(req.qp_count),
    ]
    if req.bidir:
        args.append("-b")
    if peer_rdma:
        args.append(peer_rdma)
    return args


def _build_ib_read_lat_args(
    req: StartRequest, settings: Settings, peer_rdma: str | None
) -> list[str]:
    args = [
        "ib_read_lat",
        "-d",
        settings.nic_device_a if peer_rdma is None else settings.nic_device_b,
        "-F",
        "-D",
        str(req.duration_sec),
        "-x",
        str(settings.rdma_gid_index),
    ]
    if peer_rdma:
        args.append(peer_rdma)
    return args


def _build_iperf3_args(req: StartRequest, settings: Settings, *, server: bool) -> list[str]:
    if server:
        return ["iperf3", "-s", "-p", "5201", "-1"]
    args = [
        "iperf3",
        "-c",
        settings.server_a_rdma_ip,
        "-p",
        "5201",
        "-t",
        str(req.duration_sec),
        "-P",
        str(req.iperf3_streams),
    ]
    if req.bidir:
        args.append("--bidir")
    return args


# ─────────────────────────── BW 측정 (부하 + sysfs) ───────────────────────────


def _ssh_kwargs(settings: Settings) -> dict[str, Any]:
    return {
        "username": settings.ssh_user,
        "client_keys": [str(settings.ssh_key_path)],
        "known_hosts": str(settings.ssh_known_hosts),
    }


async def _read_iface_bytes(conn: asyncssh.SSHClientConnection, iface: str) -> tuple[int, int]:
    """mlx5 vport RDMA + TCP 카운터 합산 (64-bit, ethtool -S).

    RDMA 트래픽은 kernel bypass 라 `/sys/class/net/.../statistics` 에 안 잡힘.
    `ethtool -S` 의 `{rx,tx}_vport_rdma_unicast_bytes` (RDMA) +
    `{rx,tx}_vport_unicast_bytes` (TCP/일반) 합산으로 양쪽 모두 측정.
    """
    cmd = (
        f"ethtool -S {iface} | awk -F: '"
        "/rx_vport(_rdma)?_unicast_bytes:/ {rx+=$2} "
        "/tx_vport(_rdma)?_unicast_bytes:/ {tx+=$2} "
        "END {print rx+0; print tx+0}'"
    )
    result = await conn.run(cmd, check=False)
    stdout = result.stdout if isinstance(result.stdout, str) else ""
    lines = stdout.strip().splitlines()
    if len(lines) < 2:
        return 0, 0
    try:
        return int(lines[0].strip()), int(lines[1].strip())
    except ValueError:
        return 0, 0


async def _run_with_sysfs(req: StartRequest, settings: Settings) -> AsyncIterator[MeasurementEvent]:
    """BW 측정 — 부하(perftest 또는 iperf3) + sysfs 카운터 5Hz 폴링."""

    # 부하 명령 빌드
    if req.tool == "ib_write_bw":
        server_args = _build_ib_write_bw_args(req, settings, peer_rdma=None)
        client_args = _build_ib_write_bw_args(req, settings, peer_rdma=settings.server_a_rdma_ip)
    elif req.tool == "iperf3":
        server_args = _build_iperf3_args(req, settings, server=True)
        client_args = _build_iperf3_args(req, settings, server=False)
    else:
        raise ValueError(f"_run_with_sysfs: unsupported tool {req.tool}")

    measure_iface = settings.server_a_netdev
    poll_interval = 0.2  # 5Hz
    ssh_kw = _ssh_kwargs(settings)

    queue: asyncio.Queue[MeasurementEvent] = asyncio.Queue(maxsize=64)
    stop_event = asyncio.Event()

    async def _measure_loop() -> None:
        try:
            async with asyncssh.connect(settings.server_a_host, **ssh_kw) as mconn:
                prev_rx, prev_tx = await _read_iface_bytes(mconn, measure_iface)
                prev_t = asyncio.get_running_loop().time()
                while not stop_event.is_set():
                    try:
                        await asyncio.wait_for(stop_event.wait(), timeout=poll_interval)
                        break
                    except TimeoutError:
                        pass
                    curr_rx, curr_tx = await _read_iface_bytes(mconn, measure_iface)
                    now = asyncio.get_running_loop().time()
                    delta_t = now - prev_t
                    if req.bidir:
                        bw = parse_sysfs_stats(prev_rx + prev_tx, curr_rx + curr_tx, delta_t)
                    else:
                        bw = parse_sysfs_stats(prev_rx, curr_rx, delta_t)
                    evt = make_sysfs_event(bw, req.msg_size, req.tool)
                    with suppress(asyncio.QueueFull):
                        queue.put_nowait(evt)
                    prev_rx, prev_tx, prev_t = curr_rx, curr_tx, now
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: S110
            # 폴링 실패는 SSE 차원에서 별도 error 이벤트로 보고 (Phase 2 step 4)
            pass

    server_conn = None
    client_conn = None
    server_proc = None
    client_proc = None
    measure_task = None

    try:
        server_conn, client_conn = await asyncio.gather(
            asyncssh.connect(settings.server_a_host, **ssh_kw),
            asyncssh.connect(settings.server_b_host, **ssh_kw),
        )
        # 부하 시작 — RDMA server listen 시작까지 1~2초 필요 (QP 생성 등)
        server_proc = await server_conn.create_process(shlex.join(server_args))
        await asyncio.sleep(1.5)
        client_proc = await client_conn.create_process(shlex.join(client_args))

        # 측정 task 시작
        measure_task = asyncio.create_task(_measure_loop())

        # client 종료까지 큐에서 yield
        client_done = asyncio.create_task(client_proc.wait())
        try:
            while not client_done.done():
                try:
                    evt = await asyncio.wait_for(queue.get(), timeout=0.5)
                    yield evt
                except TimeoutError:
                    continue
        finally:
            client_done.cancel()
            with suppress(asyncio.CancelledError):
                await client_done

        # 종료 후 큐 잔여 flush
        stop_event.set()
        with suppress(Exception):
            await asyncio.wait_for(measure_task, timeout=2.0)
        while not queue.empty():
            yield queue.get_nowait()
    finally:
        stop_event.set()
        if measure_task is not None and not measure_task.done():
            measure_task.cancel()
            with suppress(Exception):
                await measure_task
        for proc in (client_proc, server_proc):
            if proc is None:
                continue
            try:
                proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except (TimeoutError, asyncssh.ProcessError, OSError):
                with suppress(Exception):
                    proc.kill()
        for conn in (client_conn, server_conn):
            if conn is None:
                continue
            with suppress(Exception):
                conn.close()
                await conn.wait_closed()


# ─────────────────────────── LAT 측정 (stdout 파싱) ───────────────────────────


async def _run_perftest_lat(
    req: StartRequest, settings: Settings
) -> AsyncIterator[MeasurementEvent]:
    """`ib_read_lat` 종료 시 stdout 1줄 파싱하여 1회 yield."""
    server_args = _build_ib_read_lat_args(req, settings, peer_rdma=None)
    client_args = _build_ib_read_lat_args(req, settings, peer_rdma=settings.server_a_rdma_ip)
    ssh_kw = _ssh_kwargs(settings)

    server_conn = None
    client_conn = None
    server_proc = None
    client_proc = None

    try:
        server_conn, client_conn = await asyncio.gather(
            asyncssh.connect(settings.server_a_host, **ssh_kw),
            asyncssh.connect(settings.server_b_host, **ssh_kw),
        )
        server_proc = await server_conn.create_process(shlex.join(server_args))
        await asyncio.sleep(0.2)
        client_proc = await client_conn.create_process(shlex.join(client_args))

        if client_proc.stdout is not None:
            async for raw_line in client_proc.stdout:
                line = raw_line.rstrip("\n")
                evt = parse_ib_read_lat_line(line)
                if evt is not None:
                    yield evt
        await client_proc.wait()
    finally:
        for proc in (client_proc, server_proc):
            if proc is None:
                continue
            try:
                proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except (TimeoutError, asyncssh.ProcessError, OSError):
                with suppress(Exception):
                    proc.kill()
        for conn in (client_conn, server_conn):
            if conn is None:
                continue
            with suppress(Exception):
                conn.close()
                await conn.wait_closed()
