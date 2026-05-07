"""Photoshop API routes."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.api.models import (
    FolderScanBody,
    PhotoshopExecuteBody,
    PhotoshopScanBody,
    PhotoshopTicketBody,
    TicketImportBody,
)


def _iter_source_files(directory: str, suffixes: tuple[str, ...], recursive: bool, max_files: int) -> list[Path]:
    root = Path(directory).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Directory not found: {directory}")
    iterator = root.rglob("*") if recursive else root.glob("*")
    files = [path for path in iterator if path.is_file() and path.suffix.lower() in suffixes]
    files.sort(key=lambda item: str(item).lower())
    return files[: max(1, max_files)]


def create_router(
    job_registry,
    get_current_workspace,
    get_photoshop_status,
    scan_photoshop_document,
    list_photoshop_tickets,
    get_photoshop_ticket,
    save_photoshop_ticket,
    start_ticket_execution,
    get_photoshop_execution_state,
    cancel_photoshop_execution,
) -> APIRouter:
    router = APIRouter()

    @router.get("/api/photoshop/status")
    async def photoshop_status():
        return JSONResponse(get_photoshop_status(get_current_workspace()))

    @router.post("/api/photoshop/scan")
    async def photoshop_scan(body: PhotoshopScanBody):
        workspace = get_current_workspace()
        job_id = job_registry.register(str(uuid.uuid4()), "photoshop_scan", body.psd_path or "Photoshop scan")

        def _on_scan_progress(progress: dict[str, Any]) -> None:
            layer_count = int(progress.get("layer_count", 0) or 0)
            smart_object_count = int(progress.get("smart_object_count", 0) or 0)
            percent = min(92.0, 18.0 + layer_count * 1.5 + smart_object_count * 0.5)
            job_registry.update(
                job_id,
                str(progress.get("stage") or "Scanning Photoshop document..."),
                percent,
                extra={
                    "scan_layer_count": layer_count,
                    "scan_normal_text_layer_count": int(progress.get("normal_text_layer_count", 0) or 0),
                    "scan_smart_text_layer_count": int(progress.get("smart_text_layer_count", 0) or 0),
                    "scan_smart_object_count": smart_object_count,
                    "scan_skipped_smart_object_count": int(progress.get("skipped_smart_object_count", 0) or 0),
                    "scan_smart_object_name": str(progress.get("smart_object_name", "") or ""),
                },
            )

        def _run():
            job_registry.update(job_id, "Scanning Photoshop document...", 25.0)
            return scan_photoshop_document(
                psd_path=body.psd_path,
                languages=body.languages,
                timeout_sec=body.timeout_sec,
                workspace=workspace,
                progress_callback=_on_scan_progress,
            )

        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(None, _run)
        except Exception as exc:
            job_registry.finish(job_id, success=False)
            return JSONResponse({"ok": False, "error": str(exc), "job_id": job_id}, status_code=400)

        job_registry.finish(job_id, success=result.get("ok", False))
        result["job_id"] = job_id
        return JSONResponse(result)

    @router.post("/api/photoshop/scan-folder")
    async def photoshop_scan_folder(body: FolderScanBody):
        workspace = get_current_workspace()
        try:
            files = _iter_source_files(body.directory, (".psd", ".psb"), body.recursive, body.max_files)
        except ValueError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

        job_id = job_registry.register(
            str(uuid.uuid4()), "photoshop_scan_folder", body.directory or "Photoshop folder scan"
        )

        def _run():
            items: list[dict[str, Any]] = []
            total = max(1, len(files))
            for index, path in enumerate(files, start=1):
                job_registry.update(job_id, f"Scanning {path.name}", min(95.0, index / total * 90.0))
                try:

                    def _on_scan_progress(
                        progress: dict[str, Any],
                        current_path: Path = path,
                        current_index: int = index,
                    ) -> None:
                        layer_count = int(progress.get("layer_count", 0) or 0)
                        smart_object_count = int(progress.get("smart_object_count", 0) or 0)
                        base_percent = (current_index - 1) / total * 90.0
                        file_percent = min(88.0 / total, (layer_count * 1.5 + smart_object_count * 0.5) / total)
                        job_registry.update(
                            job_id,
                            f"{current_path.name}: {progress.get('stage') or 'Scanning Photoshop document...'}",
                            min(95.0, base_percent + 5.0 + file_percent),
                            extra={
                                "scan_layer_count": layer_count,
                                "scan_normal_text_layer_count": int(progress.get("normal_text_layer_count", 0) or 0),
                                "scan_smart_text_layer_count": int(progress.get("smart_text_layer_count", 0) or 0),
                                "scan_smart_object_count": smart_object_count,
                                "scan_skipped_smart_object_count": int(
                                    progress.get("skipped_smart_object_count", 0) or 0
                                ),
                                "scan_smart_object_name": str(progress.get("smart_object_name", "") or ""),
                                "scan_current_file": current_path.name,
                                "scan_file_index": current_index,
                                "scan_file_total": total,
                            },
                        )

                    result = scan_photoshop_document(
                        psd_path=str(path),
                        languages=body.languages,
                        timeout_sec=body.timeout_sec,
                        workspace=workspace,
                        progress_callback=_on_scan_progress,
                    )
                    items.append({"path": str(path), **result})
                except Exception as exc:  # keep folder batches useful even when one PSD fails
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
            payload["error"] = "No Photoshop files found in selected folder."
        return JSONResponse(payload, status_code=200 if payload["ok"] or not files else 400)

    @router.get("/api/photoshop/tickets")
    async def photoshop_tickets():
        return JSONResponse({"ok": True, "items": list_photoshop_tickets(get_current_workspace())})

    @router.get("/api/photoshop/tickets/{ticket_id}")
    async def photoshop_ticket(ticket_id: str):
        try:
            result = get_photoshop_ticket(ticket_id, get_current_workspace())
            return JSONResponse({"ok": True, **result})
        except FileNotFoundError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=404)
        except ValueError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    @router.post("/api/photoshop/tickets/import")
    async def photoshop_ticket_import(body: TicketImportBody):
        from modules.adobe.photoshop import import_photoshop_ticket

        try:
            result = import_photoshop_ticket(body.file_path, get_current_workspace(), body.ticket_id)
            return JSONResponse({"ok": True, **result})
        except FileNotFoundError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=404)
        except ValueError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    @router.put("/api/photoshop/tickets/{ticket_id}")
    async def photoshop_ticket_update(ticket_id: str, body: PhotoshopTicketBody):
        try:
            result = save_photoshop_ticket(ticket_id, body.ticket, get_current_workspace())
            return JSONResponse({"ok": True, **result})
        except Exception as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    @router.delete("/api/photoshop/tickets/{ticket_id}")
    async def photoshop_ticket_delete(ticket_id: str):
        from modules.adobe.photoshop import delete_photoshop_ticket

        try:
            result = delete_photoshop_ticket(ticket_id, get_current_workspace())
            return JSONResponse({"ok": True, **result})
        except FileNotFoundError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=404)
        except ValueError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    @router.post("/api/photoshop/tickets/{ticket_id}/execute")
    async def photoshop_execute(ticket_id: str, body: PhotoshopExecuteBody):
        workspace = get_current_workspace()
        job_id = str(uuid.uuid4())
        job_registry.register(job_id, "photoshop", f"Photoshop / {ticket_id[:8]}")

        def _on_progress(stage: str, percent: float) -> None:
            job_registry.update(job_id, stage, percent)

        def _on_finish(success: bool, payload: dict[str, Any]) -> None:
            if payload.get("status") == "cancelled":
                job_registry.update(job_id, "Execution cancelled", 100.0, "error")
                return
            job_registry.finish(job_id, success=success)

        try:
            result = start_ticket_execution(
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

    @router.get("/api/photoshop/executions/{ticket_id}")
    async def photoshop_execution(ticket_id: str):
        state = get_photoshop_execution_state(ticket_id)
        if not state:
            return JSONResponse({"ok": False, "error": f"Execution not found for ticket {ticket_id}"}, status_code=404)
        return JSONResponse({"ok": True, "state": state})

    @router.post("/api/photoshop/executions/{ticket_id}/cancel")
    async def photoshop_cancel(ticket_id: str):
        try:
            state = cancel_photoshop_execution(ticket_id)
            return JSONResponse({"ok": True, "state": state})
        except FileNotFoundError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=404)

    return router
