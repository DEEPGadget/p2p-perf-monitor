"""GET /api/health — FastAPI alive 체크 (SSH 미시도)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}
