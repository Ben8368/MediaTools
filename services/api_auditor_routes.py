"""Auditor API routes."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from services.api_models import AuditorConfigBody


def create_router(
    run_simple_job,
    get_current_workspace,
    get_auditor_config,
    get_auditor_status,
    run_auditor_scan_once,
    save_auditor_config,
) -> APIRouter:
    router = APIRouter()

    @router.get("/api/auditor/status")
    async def auditor_status():
        return JSONResponse(get_auditor_status(get_current_workspace()))

    @router.get("/api/auditor/config")
    async def auditor_config():
        return JSONResponse(get_auditor_config(get_current_workspace()))

    @router.put("/api/auditor/config")
    async def auditor_save_config(body: AuditorConfigBody):
        try:
            return JSONResponse(save_auditor_config(body.config, get_current_workspace()))
        except Exception as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    @router.post("/api/auditor/run-once")
    async def auditor_run_once():
        def _run():
            return run_auditor_scan_once(get_current_workspace())

        result = await run_simple_job("auditor", "Auditor scan once", _run)
        return JSONResponse(result)

    return router
