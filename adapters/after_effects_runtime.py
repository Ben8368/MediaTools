"""Adapter for the After Effects COM runtime."""

from __future__ import annotations

import importlib
import importlib.util
import subprocess
import sys
from typing import Any

from backend.config import BASE_DIR

AE_SRC = BASE_DIR / "vendor" / "adobe" / "after-effects" / "com" / "src"
RUNTIME_MODULES = ["ae_connector.py"]
AE_PROCESS_NAMES = ("AfterFX.exe",)


def _is_windows_process_running(process_names: tuple[str, ...]) -> bool:
    if not sys.platform.startswith("win"):
        return False
    for process_name in process_names:
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {process_name}", "/NH"],
                check=False,
                capture_output=True,
                text=True,
                timeout=2,
            )
        except Exception:
            continue
        if process_name.lower() in result.stdout.lower():
            return True
    return False


class AfterEffectsAutomationAdapter:
    """Loads AfterEffects COM runtime lazily and reports dependency status."""

    def __init__(self) -> None:
        self.src_dir = AE_SRC

    def ensure_runtime_path(self) -> None:
        src_path = str(self.src_dir)
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    def is_supported_platform(self) -> bool:
        return sys.platform.startswith("win")

    def can_import_pywin32(self) -> bool:
        return (
            importlib.util.find_spec("win32com") is not None
            and importlib.util.find_spec("pythoncom") is not None
        )

    def get_status(self) -> dict[str, Any]:
        source_exists = self.src_dir.exists() and all(
            (self.src_dir / m).exists() for m in RUNTIME_MODULES
        )
        app_running = _is_windows_process_running(AE_PROCESS_NAMES)
        reason = ""
        if not source_exists:
            reason = "missing_source"
        elif not self.is_supported_platform():
            reason = "windows_only"
        elif not self.can_import_pywin32():
            reason = "missing_pywin32"
        available = source_exists and self.is_supported_platform() and self.can_import_pywin32()
        return {
            "available": available,
            "platform": "com",
            "source_exists": source_exists,
            "windows_only": self.is_supported_platform(),
            "pywin32": self.can_import_pywin32(),
            "app_running": app_running,
            "app_process": AE_PROCESS_NAMES[0],
            "src_dir": str(self.src_dir),
            "reason": reason,
        }

    def load_runtime(self) -> dict[str, Any]:
        status = self.get_status()
        if not status["source_exists"]:
            raise RuntimeError("AfterEffects connector source is missing")
        if not status["windows_only"]:
            raise RuntimeError("After Effects automation is only supported on Windows")
        if not status["pywin32"]:
            raise RuntimeError("pywin32 is not installed")

        self.ensure_runtime_path()
        return {
            "AfterEffectsConnector": importlib.import_module("ae_connector").AfterEffectsConnector,
            "pythoncom": importlib.import_module("pythoncom"),
        }
