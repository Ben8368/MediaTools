"""Media command API routes for download, transcode, and decrypt tasks."""

from __future__ import annotations

import asyncio
import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.api.models import DecryptorDecryptBody, EncoderTranscodeBody, FetcherDownloadBody


def _start_background(target) -> None:
    threading.Thread(target=target, daemon=True).start()


def create_router(
    job_registry,
    get_current_workspace,
    resolve_allowed_path,
    run_fetch_batch_stream,
    run_transcode_job,
    run_decrypt_job,
    result_success,
) -> APIRouter:
    router = APIRouter()

    @router.post("/api/fetcher/download")
    async def fetcher_download(body: FetcherDownloadBody):
        from backend.services.task_center import TaskStatus, TaskType, get_task_center

        workspace = get_current_workspace()
        platform = (body.platform or "auto").strip() or "auto"
        quality = (body.quality or "h264").strip().lower()
        supports_subtitles = platform not in {"short_video"}
        subtitles_enabled = bool(body.subtitles and supports_subtitles)
        try:
            output_dir = (
                resolve_allowed_path(body.output_dir, workspace)
                if body.output_dir.strip()
                else Path(workspace["downloads_dir"])
            )
            output_dir.mkdir(parents=True, exist_ok=True)
            if not output_dir.is_dir():
                raise ValueError("Download target must be a directory")
        except Exception as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

        task_center = get_task_center()
        task_id = str(uuid.uuid4())
        task_center.create_task(
            task_id=task_id,
            task_type=TaskType.DOWNLOAD,
            name=body.url[:48] or "Download task",
            params={
                "url": body.url,
                "platform": platform,
                "output_dir": str(output_dir),
                "subtitles": subtitles_enabled,
                "analyze": body.analyze,
                "quality": quality,
            },
        )

        def _run() -> None:
            result: dict[str, Any] | None = None
            subtitle_mode = "original_only" if subtitles_enabled else "none"
            video_codec_preference = quality if quality in {"best", "h264"} else "h264"
            job_id = job_registry.register(task_id, "fetcher", body.url[:48] or "Download task")

            def cancel_check() -> bool:
                return job_registry.is_cancelled(job_id) or task_center.get_task(task_id)["status"] == TaskStatus.CANCELLED.value

            task_center.update_task(task_id, status=TaskStatus.RUNNING)

            try:
                for snapshot in run_fetch_batch_stream(
                    urls=[body.url],
                    output_dir=str(output_dir),
                    naming_template="{index}_{title}_{upload_date}",
                    analyze=body.analyze and body.subtitles,
                    download_video=True,
                    video_codec_preference=video_codec_preference,
                    subtitle_mode=subtitle_mode,
                    subtitle_formats=["srt"],
                    cancel_check=cancel_check,
                ):
                    result = snapshot
                    progress = float(snapshot.get("progress_percent", 0.0))
                    stage = snapshot.get("progress_text", "running")
                    job_registry.update(job_id, stage, progress)
                    task_center.update_task(task_id, progress=progress, stage=stage)
            except Exception as exc:
                job_registry.finish(job_id, success=False)
                task_center.update_task(task_id, status=TaskStatus.FAILED, error=str(exc))
                return

            if not isinstance(result, dict):
                job_registry.finish(job_id, success=False)
                task_center.update_task(task_id, status=TaskStatus.FAILED, error="download failed: no result")
                return

            if job_registry.is_cancelled(job_id) or result.get("current_stage") == "cancelled":
                job_registry.finish(job_id, success=False)
                task_center.update_task(task_id, status=TaskStatus.CANCELLED)
                return

            items = result.get("items") or []
            info = items[0].get("info") if items and isinstance(items[0], dict) else None
            if isinstance(info, dict):
                success = bool(info.get("local_path") or info.get("subtitle_path"))
                job_registry.finish(job_id, success=success)
                task_center.update_task(
                    task_id,
                    status=TaskStatus.COMPLETED if success else TaskStatus.FAILED,
                    progress=100.0 if success else task_center.get_task(task_id)["progress"],
                    result=result,
                )
                return

            job_registry.finish(job_id, success=False)
            task_center.update_task(task_id, status=TaskStatus.FAILED, error="download failed")

        _start_background(_run)
        return JSONResponse({"ok": True, "task_id": task_id, "status": TaskStatus.PENDING.value})

    @router.post("/api/encoder/transcode")
    async def encoder_transcode(body: EncoderTranscodeBody):
        from backend.services.task_center import TaskStatus, TaskType, get_task_center

        task_center = get_task_center()
        task_id = str(uuid.uuid4())
        task_center.create_task(
            task_id=task_id,
            task_type=TaskType.TRANSCODE,
            name=Path(body.input_path).name or "Transcode task",
            params={
                "input_path": body.input_path,
                "output_path": body.output_path,
                "codec": body.codec,
                "crf": body.crf,
                "preset": body.preset,
                "vcodec": body.vcodec,
                "acodec": body.acodec,
            },
        )

        job_id = job_registry.register(task_id, "encoder", Path(body.input_path).name or "Transcode task")

        def progress_callback(progress: float):
            job_registry.update(job_id, "transcoding", progress)
            task_center.update_task(task_id, progress=progress, stage="transcoding")

        def cancel_check() -> bool:
            return job_registry.is_cancelled(job_id) or task_center.get_task(task_id)["status"] == TaskStatus.CANCELLED.value

        def _run():
            task_center.update_task(task_id, status=TaskStatus.RUNNING)
            return run_transcode_job(
                body.input_path,
                body.output_path,
                body.codec,
                body.crf,
                body.preset,
                body.vcodec,
                body.acodec,
                progress_callback=progress_callback,
                cancel_check=cancel_check,
            )

        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(None, _run)
        except Exception as exc:
            job_registry.finish(job_id, success=False)
            task_center.update_task(task_id, status=TaskStatus.FAILED, error=str(exc))
            raise

        if job_registry.is_cancelled(job_id) or task_center.get_task(task_id)["status"] == TaskStatus.CANCELLED.value:
            job_registry.finish(job_id, success=False)
            task_center.update_task(task_id, status=TaskStatus.CANCELLED)
        else:
            success = result_success(result)
            job_registry.finish(job_id, success=success)
            task_center.update_task(
                task_id,
                status=TaskStatus.COMPLETED if success else TaskStatus.FAILED,
                progress=100.0 if success else task_center.get_task(task_id)["progress"],
                result=result,
            )

        return JSONResponse(result)

    @router.post("/api/decryptor/decrypt")
    async def decryptor_decrypt(body: DecryptorDecryptBody):
        from backend.services.task_center import TaskStatus, TaskType, get_task_center

        task_center = get_task_center()
        task_id = str(uuid.uuid4())
        task_center.create_task(
            task_id=task_id,
            task_type=TaskType.DECRYPT,
            name=Path(body.input_path).name or "Decrypt task",
            params={
                "input_type": body.input_type,
                "input_path": body.input_path,
                "output_dir": body.output_dir,
                "remove_source": body.remove_source,
                "add_to_assets": body.add_to_assets,
            },
        )

        job_id = job_registry.register(task_id, "decryptor", Path(body.input_path).name or "Decrypt task")

        def cancel_check() -> bool:
            return job_registry.is_cancelled(job_id) or task_center.get_task(task_id)["status"] == TaskStatus.CANCELLED.value

        def _run():
            task_center.update_task(task_id, status=TaskStatus.RUNNING, stage="decrypting")
            job_registry.update(job_id, "decrypting", 10.0)
            return run_decrypt_job(
                body.input_type,
                body.input_path,
                body.output_dir,
                body.remove_source,
                body.add_to_assets,
                cancel_check=cancel_check,
            )

        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(None, _run)
        except Exception as exc:
            job_registry.finish(job_id, success=False)
            task_center.update_task(task_id, status=TaskStatus.FAILED, error=str(exc))
            raise

        if job_registry.is_cancelled(job_id) or task_center.get_task(task_id)["status"] == TaskStatus.CANCELLED.value:
            job_registry.finish(job_id, success=False)
            task_center.update_task(task_id, status=TaskStatus.CANCELLED)
        else:
            success = result_success(result)
            job_registry.finish(job_id, success=success)
            task_center.update_task(
                task_id,
                status=TaskStatus.COMPLETED if success else TaskStatus.FAILED,
                progress=100.0 if success else task_center.get_task(task_id)["progress"],
                result=result,
            )

        return JSONResponse(result)

    return router
