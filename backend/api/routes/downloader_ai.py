"""Downloader-specific AI routes.

These routes create persisted TaskCenter tasks so the downloader UI can surface
AI analyze/slice as first-class operations.
"""

from __future__ import annotations

import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.api.models import DownloaderAiAnalyzeBody, DownloaderAiSliceBody


def _start_background(target) -> None:
    threading.Thread(target=target, daemon=True).start()


def _task_media_paths(task: dict[str, Any]) -> tuple[str, str]:
    result = task.get("result") if isinstance(task.get("result"), dict) else {}
    items = result.get("items") if isinstance(result.get("items"), list) else []
    info = items[0].get("info") if items and isinstance(items[0], dict) else {}
    if not isinstance(info, dict):
        info = {}
    video_path = str(info.get("local_path") or "").strip()
    subtitle_path = str(info.get("subtitle_path") or "").strip()
    return video_path, subtitle_path


def create_router(job_registry, analyze_subtitle_for_workbench, export_clips_from_workbench) -> APIRouter:
    router = APIRouter(tags=["downloader"])

    @router.post("/api/downloader/ai/analyze")
    async def downloader_ai_analyze(body: DownloaderAiAnalyzeBody):
        from backend.services.task_center import TaskStatus, TaskType, get_task_center

        task_center = get_task_center()
        source = task_center.get_task(body.task_id)
        if not source:
            return JSONResponse({"ok": False, "error": "任务不存在"}, status_code=404)
        if source.get("status") != TaskStatus.COMPLETED.value:
            return JSONResponse({"ok": False, "error": "请先等待下载任务完成"}, status_code=400)

        _, subtitle_path = _task_media_paths(source)
        if not subtitle_path:
            return JSONResponse({"ok": False, "error": "未找到字幕文件路径"}, status_code=400)

        ai_task_id = str(uuid.uuid4())
        task_center.create_task(
            task_id=ai_task_id,
            task_type=TaskType.AI_ANALYZE,
            name=f"AI分析: {Path(subtitle_path).name or body.task_id}",
            params={
                "source_task_id": body.task_id,
                "subtitle_path": subtitle_path,
                "target_duration": body.target_duration,
                "extra_context": body.extra_context,
            }
        )

        def _run() -> None:
            job_id = job_registry.register(ai_task_id, "ai_analyze", Path(subtitle_path).name or "AI分析")
            task_center.update_task(ai_task_id, status=TaskStatus.RUNNING, progress=5.0, stage="准备分析")
            job_registry.update(job_id, "preparing", 5.0)
            try:
                task_center.update_task(ai_task_id, progress=15.0, stage="分析字幕")
                job_registry.update(job_id, "analyzing", 15.0)
                result = analyze_subtitle_for_workbench(subtitle_path, extra_context=body.extra_context, target_duration=body.target_duration)
            except Exception as exc:
                job_registry.finish(job_id, success=False)
                task_center.update_task(ai_task_id, status=TaskStatus.FAILED, error=str(exc), stage="分析失败")
                return

            ok = bool(result.get("ok"))
            job_registry.finish(job_id, success=ok)
            task_center.update_task(
                ai_task_id,
                status=TaskStatus.COMPLETED if ok else TaskStatus.FAILED,
                progress=100.0 if ok else 0.0,
                stage="分析完成" if ok else "分析失败",
                result=result,
                error="" if ok else str(result.get("message") or "analysis failed"),
            )

        _start_background(_run)
        return JSONResponse({"ok": True, "task_id": ai_task_id, "status": TaskStatus.PENDING.value})

    @router.post("/api/downloader/ai/slice")
    async def downloader_ai_slice(body: DownloaderAiSliceBody):
        from backend.services.task_center import TaskStatus, TaskType, get_task_center

        task_center = get_task_center()
        source = task_center.get_task(body.task_id)
        if not source:
            return JSONResponse({"ok": False, "error": "任务不存在"}, status_code=404)
        if source.get("status") != TaskStatus.COMPLETED.value:
            return JSONResponse({"ok": False, "error": "请先等待下载任务完成"}, status_code=400)

        video_path, subtitle_path = _task_media_paths(source)
        if not video_path:
            return JSONResponse({"ok": False, "error": "未找到本地视频文件路径"}, status_code=400)

        ai_task_id = str(uuid.uuid4())
        task_center.create_task(
            task_id=ai_task_id,
            task_type=TaskType.AI_SLICE,
            name=f"AI切片: {Path(video_path).name or body.task_id}",
            params={
                "source_task_id": body.task_id,
                "video_path": video_path,
                "subtitle_path": subtitle_path,
                "burn_subtitles": body.burn_subtitles,
                "padding": body.padding,
                "target_duration": body.target_duration,
                "extra_context": body.extra_context,
            },
        )

        def _run() -> None:
            job_id = job_registry.register(ai_task_id, "ai_slice", Path(video_path).name or "AI切片")
            task_center.update_task(ai_task_id, status=TaskStatus.RUNNING, progress=5.0, stage="准备切片")
            job_registry.update(job_id, "preparing", 5.0)

            try:
                clips_json = "[]"
                analysis_result: dict[str, Any] | None = None
                if subtitle_path:
                    task_center.update_task(ai_task_id, progress=20.0, stage="分析字幕")
                    job_registry.update(job_id, "analyzing", 20.0)
                    analysis_result = analyze_subtitle_for_workbench(subtitle_path, extra_context=body.extra_context, target_duration=body.target_duration)
                    if analysis_result.get("ok"):
                        clips_json = str(analysis_result.get("clips_json") or "[]")

                task_center.update_task(ai_task_id, progress=55.0, stage="调用 FFmpeg 切片")
                job_registry.update(job_id, "slicing", 55.0)
                export_result = export_clips_from_workbench(
                    video_path,
                    subtitle_path or "",
                    clips_json,
                    burn_subtitles=body.burn_subtitles,
                    start_padding=body.padding,
                    end_padding=body.padding,
                )
            except Exception as exc:
                job_registry.finish(job_id, success=False)
                task_center.update_task(ai_task_id, status=TaskStatus.FAILED, error=str(exc), stage="切片失败")
                return

            ok = bool(export_result.get("ok"))
            merged_result = {
                "analysis": analysis_result,
                "export": export_result,
                "video_path": video_path,
                "subtitle_path": subtitle_path,
            }
            job_registry.finish(job_id, success=ok)
            task_center.update_task(
                ai_task_id,
                status=TaskStatus.COMPLETED if ok else TaskStatus.FAILED,
                progress=100.0 if ok else 0.0,
                stage="切片完成" if ok else "切片失败",
                result=merged_result,
                error="" if ok else str(export_result.get("message") or "slice failed"),
            )

        _start_background(_run)
        return JSONResponse({"ok": True, "task_id": ai_task_id, "status": TaskStatus.PENDING.value})

    return router
