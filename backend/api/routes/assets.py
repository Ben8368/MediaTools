"""Asset library API routes."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse


def create_router(get_current_workspace, resolve_allowed_path, asset_library_cls, get_asset_scan_max_files) -> APIRouter:
    router = APIRouter()

    @router.get("/api/assets/list")
    async def assets_list(directory: str = "", keyword: str = "", asset_type: str = ""):
        try:
            workspace = get_current_workspace()
            root_dir = resolve_allowed_path(directory or workspace["project_root"], workspace)
            if not root_dir.is_dir():
                return JSONResponse({"ok": False, "error": "Asset scan path must be a directory"}, status_code=400)
            library = asset_library_cls(str(root_dir))
            assets = library.scan(str(root_dir), max_files=get_asset_scan_max_files())
        except Exception as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

        if keyword.strip():
            keyword_lower = keyword.strip().lower()
            assets = [item for item in assets if keyword_lower in item["name"].lower()]

        if asset_type.strip():
            assets = [item for item in assets if item["type"] == asset_type.strip()]

        return JSONResponse(
            {
                "ok": True,
                "directory": str(root_dir),
                "items": assets[:300],
                "stats": library.get_stats(),
                "truncated": library.truncated,
                "scan_limit": get_asset_scan_max_files(),
            }
        )

    return router
