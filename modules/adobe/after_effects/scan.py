from __future__ import annotations

import threading
import uuid
from typing import Any


def scan_ae_project_impl(*, project_path: str = "", workspace: dict | None = None) -> dict[str, Any]:
    from . import service as ae_service

    if not project_path:
        return {"ok": False, "error": "project_path is required"}

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
            layers = connector.scan_project_for_text_layers(project_path)

            ticket_id = str(uuid.uuid4())
            tasks = [
                {
                    "layer_id": f"{layer['comp_index']}:{layer['layer_index']}",
                    "comp_name": layer.get("comp_name", ""),
                    "comp_index": layer.get("comp_index"),
                    "layer_name": layer.get("layer_name", ""),
                    "layer_index": layer.get("layer_index"),
                    "layer_type": "text",
                    "original_text": layer.get("original_text", ""),
                    "source_font": layer.get("source_font", ""),
                    "font_size": layer.get("font_size", 0),
                    "tracking": layer.get("tracking", 0),
                    "target_text": "",
                    "target_font": "",
                    "output_name": "output.aep",
                    "status": "pending",
                }
                for layer in layers
            ]

            ticket_payload = ae_service._build_ticket_from_layers(tasks, project_path)
            ticket_file = ae_service._ticket_path(ticket_id, workspace)
            ae_service._save_ticket_payload(ticket_file, ticket_payload)

            comp_names = sorted({task["comp_name"] for task in tasks if task.get("comp_name")})
            result_holder["result"] = {
                "ok": True,
                "ticket_id": ticket_id,
                "ticket_path": str(ticket_file),
                "ticket": ticket_payload,
                "source_project": project_path,
                "layer_count": len(tasks),
                "comp_count": len(comp_names),
                "comps": comp_names,
                "message": f"Scanned {len(tasks)} text layers across {len(comp_names)} compositions",
            }
        except Exception as exc:
            result_holder["result"] = {"ok": False, "error": str(exc)}
        finally:
            try:
                connector.close_project()
            except Exception:
                pass
            try:
                connector.disconnect()
            except Exception:
                pass
            pythoncom.CoUninitialize()

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    thread.join(timeout=120)
    if thread.is_alive():
        return {"ok": False, "error": "AE scan timed out after 120 seconds"}
    return result_holder.get("result", {"ok": False, "error": "Unknown error during scan"})


def list_ae_fonts_impl(query: str = "", limit: int = 200, workspace: dict | None = None) -> dict[str, Any]:
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
            fonts = connector.get_available_fonts(query=query, limit=limit)
            result_holder["result"] = {
                "ok": True,
                "fonts": fonts,
                "count": len(fonts),
                "query": query,
                "limit": limit,
            }
        except Exception as exc:
            result_holder["result"] = {"ok": False, "error": str(exc), "fonts": []}
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
        return {"ok": False, "error": "Font enumeration timed out", "fonts": []}
    return result_holder.get("result", {"ok": False, "error": "Unknown error", "fonts": []})
