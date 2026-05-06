"""Adapter for the vendored WeChat moments generator source bundle."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from config import BASE_DIR

WECHAT_MOMENTS_ROOT = BASE_DIR / "vendor" / "wechat_moments_source"


class WechatMomentsRuntimeAdapter:
    """Reports the state of the vendored WeChat source bundle without embedding it."""

    def __init__(self) -> None:
        self.root = WECHAT_MOMENTS_ROOT
        self.entry_html = self.root / "index.html"
        self.main_js = self.root / "js" / "main.js"
        self.avatar_js = self.root / "js" / "avatar-generator.js"

    def _read_text(self, path: Path) -> str:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")

    def get_status(self) -> dict[str, Any]:
        main_text = self._read_text(self.main_js)
        avatar_text = self._read_text(self.avatar_js)

        source_exists = self.root.exists() and self.entry_html.exists() and self.main_js.exists()
        uses_global_window = "window." in main_text
        uses_local_storage = "localStorage" in main_text
        uses_external_avatar_provider = "picsum.photos" in avatar_text

        return {
            "available": source_exists,
            "source_exists": source_exists,
            "root": str(self.root),
            "entry_html": str(self.entry_html),
            "main_js": str(self.main_js),
            "avatar_js": str(self.avatar_js),
            "ui_mode": "static_dom_page",
            "uses_global_window": uses_global_window,
            "uses_local_storage": uses_local_storage,
            "uses_external_avatar_provider": uses_external_avatar_provider,
            "recommended_module_id": "wechat_moments",
            "vendor_slug": "wechat_moments_source",
        }
