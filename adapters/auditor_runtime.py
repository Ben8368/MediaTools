"""Adapter for the vendored Auditor source bundle."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from config import BASE_DIR

AUDITOR_ROOT = BASE_DIR / "vendor" / "auditor" / "src"


class AuditorRuntimeAdapter:
    """Reports the state of the vendored Auditor project without importing it."""

    def __init__(self) -> None:
        self.root = AUDITOR_ROOT
        self.entrypoint = self.root / "main.py"
        self.settings_file = self.root / "settings.py"
        self.snapshot_file = self.root / "monitor" / "folder_monitor.py"

    def _read_text(self, path: Path) -> str:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")

    def get_status(self) -> dict[str, Any]:
        settings_text = self._read_text(self.settings_file)
        monitor_text = self._read_text(self.snapshot_file)

        source_exists = self.root.exists() and self.entrypoint.exists() and self.settings_file.exists()
        uses_env_singleton = "load_dotenv()" in settings_text
        uses_relative_workbook = "tao_config.xlsx" in settings_text
        uses_relative_snapshot = "data/snapshot.json" in monitor_text or 'self.snapshot_file = "data/snapshot.json"' in monitor_text

        return {
            "available": source_exists,
            "source_exists": source_exists,
            "root": str(self.root),
            "entrypoint": str(self.entrypoint),
            "settings_file": str(self.settings_file),
            "watch_mode": "polling_forever",
            "uses_env_singleton": uses_env_singleton,
            "uses_relative_workbook": uses_relative_workbook,
            "uses_relative_snapshot": uses_relative_snapshot,
            "recommended_module_id": "auditor",
            "vendor_slug": "auditor",
        }
