"""Unified Adobe and After Effects API routes."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.api.models import AdobeExecuteBody, AdobeScanBody, AdobeTicketBody, FolderScanBody, TicketImportBody


def _iter_source_files(directory: str, suffixes: tuple[str, ...], recursive: bool, max_files: int) -> list[Path]:
    root = Path(directory).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Directory not found: {directory}")
    iterator = root.rglob("*") if recursive else root.glob("*")
    files = [path for path in iterator if path.is_file() and path.suffix.lower() in suffixes]
    files.sort(key=lambda item: str(item).lower())
    return files[: max(1, max_files)]


def create_router(job_registry, get_current_workspace, get_photoshop_status) -> APIRouter:
    router = APIRouter()

    @router.get("/api/adobe/{tool}/status")
    async def adobe_tool_status(tool: str):
        workspace = get_current_workspace()
        if tool == "photoshop":
            return JSONResponse(get_photoshop_status(workspace))
        if tool == "after_effects":
            from modules.adobe.after_effects import get_ae_status

            return JSONResponse(get_ae_status(workspace))
        return JSONResponse({"ok": False, "error": f"Unknown Adobe tool: {tool}"}, status_code=400)

    @router.post("/api/adobe/after_effects/scan")
    async def ae_scan(body: AdobeScanBody):
        from modules.adobe.after_effects import scan_ae_project

        workspace = get_current_workspace()
        job_id = job_registry.register(str(uuid.uuid4()), "ae_scan", body.file_path or "AE scan")

        def _run():
            job_registry.update(job_id, "Scanning AE project...", 25.0)
            return scan_ae_project(project_path=body.file_path, workspace=workspace)

        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(None, _run)
        except Exception as exc:
            job_registry.finish(job_id, success=False)
            return JSONResponse({"ok": False, "error": str(exc), "job_id": job_id}, status_code=400)

        job_registry.finish(job_id, success=result.get("ok", False))
        result["job_id"] = job_id
        return JSONResponse(result)

    @router.post("/api/adobe/after_effects/scan-folder")
    async def ae_scan_folder(body: FolderScanBody):
        from modules.adobe.after_effects import scan_ae_project

        workspace = get_current_workspace()
        try:
            files = _iter_source_files(body.directory, (".aep",), body.recursive, body.max_files)
        except ValueError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

        job_id = job_registry.register(str(uuid.uuid4()), "ae_scan_folder", body.directory or "AE folder scan")

        def _run():
            items: list[dict[str, Any]] = []
            total = max(1, len(files))
            for index, path in enumerate(files, start=1):
                job_registry.update(job_id, f"Scanning {path.name}", min(95.0, index / total * 90.0))
                try:
                    result = scan_ae_project(project_path=str(path), workspace=workspace)
                    items.append({"path": str(path), **result})
                except Exception as exc:
                    items.append({"ok": False, "path": str(path), "error": str(exc)})
            return items

        loop = asyncio.get_running_loop()
        items = await loop.run_in_executor(None, _run)
        success_items = [item for item in items if item.get("ok")]
        job_registry.finish(job_id, success=bool(success_items))
        payload: dict[str, Any] = {
            "ok": bool(success_items),
            "job_id": job_id,
            "items": items,
            "count": len(items),
            "created_count": len(success_items),
        }
        if success_items:
            payload["ticket_id"] = success_items[0].get("ticket_id")
            payload["ticket"] = success_items[0].get("ticket")
        elif not files:
            payload["error"] = "No After Effects projects found in selected folder."
        return JSONResponse(payload, status_code=200 if payload["ok"] or not files else 400)

    @router.get("/api/adobe/after_effects/tickets")
    async def ae_tickets():
        from modules.adobe.after_effects import list_ae_tickets

        return JSONResponse({"ok": True, "items": list_ae_tickets(get_current_workspace())})

    @router.get("/api/adobe/after_effects/tickets/{ticket_id}")
    async def ae_ticket(ticket_id: str):
        from modules.adobe.after_effects import get_ae_ticket

        try:
            result = get_ae_ticket(ticket_id, get_current_workspace())
            return JSONResponse({"ok": True, **result})
        except FileNotFoundError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=404)
        except ValueError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    @router.post("/api/adobe/after_effects/tickets/import")
    async def ae_ticket_import(body: TicketImportBody):
        from modules.adobe.after_effects import import_ae_ticket

        try:
            result = import_ae_ticket(body.file_path, get_current_workspace(), body.ticket_id)
            return JSONResponse({"ok": True, **result})
        except FileNotFoundError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=404)
        except ValueError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    @router.put("/api/adobe/after_effects/tickets/{ticket_id}")
    async def ae_ticket_update(ticket_id: str, body: AdobeTicketBody):
        from modules.adobe.after_effects import save_ae_ticket

        try:
            result = save_ae_ticket(ticket_id, body.ticket, get_current_workspace())
            return JSONResponse({"ok": True, **result})
        except Exception as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    @router.delete("/api/adobe/after_effects/tickets/{ticket_id}")
    async def ae_ticket_delete(ticket_id: str):
        from modules.adobe.after_effects import delete_ae_ticket

        try:
            result = delete_ae_ticket(ticket_id, get_current_workspace())
            return JSONResponse({"ok": True, **result})
        except FileNotFoundError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=404)
        except ValueError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    @router.post("/api/adobe/after_effects/tickets/{ticket_id}/execute")
    async def ae_execute(ticket_id: str, body: AdobeExecuteBody):
        from modules.adobe.after_effects import start_ae_ticket_execution

        workspace = get_current_workspace()
        job_id = str(uuid.uuid4())
        job_registry.register(job_id, "after_effects", f"AE / {ticket_id[:8]}")

        def _on_progress(stage: str, percent: float) -> None:
            job_registry.update(job_id, stage, percent)

        def _on_finish(success: bool, payload: dict[str, Any]) -> None:
            if payload.get("status") == "cancelled":
                job_registry.update(job_id, "Execution cancelled", 100.0, "error")
                return
            job_registry.finish(job_id, success=success)

        try:
            result = start_ae_ticket_execution(
                ticket_id,
                dry_run=body.dry_run,
                selected_task_indexes=body.selected_task_indexes,
                workspace=workspace,
                job_id=job_id,
                on_progress=_on_progress,
                on_finish=_on_finish,
            )
            return JSONResponse(result)
        except Exception as exc:
            job_registry.finish(job_id, success=False)
            return JSONResponse({"ok": False, "error": str(exc), "job_id": job_id}, status_code=400)

    @router.get("/api/adobe/after_effects/executions/{ticket_id}")
    async def ae_execution(ticket_id: str):
        from modules.adobe.common.execution import get_execution_state

        state = get_execution_state(ticket_id)
        if not state:
            return JSONResponse({"ok": False, "error": f"Execution not found for ticket {ticket_id}"}, status_code=404)
        return JSONResponse({"ok": True, "state": state})

    @router.post("/api/adobe/after_effects/executions/{ticket_id}/cancel")
    async def ae_cancel(ticket_id: str):
        from modules.adobe.common.execution import cancel_execution

        try:
            state = cancel_execution(ticket_id)
            return JSONResponse({"ok": True, "state": state})
        except FileNotFoundError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=404)
        except RuntimeError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    @router.get("/api/adobe/after_effects/fonts")
    async def ae_fonts(query: str = "", limit: int = 200):
        from modules.adobe.after_effects import list_ae_fonts

        result = list_ae_fonts(query=query, limit=limit, workspace=get_current_workspace())
        return JSONResponse(result)

    @router.post("/api/adobe/after_effects/checkpoints/create")
    async def ae_checkpoint_create(body: AdobeScanBody):
        from modules.adobe.after_effects import create_ae_checkpoint

        result = create_ae_checkpoint(
            project_path=body.file_path,
            label=body.label or "",
            step_index=body.step_index or 0,
            notes=body.notes or "",
            workspace=get_current_workspace(),
        )
        return JSONResponse(result)

    @router.post("/api/adobe/after_effects/checkpoints/revert")
    async def ae_checkpoint_revert(body: AdobeScanBody):
        from modules.adobe.after_effects import revert_ae_checkpoint

        result = revert_ae_checkpoint(
            checkpoint_path=body.file_path,
            create_branch=body.create_branch or False,
            workspace=get_current_workspace(),
        )
        return JSONResponse(result)

    @router.get("/api/adobe/after_effects/checkpoints")
    async def ae_checkpoints_list(project_path: str):
        from modules.adobe.after_effects import list_ae_checkpoints

        result = list_ae_checkpoints(project_path=project_path, workspace=get_current_workspace())
        return JSONResponse(result)

    @router.post("/api/adobe/after_effects/render/add")
    async def ae_render_add(body: AdobeScanBody):
        from modules.adobe.after_effects import add_ae_to_render_queue

        result = add_ae_to_render_queue(
            project_path=body.file_path,
            comp_index=body.comp_index or 1,
            output_path=body.output_path or "",
            output_module_template=body.output_module_template or "Best Settings",
            workspace=get_current_workspace(),
        )
        return JSONResponse(result)

    @router.post("/api/adobe/after_effects/render/start")
    async def ae_render_start(body: AdobeScanBody):
        from modules.adobe.after_effects import start_ae_render

        result = start_ae_render(project_path=body.file_path, workspace=get_current_workspace())
        return JSONResponse(result)

    @router.get("/api/adobe/after_effects/render/status")
    async def ae_render_status(project_path: str):
        from modules.adobe.after_effects import get_ae_render_queue_status

        result = get_ae_render_queue_status(project_path=project_path, workspace=get_current_workspace())
        return JSONResponse(result)

    return router
