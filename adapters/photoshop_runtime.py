"""Adapter for the bundled Photoshop runtime."""

from __future__ import annotations

import importlib
import importlib.util
import subprocess
import sys
from typing import Any

from backend.config import BASE_DIR

PHOTOSHOP_AUTO_ROOT = BASE_DIR / "vendor" / "adobe" / "photoshop" / "com"
PHOTOSHOP_AUTO_SRC = PHOTOSHOP_AUTO_ROOT / "src"
RUNTIME_MODULES = [
    "ps_connector.py",
    "ticket_workflow.py",
    "text_modifier.py",
    "config_reader.py",
    "ticket_json.py",
    # 核心模块
    "text_models.py",
    "text_utils.py",
    "text_logger.py",
    "font_resolver.py",
    "document_scanner.py",
    "adaptive_lab.py",
    "adaptive_algorithm.py",
    "workorder_applier.py",
    "smart_object_handler.py",
]
PHOTOSHOP_PROCESS_NAMES = ("Photoshop.exe",)


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


class PhotoshopAutomationAdapter:
    """Loads PhotoshopAuto runtime lazily and reports dependency status."""

    def __init__(self) -> None:
        self.root = PHOTOSHOP_AUTO_ROOT
        self.src_dir = PHOTOSHOP_AUTO_SRC

    def ensure_runtime_path(self) -> None:
        src_path = str(self.src_dir)
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

    def is_supported_platform(self) -> bool:
        return sys.platform.startswith("win")

    def can_import_pywin32(self) -> bool:
        return importlib.util.find_spec("win32com") is not None and importlib.util.find_spec("pythoncom") is not None

    def get_status(self) -> dict[str, Any]:
        source_exists = self.root.exists() and self.src_dir.exists()
        runtime_modules = source_exists and all((self.src_dir / name).exists() for name in RUNTIME_MODULES)
        runtime_ready = self.is_supported_platform() and source_exists and self.can_import_pywin32()
        app_running = _is_windows_process_running(PHOTOSHOP_PROCESS_NAMES)
        reason = ""
        if not source_exists:
            reason = "missing_source"
        elif not runtime_modules:
            reason = "missing_runtime_modules"
        elif not self.is_supported_platform():
            reason = "windows_only"
        elif not self.can_import_pywin32():
            reason = "missing_pywin32"
        runtime_ready = runtime_ready and runtime_modules
        return {
            "available": runtime_ready,
            "source_exists": source_exists,
            "runtime_modules": runtime_modules,
            "windows_only": self.is_supported_platform(),
            "pywin32": self.can_import_pywin32(),
            "app_running": app_running,
            "app_process": PHOTOSHOP_PROCESS_NAMES[0],
            "root": str(self.root),
            "src_dir": str(self.src_dir),
            "reason": reason,
        }

    def load_runtime(self) -> dict[str, Any]:
        status = self.get_status()
        if not status["source_exists"]:
            raise RuntimeError("PhotoshopAuto source is missing from the repository")
        if not status["runtime_modules"]:
            raise RuntimeError("PhotoshopAuto runtime modules are missing from the repository")
        if not status["windows_only"]:
            raise RuntimeError("Photoshop automation is only supported on Windows")
        if not status["pywin32"]:
            raise RuntimeError("pywin32 is not installed")

        self.ensure_runtime_path()
        return {
            "PhotoshopConnector": importlib.import_module("ps_connector").PhotoshopConnector,
            "scan_document_for_ticket": importlib.import_module("ticket_workflow").scan_document_for_ticket,
            "modify_smart_object_text_layer": importlib.import_module("ticket_workflow").modify_smart_object_text_layer,
            "AdjustParams": importlib.import_module("text_modifier").AdjustParams,
            "modify_text_layer": importlib.import_module("text_modifier").modify_text_layer,
            "TextMapping": importlib.import_module("config_reader").TextMapping,
            "Ticket": importlib.import_module("ticket_json").Ticket,
            "TicketTask": importlib.import_module("ticket_json").TicketTask,
            "TicketMeta": importlib.import_module("ticket_json").TicketMeta,
            "load_ticket_json": importlib.import_module("ticket_json").load_ticket_json,
            "save_ticket_json": importlib.import_module("ticket_json").save_ticket_json,
            "pythoncom": importlib.import_module("pythoncom"),
        }
