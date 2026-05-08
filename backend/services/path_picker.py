"""Restricted filesystem browser for frontend path picking."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from backend.config import BASE_DIR, WORKSPACE_ALLOWED_ROOTS
from backend.services.workspace import get_current_workspace
from modules.filebrowser import resolve_filebrowser_path as _resolve_under_filebrowser_roots


def _dedupe_roots(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    roots: list[dict[str, str]] = []
    for item in items:
        path = str(Path(item["path"]).expanduser().resolve())
        if path in seen:
            continue
        seen.add(path)
        roots.append({**item, "path": path})
    return roots


def get_path_picker_roots(workspace: dict | None = None) -> list[dict[str, str]]:
    ws = workspace or get_current_workspace()
    candidates = [
        {"id": "workspace", "label": "Current workspace", "path": ws["project_root"]},
        {"id": "downloads", "label": "Downloads", "path": ws["downloads_dir"]},
        {"id": "assets", "label": "Assets", "path": ws["assets_dir"]},
        {"id": "exports", "label": "Exports", "path": ws["exports_dir"]},
        {"id": "projects", "label": "Projects", "path": str(BASE_DIR / "projects")},
    ]
    for index, root in enumerate(WORKSPACE_ALLOWED_ROOTS):
        candidates.append({"id": f"allowed_{index}", "label": f"Allowed root {index + 1}", "path": str(root)})
    return _dedupe_roots(candidates)


def _resolve_root(root_id: str, workspace: dict | None = None) -> Path:
    for root in get_path_picker_roots(workspace):
        if root["id"] == root_id:
            return Path(root["path"]).resolve()
    raise ValueError(f"Unknown path picker root: {root_id}")


def _resolve_child(root: Path, relative_path: str) -> Path:
    raw = Path(relative_path or ".")
    target = raw if raw.is_absolute() else root / raw
    target = target.resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise ValueError("Path is outside the selected root")
    return target


def resolve_allowed_path(path: str, workspace: dict | None = None) -> Path:
    """解析用户路径：先匹配工作区/path-picker 根目录，再放宽到 filebrowser 可选盘符路径。"""
    ws = workspace or get_current_workspace()
    raw = Path(path or ws["project_root"]).expanduser()
    target = raw if raw.is_absolute() else Path(ws["project_root"]) / raw
    target = target.resolve()
    for root in get_path_picker_roots(ws):
        allowed_root = Path(root["path"]).resolve()
        try:
            target.relative_to(allowed_root)
            return target
        except ValueError:
            continue
    # 目录选择器等 UI 可走 filebrowser 盘符列表；写入类 API 应与可见范围一致。
    try:
        return _resolve_under_filebrowser_roots(target)
    except ValueError:
        pass
    raise ValueError("Path is outside allowed roots")


def _entry(path: Path, root: Path) -> dict[str, Any]:
    stat = path.stat()
    is_dir = path.is_dir()
    return {
        "name": path.name,
        "path": str(path),
        "relative_path": "." if path == root else str(path.relative_to(root)),
        "type": "directory" if is_dir else "file",
        "size": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "extension": "" if is_dir else path.suffix.lower(),
    }


def list_path_picker_directory(
    *,
    root_id: str,
    path: str = ".",
    show_hidden: bool = False,
    workspace: dict | None = None,
) -> dict[str, Any]:
    root = _resolve_root(root_id, workspace)
    root.mkdir(parents=True, exist_ok=True)
    target = _resolve_child(root, path)
    if not target.exists():
        if target.parent.exists() and target.parent.is_dir():
            target = target.parent
        else:
            raise FileNotFoundError(f"Path does not exist: {path}")
    elif not target.is_dir():
        target = target.parent

    directories: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []
    for item in target.iterdir():
        if not show_hidden and item.name.startswith("."):
            continue
        try:
            info = _entry(item, root)
        except OSError:
            continue
        if item.is_dir():
            directories.append(info)
        elif item.is_file():
            files.append(info)

    parent = None
    if target != root:
        parent = "." if target.parent == root else str(target.parent.relative_to(root))

    return {
        "root": {"id": root_id, "path": str(root)},
        "path": str(target),
        "relative_path": "." if target == root else str(target.relative_to(root)),
        "parent": parent,
        "directories": sorted(directories, key=lambda item: item["name"].lower()),
        "files": sorted(files, key=lambda item: item["name"].lower()),
    }
