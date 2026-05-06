"""After Effects ??????????COM ????"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from adapters.after_effects_runtime import AfterEffectsAutomationAdapter
from modules.adobe.common.execution import (
    _executions,
    _executions_guard,
)

ProgressCallback = Callable[[str, float], None]
FinishCallback = Callable[[bool, dict[str, Any]], None]

_adapter = AfterEffectsAutomationAdapter()
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


def _ae_root(kind: str, workspace: dict | None = None) -> Path:
    base = _require_workspace_dir(kind, workspace)
    root = base / "after_effects"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _tickets_dir(workspace: dict | None = None) -> Path:
    target = _ae_root("manifests", workspace) / "tickets"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _exports_dir(workspace: dict | None = None) -> Path:
    target = _ae_root("exports", workspace) / "renders"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _ticket_path(ticket_id: str, workspace: dict | None = None) -> Path:
    return _tickets_dir(workspace) / f"{ticket_id}.json"


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
    tasks = [t for t in payload.get("tasks", []) if isinstance(t, dict)]
    return {
        "ticket_id": path.stem,
        "path": str(path),
        "source_project": meta.get("source_project", ""),
        "created_at": meta.get("created_at", ""),
        "task_count": len(tasks),
        "confirmed_count": sum(1 for t in tasks if t.get("status") == "confirmed"),
        "updated_at": path.stat().st_mtime,
    }


def get_ae_status(workspace: dict | None = None) -> dict[str, Any]:
    status = _adapter.get_status()
    with _executions_guard:
        running = sum(
            1 for s in _executions.values()
            if s.tool == "after_effects" and s.status == "running"
        )
    status.update({
        "tickets_dir": str(_tickets_dir(workspace)),
        "exports_dir": str(_exports_dir(workspace)),
        "running_executions": running,
    })
    return status


def list_ae_tickets(workspace: dict | None = None) -> list[dict[str, Any]]:
    tickets: list[dict[str, Any]] = []
    for path in sorted(_tickets_dir(workspace).glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            tickets.append(_ticket_summary(path, _load_ticket_payload(path)))
        except Exception:
            continue
    return tickets


def get_ae_ticket(ticket_id: str, workspace: dict | None = None) -> dict[str, Any]:
    path = _ticket_path(ticket_id, workspace)
    if not path.exists():
        raise FileNotFoundError(f"Ticket not found: {ticket_id}")
    return {"ticket_id": ticket_id, "path": str(path), "ticket": _load_ticket_payload(path)}


def save_ae_ticket(ticket_id: str, ticket_payload: dict[str, Any], workspace: dict | None = None) -> dict[str, Any]:
    path = _ticket_path(ticket_id, workspace)
    _save_ticket_payload(path, ticket_payload)
    return {"ticket_id": ticket_id, "path": str(path), "ticket": _load_ticket_payload(path)}


def _build_ticket_from_layers(layers: list[dict[str, Any]], source_project: str) -> dict[str, Any]:
    return {
        "meta": {
            "created_by": "mediatools_scan",
            "source_project": source_project,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "tool": "after_effects",
            "platform": "com",
        },
        "tasks": layers,
    }


# ---------------------------------------------------------------------------
# 扫描（COM）
# ---------------------------------------------------------------------------

def scan_ae_project(
    *,
    project_path: str = "",
    workspace: dict | None = None,
) -> dict[str, Any]:
    from modules.adobe.after_effects.scan import scan_ae_project_impl

    return scan_ae_project_impl(project_path=project_path, workspace=workspace)


# ---------------------------------------------------------------------------
# 执行（COM）
# ---------------------------------------------------------------------------

def _should_execute_task(task: dict[str, Any]) -> bool:
    if task.get("status") == "skip":
        return False
    if task.get("status") in {"confirmed", "ready", "approved"}:
        return True
    return bool((task.get("target_text") or "").strip() or (task.get("target_font") or "").strip())


def start_ae_ticket_execution(
    ticket_id: str,
    *,
    dry_run: bool = False,
    selected_task_indexes: list[int] | None = None,
    workspace: dict | None = None,
    job_id: str,
    on_progress: ProgressCallback | None = None,
    on_finish: FinishCallback | None = None,
) -> dict[str, Any]:
    from modules.adobe.after_effects.execution import start_ae_ticket_execution_impl

    return start_ae_ticket_execution_impl(
        ticket_id,
        dry_run=dry_run,
        selected_task_indexes=selected_task_indexes,
        workspace=workspace,
        job_id=job_id,
        on_progress=on_progress,
        on_finish=on_finish,
    )


def list_ae_fonts(query: str = "", limit: int = 200, workspace: dict | None = None) -> dict[str, Any]:
    from modules.adobe.after_effects.scan import list_ae_fonts_impl

    return list_ae_fonts_impl(query=query, limit=limit, workspace=workspace)


def create_ae_checkpoint(
    project_path: str,
    label: str = "",
    step_index: int = 0,
    notes: str = "",
    workspace: dict | None = None,
) -> dict[str, Any]:
    from modules.adobe.after_effects.project_ops import create_ae_checkpoint_impl

    return create_ae_checkpoint_impl(
        project_path=project_path,
        label=label,
        step_index=step_index,
        notes=notes,
        workspace=workspace,
    )


def revert_ae_checkpoint(
    checkpoint_path: str,
    create_branch: bool = False,
    workspace: dict | None = None,
) -> dict[str, Any]:
    from modules.adobe.after_effects.project_ops import revert_ae_checkpoint_impl

    return revert_ae_checkpoint_impl(
        checkpoint_path=checkpoint_path,
        create_branch=create_branch,
        workspace=workspace,
    )


def list_ae_checkpoints(project_path: str, workspace: dict | None = None) -> dict[str, Any]:
    from modules.adobe.after_effects.project_ops import list_ae_checkpoints_impl

    return list_ae_checkpoints_impl(project_path=project_path, workspace=workspace)


def add_ae_to_render_queue(
    project_path: str,
    comp_index: int,
    output_path: str,
    output_module_template: str = "Best Settings",
    workspace: dict | None = None,
) -> dict[str, Any]:
    from modules.adobe.after_effects.project_ops import add_ae_to_render_queue_impl

    return add_ae_to_render_queue_impl(
        project_path=project_path,
        comp_index=comp_index,
        output_path=output_path,
        output_module_template=output_module_template,
        workspace=workspace,
    )


def start_ae_render(
    project_path: str,
    workspace: dict | None = None,
    on_progress: ProgressCallback | None = None,
    on_finish: FinishCallback | None = None,
) -> dict[str, Any]:
    from modules.adobe.after_effects.project_ops import start_ae_render_impl

    return start_ae_render_impl(
        project_path=project_path,
        workspace=workspace,
        on_progress=on_progress,
        on_finish=on_finish,
    )


def get_ae_render_queue_status(project_path: str, workspace: dict | None = None) -> dict[str, Any]:
    from modules.adobe.after_effects.project_ops import get_ae_render_queue_status_impl

    return get_ae_render_queue_status_impl(project_path=project_path, workspace=workspace)
