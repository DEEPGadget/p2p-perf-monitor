"""공통 pytest fixture. Spec → rules/testing.md."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True, scope="session")
def _load_env() -> None:
    """.env 가 있으면 먼저 로드 (live 테스트), 부재 시 더미값 채움.

    pydantic-settings 는 환경변수 우선이라 conftest 의 더미값이 .env 보다 우선됨 →
    .env 가 있으면 그 값을 os.environ 에 먼저 넣어 setdefault 가 덮어쓰지 않게.
    """
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.split("#")[0].strip().strip('"').strip("'")
            os.environ.setdefault(key, value)

    # .env 가 없거나 누락 키 — 더미값으로 모듈 import 가능하게
    os.environ.setdefault("SERVER_A_HOST", "192.0.2.10")
    os.environ.setdefault("SERVER_B_HOST", "192.0.2.11")
    os.environ.setdefault("SERVER_A_RDMA_IP", "192.0.2.20")
    os.environ.setdefault("SERVER_B_RDMA_IP", "192.0.2.21")
