"""Filebrowser API routes."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from modules.filebrowser import (
    fb_copy,
    fb_delete,
    fb_empty_trash,
    fb_info,
    fb_list,
    fb_list_trash,
    fb_mkdir,
    fb_move,
    fb_purge_trash,
    fb_rename,
    fb_restore_trash,
    list_filebrowser_disks,
)
from services.api_models import (
    FilebrowserTrashBody,
    FilesCopyBody,
    FilesDeleteBody,
    FilesMkdirBody,
    FilesMoveBody,
    FilesRenameBody,
)
from services.filebrowser_runtime import (
    get_filebrowser_status,
    read_filebrowser_log,
    restart_filebrowser_service,
    start_filebrowser_service,
    stop_filebrowser_service,
)

router = APIRouter(prefix="/api/filebrowser", tags=["filebrowser"])


@router.get("/disks")
async def filebrowser_disks():
    return JSONResponse({"ok": True, "disks": list_filebrowser_disks()})


@router.get("/status")
async def filebrowser_status():
    try:
        return JSONResponse({"ok": True, **get_filebrowser_status()})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@router.post("/start")
async def filebrowser_start():
    try:
        return JSONResponse(start_filebrowser_service())
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@router.post("/stop")
async def filebrowser_stop():
    try:
        return JSONResponse(stop_filebrowser_service())
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@router.post("/restart")
async def filebrowser_restart():
    try:
        return JSONResponse(restart_filebrowser_service())
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@router.get("/log")
async def filebrowser_log(lines: int = 40):
    try:
        return JSONResponse({"ok": True, "log": read_filebrowser_log(lines)})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@router.get("/list")
async def filebrowser_list(directory: str = ".", show_hidden: bool = False):
    try:
        return JSONResponse({"ok": True, **fb_list(directory, show_hidden)})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@router.get("/info")
async def filebrowser_info(path: str):
    try:
        return JSONResponse({"ok": True, **fb_info(path)})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@router.post("/mkdir")
async def filebrowser_mkdir(body: FilesMkdirBody):
    try:
        return JSONResponse({"ok": True, **fb_mkdir(body.path)})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@router.post("/rename")
async def filebrowser_rename(body: FilesRenameBody):
    try:
        return JSONResponse({"ok": True, **fb_rename(body.old_path, body.new_name)})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@router.post("/move")
async def filebrowser_move(body: FilesMoveBody):
    try:
        return JSONResponse({"ok": True, **fb_move(body.source_path, body.dest_path)})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@router.post("/copy")
async def filebrowser_copy(body: FilesCopyBody):
    try:
        return JSONResponse({"ok": True, **fb_copy(body.source_path, body.dest_path)})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@router.delete("/delete")
async def filebrowser_delete(body: FilesDeleteBody):
    try:
        return JSONResponse({"ok": True, **fb_delete(body.path, body.recursive)})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@router.get("/trash")
async def filebrowser_trash():
    try:
        return JSONResponse({"ok": True, **fb_list_trash()})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@router.post("/trash/restore")
async def filebrowser_trash_restore(body: FilebrowserTrashBody):
    try:
        return JSONResponse({"ok": True, **fb_restore_trash(body.id, body.restore_path)})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@router.post("/trash/purge")
async def filebrowser_trash_purge(body: FilebrowserTrashBody):
    try:
        return JSONResponse({"ok": True, **fb_purge_trash(body.id)})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@router.delete("/trash/empty")
async def filebrowser_trash_empty():
    try:
        return JSONResponse({"ok": True, **fb_empty_trash()})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
