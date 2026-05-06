"""Workbench API routes."""

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.api.models import WorkbenchAnalyzeBody, WorkbenchExportBody

RunSimpleJob = Callable[[str, str, Callable[[], dict[str, Any]]], Awaitable[dict[str, Any]]]
ListWorkspaceMedia = Callable[[], dict[str, Any]]
AnalyzeSubtitle = Callable[[str, int], dict[str, Any]]
ExportClips = Callable[..., dict[str, Any]]


def create_router(
    run_simple_job: RunSimpleJob,
    list_workspace_media: ListWorkspaceMedia,
    analyze_subtitle_for_workbench: AnalyzeSubtitle,
    export_clips_from_workbench: ExportClips,
) -> APIRouter:
    router = APIRouter()

    @router.get("/api/workbench/media")
    async def workbench_media():
        return JSONResponse({"ok": True, **list_workspace_media()})

    @router.post("/api/workbench/analyze")
    async def workbench_analyze(body: WorkbenchAnalyzeBody):
        def _run():
            return analyze_subtitle_for_workbench(body.subtitle_path, body.clip_count)

        result = await run_simple_job("analysis", Path(body.subtitle_path).name or "字幕分析", _run)
        return JSONResponse(result)

    @router.post("/api/workbench/export")
    async def workbench_export(body: WorkbenchExportBody):
        def _run():
            return export_clips_from_workbench(
                body.video_path,
                body.subtitle_path,
                body.clips_json,
                burn_subtitles=body.burn_subtitles,
            )

        result = await run_simple_job("workbench", Path(body.video_path).name or "批量导出", _run)
        return JSONResponse(result)

    return router
