"""Log viewer API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from services.log_buffer import get_log_buffer

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("")
async def get_logs(level: str = "", module: str = "", page: int = 1, page_size: int = 50):
    """Return buffered backend logs with filtering and pagination."""
    buffer = get_log_buffer()
    return JSONResponse(buffer.get_records(level=level or "", module=module or "", page=page, page_size=page_size))


@router.get("/modules")
async def get_log_modules():
    """Return available log modules and levels."""
    buffer = get_log_buffer()
    return JSONResponse({"ok": True, "modules": buffer.get_modules(), "levels": buffer.get_levels()})


@router.post("/clear")
async def clear_logs():
    """Clear all buffered backend log records."""
    get_log_buffer().clear()
    logging.getLogger("api.logs").info(
        "Log buffer cleared",
        extra={"user": "local", "event": "清空日志缓冲区"},
    )
    return JSONResponse({"ok": True})
