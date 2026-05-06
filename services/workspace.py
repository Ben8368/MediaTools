"""Single project workspace management."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from backend.config import BASE_DIR, WORKSPACE_ALLOWED_ROOTS

RUNTIME_DIR = BASE_DIR / "runtime"
WORKSPACE_FILE = RUNTIME_DIR / "workspace.json"
DEFAULT_WORKSPACE_ROOT = BASE_DIR / "projects" / "default"
logger = logging.getLogger(__name__)

WORKSPACE_LAYOUT = {
    "inputs_dir": "inputs",
    "downloads_dir": "downloads",
    "decrypted_dir": "decrypted",
    "transcoded_dir": "transcoded",
    "clips_dir": "clips",
    "subtitles_dir": "subtitles",
    "analysis_dir": "analysis",
    "assets_dir": "assets",
    "imports_dir": "imports",
    "exports_dir": "exports",
    "cache_dir": "cache",
    "logs_dir": "logs",
    "manifests_dir": "manifests",
}


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _workspace_payload(root: Path) -> dict:
    root = root.resolve()
    payload = {"project_root": str(_ensure_dir(root))}
    for key, folder in WORKSPACE_LAYOUT.items():
        payload[key] = str(_ensure_dir(root / folder))
    return payload


def _validate_workspace_root(root: Path) -> Path:
    resolved = root.expanduser().resolve()
    allowed_roots = [allowed.expanduser().resolve() for allowed in WORKSPACE_ALLOWED_ROOTS]
    for allowed_root in allowed_roots:
        try:
            resolved.relative_to(allowed_root)
            return resolved
        except ValueError:
            continue
    allowed_text = ", ".join(str(path) for path in allowed_roots)
    raise ValueError(f"Workspace root must be under one of: {allowed_text}")


def get_current_workspace() -> dict:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    if WORKSPACE_FILE.exists():
        try:
            data = json.loads(WORKSPACE_FILE.read_text(encoding="utf-8"))
            root = Path(data.get("project_root", str(DEFAULT_WORKSPACE_ROOT)))
            return _workspace_payload(root)
        except Exception as exc:
            logger.warning(
                "Invalid workspace config at %s; falling back to default workspace: %s",
                WORKSPACE_FILE,
                exc,
            )

    workspace = _workspace_payload(DEFAULT_WORKSPACE_ROOT)
    WORKSPACE_FILE.write_text(json.dumps(workspace, ensure_ascii=False, indent=2), encoding="utf-8")
    return workspace


def set_current_workspace(project_root: str, *, enforce_allowed_root: bool = False) -> dict:
    root = Path(project_root).expanduser()
    if enforce_allowed_root:
        root = _validate_workspace_root(root)
    workspace = _workspace_payload(root)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    WORKSPACE_FILE.write_text(json.dumps(workspace, ensure_ascii=False, indent=2), encoding="utf-8")
    return workspace


def get_workspace_dir(kind: str, workspace: dict | None = None) -> Path:
    ws = workspace or get_current_workspace()
    key = kind if kind.endswith("_dir") else f"{kind}_dir"
    if key not in ws:
        raise KeyError(f"Unknown workspace dir: {kind}")
    return Path(ws[key])


def workspace_path(kind: str, *parts: str, workspace: dict | None = None, ensure_parent: bool = True) -> Path:
    base = get_workspace_dir(kind, workspace)
    target = base.joinpath(*parts)
    if ensure_parent:
        target.parent.mkdir(parents=True, exist_ok=True)
    return target


def derive_output_path(
    kind: str,
    input_path: str,
    *,
    suffix: str = "",
    extension: str | None = None,
    workspace: dict | None = None,
) -> Path:
    input_file = Path(input_path)
    ext = extension if extension is not None else input_file.suffix
    filename = f"{input_file.stem}{suffix}{ext}"
    return workspace_path(kind, filename, workspace=workspace)


def format_workspace_text(workspace: dict | None = None) -> str:
    ws = workspace or get_current_workspace()
    return "\n".join([
        f"项目根目录: {ws['project_root']}",
        f"输入目录: {ws['inputs_dir']}",
        f"下载目录: {ws['downloads_dir']}",
        f"解密目录: {ws['decrypted_dir']}",
        f"转码目录: {ws['transcoded_dir']}",
        f"切片目录: {ws['clips_dir']}",
        f"字幕目录: {ws['subtitles_dir']}",
        f"分析目录: {ws['analysis_dir']}",
        f"素材目录: {ws['assets_dir']}",
        f"导出目录: {ws['exports_dir']}",
    ])
