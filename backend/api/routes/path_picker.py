"""Path picker API routes."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.services.path_picker import get_path_picker_roots, list_path_picker_directory
from backend.services.workspace import get_current_workspace

router = APIRouter()


@router.get("/api/path-picker/roots")
async def path_picker_roots():
    try:
        return JSONResponse({"ok": True, "roots": get_path_picker_roots(get_current_workspace())})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)


@router.get("/api/path-picker/list")
async def path_picker_list(root_id: str = "workspace", path: str = ".", show_hidden: bool = False):
    try:
        result = list_path_picker_directory(
            root_id=root_id,
            path=path,
            show_hidden=show_hidden,
            workspace=get_current_workspace(),
        )
        return JSONResponse({"ok": True, **result})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
