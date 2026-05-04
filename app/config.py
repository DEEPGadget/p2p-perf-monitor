"""Settings loaded from .env. Spec → CLAUDE.md §환경변수, .env.example."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """런타임 설정. .env 또는 환경변수에서 로드."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ─── SSH 접근 (관리망) ───
    server_a_host: str
    server_b_host: str
    ssh_user: str = "deepgadget"
    ssh_key_path: Path = Path("/etc/p2p-monitor/id_ed25519")
    ssh_known_hosts: Path = Path("/etc/p2p-monitor/known_hosts")

    # ─── RDMA 망 (perftest 인자) ───
    server_a_rdma_ip: str
    server_b_rdma_ip: str

    # ─── NIC 디바이스 (양쪽 동일 포트, RoCE 전환 후 확정) ───
    nic_device_a: str = "mlx5_0"
    nic_device_b: str = "mlx5_0"

    # ─── RoCE / RDMA ───
    rdma_gid_index: int = 3
    rdma_mtu: int = 9000

    # ─── 측정 도구 카테고리 default ───
    measurement_tool: Literal["perftest", "iperf3", "mock"] = "perftest"

    # ─── FastAPI 바인드 ───
    bind_host: str = "0.0.0.0"  # noqa: S104  (운영 의도, security.md §네트워크 노출)
    bind_port: int = 8080

    # ─── 개발 / 로깅 ───
    dev_cors: bool = False
    log_level: str = "INFO"
