"""System status, metrics, and module catalog API routes."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from adapters import FFmpegAdapter, PhotoshopAutomationAdapter, UmcliAdapter, YtdlpAdapter
from backend.config import ANALYSIS_MODEL
from patches import get_patch_diagnostics
from backend.services.api_modules import build_module_catalog
from backend.services.runtime.filebrowser import get_filebrowser_status
from backend.services.system_fonts import list_system_fonts
from backend.services.system_monitor import get_runtime_metrics


def build_system_snapshot() -> dict:
    ytdlp_status = YtdlpAdapter().get_status()
    ffmpeg_info = FFmpegAdapter().get_info()
    umcli_ok = UmcliAdapter().is_available()
    patch_info = get_patch_diagnostics()
    return {
        "model": ANALYSIS_MODEL,
        "ytdlp": ytdlp_status.get("installed", False),
        "ytdlp_version": ytdlp_status.get("version", ""),
        "ffmpeg": ffmpeg_info.get("installed", False),
        "ffmpeg_version": ffmpeg_info.get("version", ""),
        "umcli": umcli_ok,
        "patches": patch_info,
    }


def build_modules_response(get_current_workspace, get_auditor_status, get_wechat_moments_status) -> dict:
    workspace = get_current_workspace()
    auditor_ok = get_auditor_status(workspace).get("available", False)
    ffmpeg_ok = FFmpegAdapter().get_info().get("installed", False)
    filebrowser_ok = get_filebrowser_status().get("running", False)
    photoshop_ok = PhotoshopAutomationAdapter().get_status().get("available", False)
    umcli_ok = UmcliAdapter().is_available()
    wechat_ok = get_wechat_moments_status(workspace).get("available", False)
    ytdlp_ok = YtdlpAdapter().get_status().get("installed", False)

    return build_module_catalog(
        auditor_ok=auditor_ok,
        ffmpeg_ok=ffmpeg_ok,
        filebrowser_ok=filebrowser_ok,
        photoshop_ok=photoshop_ok,
        umcli_ok=umcli_ok,
        wechat_ok=wechat_ok,
        ytdlp_ok=ytdlp_ok,
    )


def create_router(get_current_workspace, get_auditor_status, get_wechat_moments_status) -> APIRouter:
    router = APIRouter()

    @router.get("/api/system/status")
    async def system_status():
        return JSONResponse(build_system_snapshot())

    @router.get("/api/system/metrics")
    async def system_metrics():
        return JSONResponse(get_runtime_metrics())

    @router.get("/api/modules")
    async def list_modules():
        return JSONResponse(
            build_modules_response(get_current_workspace, get_auditor_status, get_wechat_moments_status)
        )

    @router.get("/api/system/fonts")
    async def system_fonts(query: str = "", limit: int = 500):
        return JSONResponse(list_system_fonts(query=query, limit=limit))

    return router
