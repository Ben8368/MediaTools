"""Legacy workspace file management API routes."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from services.api_models import (
    FilesCopyBody,
    FilesDeleteBody,
    FilesExtractIconBody,
    FilesMkdirBody,
    FilesMoveBody,
    FilesRenameBody,
)


def create_router(
    get_file_manager,
    get_current_workspace,
    get_preview_generator,
    get_preview_max_bytes,
    extract_icon,
) -> APIRouter:
    router = APIRouter()

    @router.get("/api/files/list")
    async def files_list(directory: str = ".", show_hidden: bool = False):
        try:
            result = get_file_manager().list_directory(directory, show_hidden)
            return JSONResponse({"ok": True, **result})
        except Exception as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    @router.post("/api/files/mkdir")
    async def files_mkdir(body: FilesMkdirBody):
        try:
            result = get_file_manager().create_directory(body.path)
            return JSONResponse({"ok": True, **result})
        except Exception as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    @router.delete("/api/files/delete")
    async def files_delete(body: FilesDeleteBody):
        try:
            result = get_file_manager().delete(body.path, body.recursive)
            return JSONResponse({"ok": True, **result})
        except Exception as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    @router.post("/api/files/rename")
    async def files_rename(body: FilesRenameBody):
        try:
            result = get_file_manager().rename(body.old_path, body.new_name)
            return JSONResponse({"ok": True, **result})
        except Exception as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    @router.post("/api/files/copy")
    async def files_copy(body: FilesCopyBody):
        try:
            result = get_file_manager().copy(body.source_path, body.dest_path)
            return JSONResponse({"ok": True, **result})
        except Exception as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    @router.post("/api/files/move")
    async def files_move(body: FilesMoveBody):
        try:
            result = get_file_manager().move(body.source_path, body.dest_path)
            return JSONResponse({"ok": True, **result})
        except Exception as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    @router.get("/api/files/info")
    async def files_info(path: str):
        try:
            result = get_file_manager().get_file_info(path)
            return JSONResponse({"ok": True, **result})
        except Exception as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    @router.get("/api/files/preview")
    async def files_preview(path: str, timestamp: str = "00:00:01"):
        try:
            file_manager = get_file_manager()
            preview_generator = get_preview_generator()
            full_path = file_manager._validate_path(path)
            if not full_path.is_file():
                return JSONResponse({"ok": False, "error": "Preview path must be a file"}, status_code=400)
            if full_path.stat().st_size > get_preview_max_bytes():
                return JSONResponse({"ok": False, "error": "File is too large to preview"}, status_code=413)

            can = preview_generator.can_preview(str(full_path))
            if not can["can_preview"]:
                return JSONResponse({"ok": False, "error": "File type not supported for preview"}, status_code=400)

            loop = asyncio.get_running_loop()
            full_path_str = str(full_path)

            if can["preview_type"] == "image":
                result = await loop.run_in_executor(None, lambda: preview_generator.generate_image_preview(full_path_str))
            elif can["preview_type"] == "video":
                cache_dir = Path(get_current_workspace()["cache_dir"]) / "previews"
                cache_dir.mkdir(parents=True, exist_ok=True)
                thumbnail_path = cache_dir / f"{full_path.stem}-{uuid.uuid4().hex}.jpg"
                result = await loop.run_in_executor(
                    None,
                    lambda: preview_generator.generate_video_thumbnail(
                        full_path_str,
                        timestamp,
                        output_path=str(thumbnail_path),
                    ),
                )
            else:
                result = await loop.run_in_executor(None, lambda: preview_generator.generate_audio_waveform(full_path_str))

            return JSONResponse({"ok": True, **result})
        except Exception as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    @router.post("/api/files/extract-icon")
    async def files_extract_icon(body: FilesExtractIconBody):
        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, lambda: extract_icon(body.exe_path, body.output_png))
            return JSONResponse(result)
        except Exception as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    return router
