#!/usr/bin/env python3
"""Phase 1 PoC CLI — `run_session` 을 stdout JSON 으로 실행.

사용 예:
    python scripts/poc.py --tool mock --duration 5
    python scripts/poc.py --tool ib_write_bw --duration 30 --msg-size 65536
    python scripts/poc.py --tool ib_write_bw --duration 30 --bidir
    python scripts/poc.py --tool iperf3 --duration 10 --streams 8

실 NIC 모드(`ib_write_bw`/`ib_read_lat`/`iperf3`)는 `.env` 필수.
mock 모드는 `.env` 없이 동작.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Any

from app.runner import run_session
from app.schemas import StartRequest


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "--tool",
        choices=["ib_write_bw", "ib_read_lat", "iperf3", "mock"],
        default="mock",
    )
    p.add_argument("--duration", type=int, default=5, help="seconds (5..600)")
    p.add_argument(
        "--msg-size",
        type=int,
        default=65536,
        help="bytes (allowlist: 64,1024,8192,65536,262144,1048576) — perftest only",
    )
    p.add_argument("--qp-count", type=int, default=1, help="QP count (1..16)")
    p.add_argument("--streams", type=int, default=8, help="iperf3 parallel streams (1..32)")
    p.add_argument("--bidir", action="store_true", help="bidirectional (-b / --bidir)")
    return p.parse_args()


def _serialize(evt: Any) -> str:
    """Pydantic 모델 → JSON 한 줄."""
    return evt.model_dump_json()


async def _main_async() -> int:
    args = _parse_args()

    try:
        req = StartRequest(
            tool=args.tool,
            duration_sec=args.duration,
            msg_size=args.msg_size,
            qp_count=args.qp_count,
            iperf3_streams=args.streams,
            bidir=args.bidir,
        )
    except Exception as e:  # pydantic ValidationError 등
        print(f"[error] invalid request: {e}", file=sys.stderr)
        return 2

    settings = None
    if args.tool != "mock":
        try:
            from app.config import Settings

            settings = Settings()  # type: ignore[call-arg]
        except Exception as e:
            print(
                f"[error] Settings load failed (use --tool mock for no-env demo): {e}",
                file=sys.stderr,
            )
            return 3

    print(
        f"[poc] tool={req.tool} duration={req.duration_sec}s msg={req.msg_size} "
        f"bidir={req.bidir} (Ctrl-C to stop)",
        file=sys.stderr,
    )

    count = 0
    try:
        async for evt in run_session(req, settings):
            print(_serialize(evt))
            count += 1
    except KeyboardInterrupt:
        print(f"[poc] interrupted after {count} events", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"[error] {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    print(f"[poc] done — {count} events", file=sys.stderr)
    return 0


def main() -> int:
    try:
        return asyncio.run(_main_async())
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
