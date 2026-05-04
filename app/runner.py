"""측정 세션 실행. Spec → rules/measurement.md, rules/security.md."""

from __future__ import annotations

import asyncio
import math
import random
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import asyncssh

from app.parser import parse_ib_read_lat_line, parse_ib_write_bw_line, parse_iperf3_json
from app.schemas import MeasurementEvent

if TYPE_CHECKING:
    from app.config import Settings
    from app.schemas import StartRequest


# ─────────────────────────── 진입점 ───────────────────────────


async def run_session(
    req: StartRequest, settings: Settings | None = None
) -> AsyncIterator[MeasurementEvent]:
    """`/api/start` 가 호출하는 메인 진입점.

    tool 에 따라 mock/perftest/iperf3 분기.
    """
    if req.tool == "mock":
        async for evt in mock_session(req):
            yield evt
        return

    if settings is None:
        raise ValueError("Settings required for non-mock tools")

    if req.tool in ("ib_write_bw", "ib_read_lat"):
        async for evt in _run_perftest(req, settings):
            yield evt
        return

    if req.tool == "iperf3":
        async for evt in _run_iperf3(req, settings):
            yield evt
        return

    raise ValueError(f"unknown tool: {req.tool}")


# ─────────────────────────── mock generator ───────────────────────────


async def mock_session(req: StartRequest) -> AsyncIterator[MeasurementEvent]:
    """NIC 부재 환경용 generator. 200G NIC + RoCE 동작 모사 (10Hz).

    Spec: rules/measurement.md §데모 모드 (mock).
    - UNI:   baseline 187, 진폭 8, σ=1.5, cap 199
    - BIDIR: baseline 374, 진폭 14, σ=2.5, cap 396
    - 30초 주기 sine + 가우시안 근사 노이즈
    """
    if req.tool == "ib_read_lat":
        async for evt in _mock_lat_session(req):
            yield evt
        return

    interval = 0.1  # 10Hz
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
        # 3-sample sum 으로 가우시안 근사 (mockup 과 동일 식)
        noise = (random.random() + random.random() + random.random() - 1.5) * sigma  # noqa: S311
        bw_avg = max(0.0, min(cap, base_avg + sine + noise))
        bw_peak = bw_avg + random.uniform(0.5, 1.5)  # noqa: S311

        yield MeasurementEvent(
            ts=datetime.now(timezone.utc),
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
    """ib_read_lat 모사 — 1.5~2.0µs 노이즈, 10Hz."""
    interval = 0.1
    loop = asyncio.get_running_loop()
    start = loop.time()
    end = start + req.duration_sec

    while loop.time() < end:
        lat = 1.5 + random.uniform(0.0, 0.5)  # noqa: S311
        yield MeasurementEvent(
            ts=datetime.now(timezone.utc),
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


# ─────────────────────────── perftest (실 SSH) ───────────────────────────


def _build_ib_write_bw_args(req: StartRequest, settings: Settings, peer_rdma: str | None) -> list[str]:
    """ib_write_bw 명령 인자 (insertion-safe, allowlist 검증된 값만)."""
    args = [
        "ib_write_bw",
        "-d", settings.nic_device_a if peer_rdma else settings.nic_device_b,
        "-F",
        "--report_gbits",
        "-D", str(req.duration_sec),
        "-x", str(settings.rdma_gid_index),
        "-s", str(req.msg_size),
        "-q", str(req.qp_count),
    ]
    if req.bidir:
        args.append("-b")
    if peer_rdma:
        args.append(peer_rdma)
    return args


def _build_ib_read_lat_args(req: StartRequest, settings: Settings, peer_rdma: str | None) -> list[str]:
    args = [
        "ib_read_lat",
        "-d", settings.nic_device_a if peer_rdma else settings.nic_device_b,
        "-F",
        "-D", str(req.duration_sec),
        "-x", str(settings.rdma_gid_index),
    ]
    if peer_rdma:
        args.append(peer_rdma)
    return args


async def _run_perftest(  # noqa: C901, PLR0915
    req: StartRequest, settings: Settings
) -> AsyncIterator[MeasurementEvent]:
    """양쪽 서버에 SSH 로 perftest 동시 실행, client stdout 파싱.

    rules/measurement.md §프로세스 라이프사이클 + rules/security.md §SSH 통일.
    Server B 가 client (A 의 RDMA IP 를 인자로). controller 는 양쪽에 SSH.
    """
    parser = parse_ib_write_bw_line if req.tool == "ib_write_bw" else parse_ib_read_lat_line
    build_args = _build_ib_write_bw_args if req.tool == "ib_write_bw" else _build_ib_read_lat_args

    server_args = build_args(req, settings, peer_rdma=None)            # A: server (인자 없음)
    client_args = build_args(req, settings, peer_rdma=settings.server_a_rdma_ip)  # B: client

    ssh_kwargs = {
        "username": settings.ssh_user,
        "client_keys": [str(settings.ssh_key_path)],
        "known_hosts": str(settings.ssh_known_hosts),
    }

    server_conn = None
    client_conn = None
    server_proc = None
    client_proc = None

    try:
        # 양쪽 SSH 동시 연결
        server_conn, client_conn = await asyncio.gather(
            asyncssh.connect(settings.server_a_host, **ssh_kwargs),
            asyncssh.connect(settings.server_b_host, **ssh_kwargs),
        )

        # Server A 측 server 모드 백그라운드 기동
        server_proc = await server_conn.create_process(server_args)
        await asyncio.sleep(0.2)  # listen 대기

        # Server B 측 client 실행
        client_proc = await client_conn.create_process(client_args)

        # client stdout 라인 단위 파싱 → yield
        if client_proc.stdout is None:
            return
        async for raw_line in client_proc.stdout:
            line = raw_line.rstrip("\n")
            evt = (
                parse_ib_write_bw_line(line, bidir=req.bidir)
                if req.tool == "ib_write_bw"
                else parse_ib_read_lat_line(line)
            )
            if evt is not None:
                yield evt

        await client_proc.wait()
    finally:
        # Cleanup: SIGTERM 5s grace → SIGKILL
        for proc in (client_proc, server_proc):
            if proc is None:
                continue
            try:
                proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except (TimeoutError, asyncssh.ProcessError, OSError):
                with _suppress_all():
                    proc.kill()
        for conn in (client_conn, server_conn):
            if conn is None:
                continue
            with _suppress_all():
                conn.close()
                await conn.wait_closed()
    # parser 미사용 변수 회피용 참조 (실제로는 위 분기에서 직접 호출)
    _ = parser


# ─────────────────────────── iperf3 (실 SSH) ───────────────────────────


async def _run_iperf3(  # noqa: C901
    req: StartRequest, settings: Settings
) -> AsyncIterator[MeasurementEvent]:
    """iperf3 -s (Server A) + iperf3 -c -J (Server B). JSON 일괄 파싱."""
    server_args = ["iperf3", "-s", "-p", "5201", "-1"]
    client_args = [
        "iperf3", "-c", settings.server_a_rdma_ip,
        "-p", "5201",
        "-t", str(req.duration_sec),
        "-P", str(req.iperf3_streams),
        "-J",
    ]
    if req.bidir:
        client_args.append("--bidir")

    ssh_kwargs = {
        "username": settings.ssh_user,
        "client_keys": [str(settings.ssh_key_path)],
        "known_hosts": str(settings.ssh_known_hosts),
    }

    server_conn = None
    client_conn = None
    server_proc = None
    try:
        server_conn, client_conn = await asyncio.gather(
            asyncssh.connect(settings.server_a_host, **ssh_kwargs),
            asyncssh.connect(settings.server_b_host, **ssh_kwargs),
        )
        server_proc = await server_conn.create_process(server_args)
        await asyncio.sleep(0.2)
        result = await client_conn.run(" ".join(client_args), check=False)
        stdout = result.stdout if isinstance(result.stdout, str) else ""
        for evt in parse_iperf3_json(stdout, bidir=req.bidir):
            yield evt
    finally:
        if server_proc is not None:
            with _suppress_all():
                server_proc.terminate()
                await asyncio.wait_for(server_proc.wait(), timeout=5.0)
        for conn in (client_conn, server_conn):
            if conn is None:
                continue
            with _suppress_all():
                conn.close()
                await conn.wait_closed()


# ─────────────────────────── helper ───────────────────────────


class _suppress_all:
    """모든 예외를 조용히 삼키는 context manager (cleanup 용)."""

    def __enter__(self) -> _suppress_all:
        return self

    def __exit__(self, *_args: object) -> bool:
        return True
