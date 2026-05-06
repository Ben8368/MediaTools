"""Workspace-aware integration facade for the vendored WeChat moments project."""

from __future__ import annotations

import base64
import json
import re
import time
from pathlib import Path
from typing import Any

from adapters import WechatMomentsRuntimeAdapter
from backend.services.workspace import get_workspace_dir

_adapter = WechatMomentsRuntimeAdapter()

DEFAULT_DRAFT = {
    "author": "A",
    "text": "很实用的教程 [微笑]\n需要收集五个赞，谢谢大家啦。",
    "location": "",
    "app": "",
    "like_count": 18,
    "comment_name": "朋友",
    "comment_text": "收藏了，晚点试一下。",
    "theme": "dark",
    "avatar_seed": "mediatools",
}


def _wechat_root(kind: str, workspace: dict | None = None) -> Path:
    target = get_workspace_dir(kind, workspace) / "wechat_moments"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _draft_path(workspace: dict | None = None) -> Path:
    return _wechat_root("manifests", workspace) / "draft.json"


def _exports_index_path(workspace: dict | None = None) -> Path:
    return _wechat_root("manifests", workspace) / "exports.json"


def get_wechat_moments_status(workspace: dict | None = None) -> dict[str, Any]:
    status = _adapter.get_status()
    manifests_dir = _wechat_root("manifests", workspace)
    status.update(
        {
            "module_id": "wechat_moments",
            "integration_mode": "frontend_module",
            "module_status": "staged",
            "assets_dir": str(_wechat_root("assets", workspace)),
            "exports_dir": str(_wechat_root("exports", workspace)),
            "manifests_dir": str(manifests_dir),
            "draft_path": str(manifests_dir / "draft.json"),
            "exports_index_path": str(manifests_dir / "exports.json"),
            "runtime_uses_external_avatar_provider": False,
            "migration_steps": [
                "Move the remaining rich layout controls from the static page into Vue.",
                "Keep module state in workspace manifests instead of browser-only localStorage.",
                "Export generated images and metadata into workspace exports.",
                "Preserve vendor source as an upstream reference while the module evolves.",
            ],
        }
    )
    return status


def _clean_draft(draft: dict[str, Any]) -> dict[str, Any]:
    return {**DEFAULT_DRAFT, **{key: value for key, value in draft.items() if key in DEFAULT_DRAFT}}


def get_wechat_moments_draft(workspace: dict | None = None) -> dict[str, Any]:
    path = _draft_path(workspace)
    if not path.exists():
        return {"ok": True, "path": str(path), "draft": dict(DEFAULT_DRAFT)}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        payload = {}
    return {"ok": True, "path": str(path), "draft": _clean_draft(payload)}


def save_wechat_moments_draft(draft: dict[str, Any], workspace: dict | None = None) -> dict[str, Any]:
    path = _draft_path(workspace)
    clean = _clean_draft(draft)
    path.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "path": str(path), "draft": clean}


def export_wechat_moments_image(
    *,
    image_data_url: str,
    draft: dict[str, Any],
    workspace: dict | None = None,
) -> dict[str, Any]:
    match = re.match(r"^data:image/png;base64,(?P<data>[A-Za-z0-9+/=\r\n]+)$", image_data_url or "")
    if not match:
        raise ValueError("Expected a PNG data URL")

    image_bytes = base64.b64decode(match.group("data"), validate=True)
    if not image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Invalid PNG payload")

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_path = _wechat_root("exports", workspace) / f"wechat_moments_{timestamp}.png"
    output_path.write_bytes(image_bytes)

    clean = _clean_draft(draft)
    manifest = {
        "ok": True,
        "kind": "wechat_moments_export",
        "created_at": time.time(),
        "output_path": str(output_path),
        "draft": clean,
    }

    index_path = _exports_index_path(workspace)
    try:
        existing = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else []
    except Exception:
        existing = []
    if not isinstance(existing, list):
        existing = []
    index_path.write_text(json.dumps([manifest, *existing[:49]], ensure_ascii=False, indent=2), encoding="utf-8")

    return {"ok": True, "output_path": str(output_path), "manifest_path": str(index_path), "draft": clean}
