"""Photoshop 自动化服务核心逻辑"""

from __future__ import annotations

import json
import queue
import threading
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from adapters.photoshop_runtime import PhotoshopAutomationAdapter
from modules.adobe.common.execution import (
    _executions,
    cancel_execution,
    get_execution_state,
)

ProgressCallback = Callable[[str, float], None]
FinishCallback = Callable[[bool, dict[str, Any]], None]

_adapter = PhotoshopAutomationAdapter()
_execution_lock = threading.Lock()


def _require_workspace_dir(kind: str, workspace: dict | None = None) -> Path:
    ws = workspace or {}
    key = kind if kind.endswith("_dir") else f"{kind}_dir"
    value = ws.get(key)
    if not value:
        raise ValueError(f"Workspace must provide '{key}'")
    return Path(value)


def get_workspace_dir(kind: str, workspace: dict | None = None) -> Path:
    return _require_workspace_dir(kind, workspace)


def _photoshop_root(kind: str, workspace: dict | None = None) -> Path:
    base = _require_workspace_dir(kind, workspace)
    root = base / "photoshop"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _tickets_dir(workspace: dict | None = None) -> Path:
    target = _photoshop_root("manifests", workspace) / "tickets"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _exports_dir(workspace: dict | None = None) -> Path:
    target = _photoshop_root("exports", workspace) / "renders"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _ticket_path(ticket_id: str, workspace: dict | None = None) -> Path:
    return _tickets_dir(workspace) / f"{ticket_id}.json"


def _runtime() -> dict[str, Any]:
    return _adapter.load_runtime()


def _load_ticket_payload(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Ticket JSON is invalid: {path.name}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Ticket JSON must contain an object: {path.name}")
    payload.setdefault("meta", {})
    payload.setdefault("tasks", [])
    if not isinstance(payload["meta"], dict) or not isinstance(payload["tasks"], list):
        raise ValueError(f"Ticket JSON has invalid shape: {path.name}")
    return payload


def _save_ticket_payload(path: Path, payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("Ticket payload must be an object")
    if not isinstance(payload.get("meta", {}), dict):
        raise ValueError("Ticket meta must be an object")
    if not isinstance(payload.get("tasks", []), list):
        raise ValueError("Ticket tasks must be a list")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _ticket_summary(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    meta = payload.get("meta", {})
    tasks = [task for task in payload.get("tasks", []) if isinstance(task, dict)]
    return {
        "ticket_id": path.stem,
        "path": str(path),
        "source_psd": meta.get("source_psd", ""),
        "created_at": meta.get("created_at", ""),
        "task_count": len(tasks),
        "confirmed_count": sum(1 for task in tasks if task.get("status") == "confirmed"),
        "updated_at": path.stat().st_mtime,
    }


def get_photoshop_status(workspace: dict | None = None) -> dict[str, Any]:
    status = _adapter.get_status()
    status.update(
        {
            "tickets_dir": str(_tickets_dir(workspace)),
            "exports_dir": str(_exports_dir(workspace)),
            "running_executions": len([item for item in _executions.values() if item.status == "running"]),
        }
    )
    return status


def list_photoshop_tickets(workspace: dict | None = None) -> list[dict[str, Any]]:
    tickets: list[dict[str, Any]] = []
    for path in sorted(_tickets_dir(workspace).glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            tickets.append(_ticket_summary(path, _load_ticket_payload(path)))
        except Exception:
            continue
    return tickets


def get_photoshop_ticket(ticket_id: str, workspace: dict | None = None) -> dict[str, Any]:
    path = _ticket_path(ticket_id, workspace)
    if not path.exists():
        raise FileNotFoundError(f"Ticket not found: {ticket_id}")
    return {"ticket_id": ticket_id, "path": str(path), "ticket": _load_ticket_payload(path)}


def save_photoshop_ticket(ticket_id: str, ticket_payload: dict[str, Any], workspace: dict | None = None) -> dict[str, Any]:
    path = _ticket_path(ticket_id, workspace)
    _save_ticket_payload(path, ticket_payload)
    return {"ticket_id": ticket_id, "path": str(path), "ticket": _load_ticket_payload(path)}


def delete_photoshop_ticket(ticket_id: str, workspace: dict | None = None) -> dict[str, Any]:
    path = _ticket_path(ticket_id, workspace)
    if not path.exists():
        raise FileNotFoundError(f"Ticket not found: {ticket_id}")
    path.unlink()
    return {"ticket_id": ticket_id, "path": str(path), "deleted": True}


def _build_ticket(runtime: dict[str, Any], scan_rows: list[Any], source_psd: str, languages: list[str]) -> Any:
    ticket_tasks = []
    expanded_languages = [item for item in languages if item] if languages else []

    for row in scan_rows:
        if expanded_languages:
            for language in expanded_languages:
                ticket_tasks.append(
                    runtime["TicketTask"](
                        layer_id=row.layer_id,
                        artboard_name=row.artboard,
                        layer_name=row.layer_name,
                        output_name=f"{language}.psd",
                        language=language,
                        line_count=row.line_count,
                        alignment=row.alignment,
                        font_size=row.font_size,
                        tracking=row.tracking,
                        width_px=row.width_px,
                        height_px=row.height_px,
                        source_psd=source_psd,
                        source_font=row.source_font,
                        original_text=row.original_text,
                        target_text="",
                        target_font="",
                        status="pending",
                    )
                )
        else:
            ticket_tasks.append(
                runtime["TicketTask"](
                    layer_id=row.layer_id,
                    artboard_name=row.artboard,
                    layer_name=row.layer_name,
                    output_name="",
                    language="",
                    line_count=row.line_count,
                    alignment=row.alignment,
                    font_size=row.font_size,
                    tracking=row.tracking,
                    width_px=row.width_px,
                    height_px=row.height_px,
                    source_psd=source_psd,
                    source_font=row.source_font,
                    original_text=row.original_text,
                    target_text="",
                    target_font="",
                    status="pending",
                )
            )

    meta = runtime["TicketMeta"](created_by="mediatools_scan", source_psd=source_psd)
    return runtime["Ticket"](meta=meta, tasks=ticket_tasks)


def scan_photoshop_document(
    *,
    psd_path: str = "",
    languages: list[str] | None = None,
    timeout_sec: int = 180,
    workspace: dict | None = None,
) -> dict[str, Any]:
    runtime = _runtime()
    result_queue: queue.Queue[tuple[str, Any]] = queue.Queue()

    def _worker() -> None:
        pythoncom = runtime["pythoncom"]
        connector = None
        opened_doc = False
        doc = None
        pythoncom.CoInitialize()
        try:
            connector = runtime["PhotoshopConnector"]()
            connector.connect()
            if psd_path:
                doc = connector.open_document(psd_path)
                opened_doc = True
            else:
                if not connector.app.Documents.Count:
                    raise RuntimeError("No open Photoshop document found")
                doc = connector.app.ActiveDocument

            source_path = str(doc.FullName)
            scan_rows = runtime["scan_document_for_ticket"](connector, doc, source_path)
            if not scan_rows:
                result_queue.put(("ok", {"ok": False, "message": "No text layers found", "source_psd": source_path}))
                return

            ticket_id = str(uuid.uuid4())
            ticket = _build_ticket(runtime, scan_rows, source_path, languages or [])
            ticket_path = _ticket_path(ticket_id, workspace)
            runtime["save_ticket_json"](ticket, str(ticket_path))
            artboards = sorted({row.artboard for row in scan_rows})
            result_queue.put(
                (
                    "ok",
                    {
                        "ok": True,
                        "ticket_id": ticket_id,
                        "ticket_path": str(ticket_path),
                        "ticket": ticket.to_dict(),
                        "source_psd": source_path,
                        "layer_count": len(scan_rows),
                        "artboard_count": len(artboards),
                        "artboards": artboards,
                    },
                )
            )
        except Exception as exc:
            result_queue.put(("error", str(exc)))
        finally:
            if connector and doc is not None and opened_doc:
                try:
                    connector.close_document(doc, save=False)
                except Exception:
                    pass
            if connector:
                try:
                    connector.disconnect()
                except Exception:
                    pass
            pythoncom.CoUninitialize()

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    thread.join(timeout_sec)

    if thread.is_alive():
        raise TimeoutError(f"Photoshop scan timed out after {timeout_sec} seconds")

    kind, payload = result_queue.get()
    if kind == "error":
        raise RuntimeError(payload)
    return payload


def _should_execute_task(task: Any) -> bool:
    if task.status == "skip":
        return False
    if task.status in {"confirmed", "ready", "approved"}:
        return True
    return bool((task.target_text or "").strip() or (task.target_font or "").strip())


def _default_output_name(source_path: str) -> str:
    source = Path(source_path)
    return f"{source.stem}_photoshop.psd"


def _group_tasks(tasks: list[Any]) -> dict[str, list[Any]]:
    grouped: dict[str, list[Any]] = {}
    for task in tasks:
        name = (task.output_name or "").strip()
        grouped.setdefault(name, []).append(task)
    return grouped


def start_ticket_execution(
    ticket_id: str,
    *,
    dry_run: bool = False,
    selected_task_indexes: list[int] | None = None,
    workspace: dict | None = None,
    job_id: str,
    on_progress: ProgressCallback | None = None,
    on_finish: FinishCallback | None = None,
) -> dict[str, Any]:
    from modules.adobe.photoshop.execution import start_ticket_execution_impl

    return start_ticket_execution_impl(
        ticket_id,
        dry_run=dry_run,
        selected_task_indexes=selected_task_indexes,
        workspace=workspace,
        job_id=job_id,
        on_progress=on_progress,
        on_finish=on_finish,
    )
