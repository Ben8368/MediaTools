from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

ProgressCallback = Callable[[str, float], None]
FinishCallback = Callable[[bool, dict[str, Any]], None]


def _checkpoints_dir(project_path: str) -> Path:
    return Path(project_path).parent / "_atom_checkpoints"


def create_ae_checkpoint_impl(project_path: str, label: str = "", step_index: int = 0, notes: str = "", workspace: dict | None = None) -> dict[str, Any]:
    from . import service as ae_service

    runtime = ae_service._adapter.load_runtime()
    pythoncom = runtime["pythoncom"]
    AfterEffectsConnector = runtime["AfterEffectsConnector"]
    result_holder: dict[str, Any] = {}

    def _worker() -> None:
        pythoncom.CoInitialize()
        connector = AfterEffectsConnector()
        try:
            connector.connect()
            connector.open_project(project_path)
            checkpoint = connector.create_checkpoint(label=label, step_index=step_index, notes=notes)
            result_holder["result"] = {"ok": True, "checkpoint": checkpoint}
        except Exception as exc:
            result_holder["result"] = {"ok": False, "error": str(exc)}
        finally:
            try:
                connector.disconnect()
            except Exception:
                pass
            pythoncom.CoUninitialize()

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    thread.join(timeout=60)
    if thread.is_alive():
        return {"ok": False, "error": "Checkpoint creation timed out"}
    return result_holder.get("result", {"ok": False, "error": "Unknown error"})


def revert_ae_checkpoint_impl(checkpoint_path: str, create_branch: bool = False, workspace: dict | None = None) -> dict[str, Any]:
    from . import service as ae_service

    runtime = ae_service._adapter.load_runtime()
    pythoncom = runtime["pythoncom"]
    AfterEffectsConnector = runtime["AfterEffectsConnector"]
    result_holder: dict[str, Any] = {}

    def _worker() -> None:
        pythoncom.CoInitialize()
        connector = AfterEffectsConnector()
        try:
            connector.connect()
            result = connector.revert_to_checkpoint(checkpoint_path=checkpoint_path, create_branch=create_branch)
            result_holder["result"] = {"ok": True, "result": result}
        except Exception as exc:
            result_holder["result"] = {"ok": False, "error": str(exc)}
        finally:
            try:
                connector.disconnect()
            except Exception:
                pass
            pythoncom.CoUninitialize()

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    thread.join(timeout=60)
    if thread.is_alive():
        return {"ok": False, "error": "Checkpoint revert timed out"}
    return result_holder.get("result", {"ok": False, "error": "Unknown error"})


def list_ae_checkpoints_impl(project_path: str, workspace: dict | None = None) -> dict[str, Any]:
    try:
        checkpoints_dir = _checkpoints_dir(project_path)
        if not checkpoints_dir.exists():
            return {"ok": True, "checkpoints": []}
        checkpoints = [
            {
                "path": str(checkpoint_file),
                "name": checkpoint_file.name,
                "size": checkpoint_file.stat().st_size,
                "created_at": checkpoint_file.stat().st_mtime,
            }
            for checkpoint_file in sorted(checkpoints_dir.glob("*.aep"), key=lambda p: p.stat().st_mtime, reverse=True)
        ]
        return {"ok": True, "checkpoints": checkpoints, "count": len(checkpoints)}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "checkpoints": []}


def add_ae_to_render_queue_impl(project_path: str, comp_index: int, output_path: str, output_module_template: str = "Best Settings", workspace: dict | None = None) -> dict[str, Any]:
    from . import service as ae_service

    runtime = ae_service._adapter.load_runtime()
    pythoncom = runtime["pythoncom"]
    AfterEffectsConnector = runtime["AfterEffectsConnector"]
    result_holder: dict[str, Any] = {}

    def _worker() -> None:
        pythoncom.CoInitialize()
        connector = AfterEffectsConnector()
        try:
            connector.connect()
            connector.open_project(project_path)
            render_item = connector.add_to_render_queue(comp_index=comp_index, output_path=output_path, output_module_template=output_module_template)
            result_holder["result"] = {"ok": True, "render_item": render_item}
        except Exception as exc:
            result_holder["result"] = {"ok": False, "error": str(exc)}
        finally:
            try:
                connector.disconnect()
            except Exception:
                pass
            pythoncom.CoUninitialize()

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    thread.join(timeout=30)
    if thread.is_alive():
        return {"ok": False, "error": "Add to render queue timed out"}
    return result_holder.get("result", {"ok": False, "error": "Unknown error"})


def start_ae_render_impl(project_path: str, workspace: dict | None = None, on_progress: ProgressCallback | None = None, on_finish: FinishCallback | None = None) -> dict[str, Any]:
    from . import service as ae_service

    runtime = ae_service._adapter.load_runtime()
    pythoncom = runtime["pythoncom"]
    AfterEffectsConnector = runtime["AfterEffectsConnector"]

    def _worker() -> None:
        pythoncom.CoInitialize()
        connector = AfterEffectsConnector()
        try:
            connector.connect()
            connector.open_project(project_path)
            if on_progress:
                on_progress("Starting render...", 0.0)
            result = connector.start_render()
            if on_progress:
                on_progress("Render completed", 100.0)
            if on_finish:
                on_finish(True, {"status": "done", "result": result})
        except Exception as exc:
            if on_finish:
                on_finish(False, {"status": "error", "error": str(exc)})
        finally:
            try:
                connector.disconnect()
            except Exception:
                pass
            pythoncom.CoUninitialize()

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    return {"ok": True, "message": "Render started in background"}


def get_ae_render_queue_status_impl(project_path: str, workspace: dict | None = None) -> dict[str, Any]:
    from . import service as ae_service

    runtime = ae_service._adapter.load_runtime()
    pythoncom = runtime["pythoncom"]
    AfterEffectsConnector = runtime["AfterEffectsConnector"]
    result_holder: dict[str, Any] = {}

    def _worker() -> None:
        pythoncom.CoInitialize()
        connector = AfterEffectsConnector()
        try:
            connector.connect()
            connector.open_project(project_path)
            status = connector.get_render_queue_status()
            result_holder["result"] = {"ok": True, "status": status}
        except Exception as exc:
            result_holder["result"] = {"ok": False, "error": str(exc)}
        finally:
            try:
                connector.disconnect()
            except Exception:
                pass
            pythoncom.CoUninitialize()

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    thread.join(timeout=30)
    if thread.is_alive():
        return {"ok": False, "error": "Get render queue status timed out"}
    return result_holder.get("result", {"ok": False, "error": "Unknown error"})
