from typing import Any

from fastapi import APIRouter

from app.services import triton_service

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def health_live() -> dict[str, Any]:
    return {"status": "ok"}


@router.get("/ready")
async def health_ready() -> dict[str, Any]:
    triton_live = await triton_service.health_check()
    return {
        "status": "ready" if triton_live else "not ready",
        "triton": triton_live,
    }
