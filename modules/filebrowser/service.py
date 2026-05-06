"""Filebrowser file operation service.

Phase 1 performs local filesystem operations directly. Path safety is owned by
filebrowser resolver so the UI can browse local and mapped drives returned by
filebrowser disks endpoint.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import string
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.config import BASE_DIR

_WINDOWS_DRIVE_CACHE: list[dict[str, Any]] | None = None
TRASH_DIR = BASE_DIR / "runtime" / "filebrowser-trash"
TRASH_META = "metadata.json"
logger = logging.getLogger("filebrowser")


def list_filebrowser_disks() -> list[dict[str, Any]]:
    """Return local and mapped drive roots that are actually readable."""
    global _WINDOWS_DRIVE_CACHE
    if os.name != "nt":
        try:
            usage = shutil.disk_usage("/")
            return [{"name": "Root (/)", "path": "/", "total": usage.total, "used": usage.used, "free": usage.free}]
        except OSError:
            return []

    disks: list[dict[str, Any]] = []
    for letter in string.ascii_uppercase:
        root = f"{letter}:\\"
        try:
            usage = shutil.disk_usage(root)
            # A quick directory probe filters out unavailable or permission-blocked mappings.
            next(Path(root).iterdir(), None)
            disks.append({
                "name": f"本地磁盘 ({letter}:)",
                "path": root,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
            })
        except (OSError, PermissionError):
            continue
    _WINDOWS_DRIVE_CACHE = disks
    return disks


def _filebrowser_roots() -> list[Path]:
    disks = _WINDOWS_DRIVE_CACHE or list_filebrowser_disks()
    return [Path(item["path"]).resolve() for item in disks]


def _is_drive_root(path: Path) -> bool:
    resolved = path.resolve()
    return any(resolved == root for root in _filebrowser_roots())


def resolve_filebrowser_path(user_path: str | Path) -> Path:
    if user_path is None or str(user_path).strip() in {"", "."}:
        roots = _filebrowser_roots()
        if not roots:
            raise ValueError("No accessible filebrowser roots")
        return roots[0]

    raw = Path(user_path)
    if not raw.is_absolute():
        raise ValueError("Filebrowser paths must be absolute")

    resolved = raw.resolve()
    for root in _filebrowser_roots():
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue
    raise ValueError("Path is outside accessible filebrowser roots")


def _stat(path: Path) -> dict[str, Any]:
    stat = path.stat()
    info: dict[str, Any] = {
        "name": path.name,
        "path": str(path),
        "size": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "is_directory": path.is_dir(),
        "is_file": path.is_file(),
    }
    if path.is_file():
        info["extension"] = path.suffix.lower()
    return info


def _trash_item_dir(trash_id: str) -> Path:
    return TRASH_DIR / trash_id


def _trash_metadata_path(trash_id: str) -> Path:
    return _trash_item_dir(trash_id) / TRASH_META


def _load_trash_metadata(trash_id: str) -> dict[str, Any]:
    meta_path = _trash_metadata_path(trash_id)
    if not meta_path.is_file():
        raise FileNotFoundError(f"Trash item not found: {trash_id}")
    return json.loads(meta_path.read_text(encoding="utf-8"))


def _write_trash_metadata(trash_id: str, metadata: dict[str, Any]) -> None:
    _trash_metadata_path(trash_id).write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


def _trash_entry_from_metadata(trash_id: str, metadata: dict[str, Any]) -> dict[str, Any]:
    trashed_path = _trash_item_dir(trash_id) / metadata["stored_name"]
    return {
        "id": trash_id,
        "name": metadata.get("name", ""),
        "original_path": metadata.get("original_path", ""),
        "deleted_at": metadata.get("deleted_at", ""),
        "type": metadata.get("type", "file"),
        "size": metadata.get("size", 0),
        "stored_path": str(trashed_path),
    }


def fb_list_trash() -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    if not TRASH_DIR.exists():
        return {"items": items}
    for item_dir in TRASH_DIR.iterdir():
        if not item_dir.is_dir():
            continue
        try:
            metadata = _load_trash_metadata(item_dir.name)
            items.append(_trash_entry_from_metadata(item_dir.name, metadata))
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            continue
    items.sort(key=lambda item: item.get("deleted_at", ""), reverse=True)
    return {"items": items}


def fb_restore_trash(trash_id: str, restore_path: str | None = None) -> dict[str, Any]:
    metadata = _load_trash_metadata(trash_id)
    source = _trash_item_dir(trash_id) / metadata["stored_name"]
    if not source.exists():
        raise FileNotFoundError(f"Trash payload not found: {trash_id}")
    dest = resolve_filebrowser_path(restore_path or metadata["original_path"])
    if dest.exists():
        raise FileExistsError(f"Restore destination already exists: {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(dest))
    shutil.rmtree(_trash_item_dir(trash_id), ignore_errors=True)
    logger.info(
        "Restored filebrowser trash item %s to %s",
        trash_id,
        dest,
        extra={"event": f"恢复回收站项目: {metadata.get('original_path')} -> {dest}", "user": "local"},
    )
    return {"restored": str(dest), "id": trash_id}


def fb_purge_trash(trash_id: str) -> dict[str, Any]:
    metadata = _load_trash_metadata(trash_id)
    shutil.rmtree(_trash_item_dir(trash_id))
    logger.warning(
        "Purged filebrowser trash item %s",
        trash_id,
        extra={"event": f"彻底删除回收站项目: {metadata.get('original_path')}", "user": "local"},
    )
    return {"purged": trash_id}


def fb_empty_trash() -> dict[str, Any]:
    count = len(fb_list_trash()["items"])
    if TRASH_DIR.exists():
        shutil.rmtree(TRASH_DIR)
    logger.warning("Emptied filebrowser trash", extra={"event": f"清空回收站: {count} 项", "user": "local"})
    return {"deleted": count}


def fb_list(directory: str, show_hidden: bool = False) -> dict[str, Any]:
    target = resolve_filebrowser_path(directory)
    if not target.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    if not target.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    files, directories = [], []
    for item in target.iterdir():
        if not show_hidden and item.name.startswith("."):
            continue
        try:
            stat = item.stat()
            is_dir = item.is_dir()
        except (OSError, PermissionError):
            continue
        entry = {
            "name": item.name,
            "path": str(item),
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        }
        if is_dir:
            entry["type"] = "directory"
            directories.append(entry)
        else:
            entry["type"] = "file"
            entry["extension"] = item.suffix.lower()
            files.append(entry)

    return {
        "path": str(target),
        "files": sorted(files, key=lambda x: x["name"].lower()),
        "directories": sorted(directories, key=lambda x: x["name"].lower()),
    }


def fb_info(path: str) -> dict[str, Any]:
    target = resolve_filebrowser_path(path)
    if not target.exists():
        raise FileNotFoundError(f"Not found: {path}")
    return _stat(target)


def fb_mkdir(path: str) -> dict[str, Any]:
    target = resolve_filebrowser_path(path)
    if target.exists():
        raise FileExistsError(f"Already exists: {path}")
    target.mkdir(parents=True, exist_ok=False)
    return {"ok": True, "path": str(target)}


def fb_rename(old_path: str, new_name: str) -> dict[str, Any]:
    source = resolve_filebrowser_path(old_path)
    clean = (new_name or "").strip()
    if not clean or clean in {".", ".."}:
        raise ValueError("Invalid new name")
    if Path(clean).name != clean:
        raise ValueError("New name must not contain path separators")
    if not source.exists():
        raise FileNotFoundError(f"Not found: {old_path}")
    dest = resolve_filebrowser_path(source.parent / clean)
    if dest.exists():
        raise FileExistsError(f"Already exists: {clean}")
    source.rename(dest)
    return {"ok": True, "old_path": str(source), "new_path": str(dest)}


def fb_move(source_path: str, dest_path: str) -> dict[str, Any]:
    source = resolve_filebrowser_path(source_path)
    dest = resolve_filebrowser_path(dest_path)
    if not source.exists():
        raise FileNotFoundError(f"Not found: {source_path}")
    if dest.exists():
        raise FileExistsError(f"Already exists: {dest_path}")
    shutil.move(str(source), str(dest))
    return {"ok": True, "source": str(source), "destination": str(dest)}


def fb_copy(source_path: str, dest_path: str) -> dict[str, Any]:
    source = resolve_filebrowser_path(source_path)
    dest = resolve_filebrowser_path(dest_path)
    if not source.exists():
        raise FileNotFoundError(f"Not found: {source_path}")
    if dest.exists():
        raise FileExistsError(f"Already exists: {dest_path}")
    if source.is_dir():
        shutil.copytree(source, dest)
    else:
        shutil.copy2(source, dest)
    return {"ok": True, "source": str(source), "destination": str(dest)}


def fb_delete(path: str, recursive: bool = False) -> dict[str, Any]:
    target = resolve_filebrowser_path(path)
    if not target.exists():
        raise FileNotFoundError(f"Not found: {path}")
    if _is_drive_root(target):
        raise ValueError("Refusing to delete a drive root")
    if target.is_dir():
        if not recursive:
            raise IsADirectoryError(f"Is a directory, use recursive=True: {path}")
    TRASH_DIR.mkdir(parents=True, exist_ok=True)
    trash_id = datetime.now().strftime("%Y%m%d%H%M%S") + "-" + uuid4().hex[:8]
    item_dir = _trash_item_dir(trash_id)
    item_dir.mkdir(parents=True, exist_ok=False)
    stored_name = target.name or "deleted"
    trashed_path = item_dir / stored_name
    stat = target.stat()
    metadata = {
        "id": trash_id,
        "name": target.name,
        "original_path": str(target),
        "stored_name": stored_name,
        "deleted_at": datetime.now().isoformat(),
        "type": "directory" if target.is_dir() else "file",
        "size": stat.st_size,
    }
    _write_trash_metadata(trash_id, metadata)
    shutil.move(str(target), str(trashed_path))
    logger.warning(
        "Moved filebrowser path to trash: %s -> %s",
        target,
        trashed_path,
        extra={"event": f"移入回收站: {target}", "user": "local"},
    )
    return {"ok": True, "deleted": str(target), "trash_id": trash_id, "trash_path": str(trashed_path)}
