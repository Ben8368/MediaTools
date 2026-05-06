"""Workspace API routes."""

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.api.models import WorkspaceBody

GetWorkspace = Callable[[], dict[str, Any]]
SetWorkspace = Callable[..., dict[str, Any]]


def create_router(get_current_workspace: GetWorkspace, set_current_workspace: SetWorkspace) -> APIRouter:
    router = APIRouter()

    @router.get("/api/workspace")
    async def get_workspace():
        return JSONResponse(get_current_workspace())

    @router.post("/api/workspace")
    async def set_workspace_route(body: WorkspaceBody):
        try:
            workspace = set_current_workspace(body.project_root, enforce_allowed_root=True)
            return JSONResponse({"ok": True, "workspace": workspace})
        except Exception as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    return router
