"""Workspace-aware integration facade for the vendored Auditor project."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from adapters import AuditorRuntimeAdapter
from services.workspace import get_workspace_dir

_adapter = AuditorRuntimeAdapter()

DEFAULT_CONFIG = {
    "output_backend": "local",
    "watch_folders": [],
    "local_workbook_name": "auditor.xlsx",
    "model": "",
    "enabled": False,
}


def _auditor_root(kind: str, workspace: dict | None = None) -> Path:
    target = get_workspace_dir(kind, workspace) / "auditor"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _config_path(workspace: dict | None = None) -> Path:
    return _auditor_root("manifests", workspace) / "config.json"


def _run_manifest_path(workspace: dict | None = None) -> Path:
    return _auditor_root("manifests", workspace) / "last_scan.json"


def _clean_config(config: dict[str, Any]) -> dict[str, Any]:
    clean = {**DEFAULT_CONFIG, **{key: value for key, value in config.items() if key in DEFAULT_CONFIG}}
    if not isinstance(clean["watch_folders"], list):
        clean["watch_folders"] = []
    clean["watch_folders"] = [str(item).strip() for item in clean["watch_folders"] if str(item).strip()]
    return clean


def get_auditor_status(workspace: dict | None = None) -> dict[str, Any]:
    status = _adapter.get_status()
    manifests_dir = _auditor_root("manifests", workspace)
    status.update(
        {
            "module_id": "auditor",
            "integration_mode": "service_module",
            "module_status": "staged",
            "analysis_dir": str(_auditor_root("analysis", workspace)),
            "logs_dir": str(_auditor_root("logs", workspace)),
            "manifests_dir": str(manifests_dir),
            "config_path": str(manifests_dir / "config.json"),
            "last_scan_path": str(manifests_dir / "last_scan.json"),
            "workbook_path": str(_auditor_root("exports", workspace) / DEFAULT_CONFIG["local_workbook_name"]),
            "runtime_uses_env_singleton": False,
            "runtime_uses_relative_paths": False,
            "migration_steps": [
                "Map Auditor rules into a workspace config object.",
                "Wrap the long-running monitor loop as a MediaTools job service.",
                "Expose workbook backends as adapters rather than process-wide globals.",
                "Write snapshots, logs, and audit outputs only through workspace paths.",
            ],
        }
    )
    return status


def get_auditor_config(workspace: dict | None = None) -> dict[str, Any]:
    path = _config_path(workspace)
    if not path.exists():
        return {"ok": True, "path": str(path), "config": dict(DEFAULT_CONFIG)}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        payload = {}
    return {"ok": True, "path": str(path), "config": _clean_config(payload)}


def save_auditor_config(config: dict[str, Any], workspace: dict | None = None) -> dict[str, Any]:
    path = _config_path(workspace)
    clean = _clean_config(config)
    path.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "path": str(path), "config": clean}


def run_auditor_scan_once(workspace: dict | None = None) -> dict[str, Any]:
    config_payload = get_auditor_config(workspace)
    config = config_payload["config"]
    watch_folders = [Path(item).expanduser() for item in config.get("watch_folders", [])]

    scanned_files: list[dict[str, Any]] = []
    missing_folders: list[str] = []
    skipped_count = 0
    max_files = 5000

    for folder in watch_folders:
        if not folder.exists() or not folder.is_dir():
            missing_folders.append(str(folder))
            continue
        for path in folder.rglob("*"):
            if not path.is_file():
                continue
            if len(scanned_files) >= max_files:
                skipped_count += 1
                continue
            try:
                stat = path.stat()
                scanned_files.append(
                    {
                        "path": str(path),
                        "size": stat.st_size,
                        "mtime": stat.st_mtime,
                        "suffix": path.suffix.lower(),
                    }
                )
            except OSError:
                skipped_count += 1

    summary = {
        "configured": bool(watch_folders),
        "folder_count": len(watch_folders),
        "missing_folder_count": len(missing_folders),
        "file_count": len(scanned_files),
        "skipped_count": skipped_count,
        "output_backend": config.get("output_backend", "local"),
        "enabled": bool(config.get("enabled")),
    }
    payload = {
        "ok": True,
        "kind": "auditor_scan_once",
        "created_at": time.time(),
        "config_path": config_payload["path"],
        "summary": summary,
        "missing_folders": missing_folders,
        "files": scanned_files,
    }

    manifest_path = _run_manifest_path(workspace)
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "manifest_path": str(manifest_path), **payload}
