"""공통 pytest fixture. Spec → rules/testing.md."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def _set_dummy_env() -> None:
    """비-mock 모듈을 import 할 때 Settings 가 .env 부재로 실패하지 않도록.

    실제 SSH/RDMA 동작은 @pytest.mark.live 테스트에서만 수행.
    """
    os.environ.setdefault("SERVER_A_HOST", "192.0.2.10")
    os.environ.setdefault("SERVER_B_HOST", "192.0.2.11")
    os.environ.setdefault("SERVER_A_RDMA_IP", "192.0.2.20")
    os.environ.setdefault("SERVER_B_RDMA_IP", "192.0.2.21")
