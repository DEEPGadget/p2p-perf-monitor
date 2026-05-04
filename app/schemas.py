"""Pydantic data models. Spec → .claude/rules/measurement.md, api.md."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Allow-listed message sizes for perftest -s option (security.md §입력 검증)
ALLOWED_MSG_SIZES: tuple[int, ...] = (64, 1024, 8192, 65536, 262144, 1048576)

# 서브툴 — API body의 tool 필드 + MeasurementEvent.sub_tool
ToolKind = Literal["ib_write_bw", "ib_read_lat", "iperf3", "mock"]

# 카테고리 — MeasurementEvent.tool_category + MEASUREMENT_TOOL env
ToolCategory = Literal["perftest", "iperf3", "mock"]

SessionStateValue = Literal["idle", "connecting", "running", "error"]

ErrorCode = Literal[
    "ssh_unreachable",
    "ssh_timeout",
    "ssh_auth_failed",
    "measure_failed",
    "temp_polling_failed",
    "parse_failed",
]

NicSource = Literal["mget_temp+ethtool", "sysfs+ethtool", "mlxlink", "mock"]


class StartRequest(BaseModel):
    """POST /api/start body. allowlist 검증."""

    model_config = ConfigDict(extra="forbid")

    tool: ToolKind = "ib_write_bw"
    duration_sec: int = Field(default=60, ge=5, le=600)
    msg_size: int = 65536
    qp_count: int = Field(default=1, ge=1, le=16)
    iperf3_streams: int = Field(default=8, ge=1, le=32)
    bidir: bool = False

    @field_validator("msg_size")
    @classmethod
    def _validate_msg_size(cls, v: int) -> int:
        if v not in ALLOWED_MSG_SIZES:
            raise ValueError(f"msg_size must be one of {ALLOWED_MSG_SIZES}")
        return v

    @model_validator(mode="after")
    def _validate_bidir_compat(self) -> StartRequest:
        # rules/measurement.md: ib_read_lat 은 bidir 의미 없음 → 422
        if self.bidir and self.tool == "ib_read_lat":
            raise ValueError("bidir=true is not supported for tool=ib_read_lat")
        return self


class SessionStatus(BaseModel):
    """API 응답 DTO + SSE 'status' event payload.

    내부 머신 상태값(SessionStateValue)과 외부 응답을 분리하기 위해 본 클래스를
    DTO 로 사용. 명명 규약 → rules/api.md.
    """

    state: SessionStateValue = "idle"
    tool: ToolKind | None = None
    started_at: datetime | None = None
    error: dict | None = None


class MeasurementEvent(BaseModel):
    """SSE 'measurement' event payload. perftest/iperf3/mock 출력 정규화.

    단위 통일: 대역폭은 Gb/s, 지연은 µs, 사이즈는 bytes.
    """

    ts: datetime
    msg_size: int
    iterations: int | None = None
    bw_peak_gbps: float
    bw_avg_gbps: float
    msg_rate_mpps: float | None = None
    lat_us: float | None = None
    lat_p99_us: float | None = None
    tool_category: ToolCategory
    sub_tool: ToolKind | None = None


class NicTelemetry(BaseModel):
    """SSE 'nic_temp' event payload. 4채널 (IC × 2 + Module × 2), 1Hz 폴링.

    측정 실패한 채널은 None — UI 는 직전 값 유지 또는 '—°C' 표시.
    """

    ts: datetime
    server_a_ic_c: float | None = None
    server_b_ic_c: float | None = None
    server_a_module_c: float | None = None
    server_b_module_c: float | None = None
    source: NicSource


class ErrorEvent(BaseModel):
    """SSE 'error' event payload. 에러 코드 카탈로그 → rules/api.md."""

    code: ErrorCode
    message: str
    host: str | None = None
    stderr_tail: str | None = None
