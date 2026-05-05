"""Settings loaded from .env. Spec → CLAUDE.md §환경변수, .env.example."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import field_validator
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
    ssh_key_path: Path = Path("~/.ssh/p2p_monitor_ed25519")
    ssh_known_hosts: Path = Path("~/.ssh/known_hosts_p2p")

    @field_validator("ssh_key_path", "ssh_known_hosts", mode="after")
    @classmethod
    def _expand_user(cls, v: Path) -> Path:
        # ~ → 절대경로 확장 (asyncssh 가 ~ 직접 인식 못 함)
        return v.expanduser()

    # ─── RDMA 망 (perftest 인자) ───
    server_a_rdma_ip: str
    server_b_rdma_ip: str

    # ─── NIC RDMA device (perftest -d 인자) ───
    # dg5W: 전통 명명 mlx5_0
    # dg5R: udev 'rocep<bus_dec>s<slot>f<func>' → rocep100s0f0
    nic_device_a: str = "mlx5_0"
    nic_device_b: str = "rocep100s0f0"

    # ─── NIC netdev 인터페이스 (sysfs BW 폴링 / ethtool 트랜시버 온도) ───
    server_a_netdev: str = "enp2s0f0np0"
    server_b_netdev: str = "ens7f0np0"

    # ─── RoCE / RDMA ───
    # GID 인덱스는 서버별 RoCE v2 IPv4 GID 위치가 다를 수 있어 분리.
    # `show_gids` 로 v2 행의 INDEX 확인 (dg5W=3, dg5R=5 라이브 검증).
    rdma_gid_index_a: int = 3
    rdma_gid_index_b: int = 5
    rdma_mtu: int = 9000

    # ─── 측정 도구 카테고리 default ───
    measurement_tool: Literal["perftest", "iperf3", "mock"] = "perftest"

    # ─── FastAPI 바인드 ───
    bind_host: str = "0.0.0.0"  # noqa: S104  (운영 의도, security.md §네트워크 노출)
    bind_port: int = 8080

    # ─── 개발 / 로깅 ───
    dev_cors: bool = False
    log_level: str = "INFO"
