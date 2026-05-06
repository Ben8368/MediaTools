from __future__ import annotations

import shutil
import threading
import time
from collections.abc import Callable
from typing import Any

from modules.adobe.common.execution import AdobeExecutionState, _executions, _executions_guard

ProgressCallback = Callable[[str, float], None]
FinishCallback = Callable[[bool, dict[str, Any]], None]


def start_ticket_execution_impl(
    ticket_id: str,
    *,
    dry_run: bool = False,
    selected_task_indexes: list[int] | None = None,
    workspace: dict | None = None,
    job_id: str,
    on_progress: ProgressCallback | None = None,
    on_finish: FinishCallback | None = None,
) -> dict[str, Any]:
    from . import service as photoshop_service

    runtime = photoshop_service._runtime()
    ticket_path = photoshop_service._ticket_path(ticket_id, workspace)
    if not ticket_path.exists():
        raise FileNotFoundError(f"Ticket not found: {ticket_id}")

    with photoshop_service._execution_lock:
        active = [item for item in _executions.values() if item.status == "running"]
        if active:
            raise RuntimeError("Another Photoshop execution is already running")

        state = AdobeExecutionState(
            ticket_id=ticket_id,
            job_id=job_id,
            tool="photoshop",
            cancel_event=threading.Event(),
        )
        with _executions_guard:
            _executions[ticket_id] = state

        def _worker() -> None:
            pythoncom = runtime["pythoncom"]
            connector = None
            doc = None
            output_paths: list[str] = []
            pythoncom.CoInitialize()
            try:
                ticket = runtime["load_ticket_json"](str(ticket_path))
                source_psd = str(ticket.meta.source_psd or "").strip()
                if not source_psd:
                    raise RuntimeError("Ticket is missing source_psd")

                selected_indexes = set(selected_task_indexes) if selected_task_indexes is not None else None
                candidate_tasks = [
                    task
                    for index, task in enumerate(ticket.tasks)
                    if (selected_indexes is None or index in selected_indexes) and photoshop_service._should_execute_task(task)
                ]
                if not candidate_tasks:
                    raise RuntimeError("Ticket does not contain selected confirmed or filled tasks")

                grouped_tasks = photoshop_service._group_tasks(candidate_tasks)
                total_tasks = len(candidate_tasks)
                completed = 0
                params = runtime["AdjustParams"](
                    tracking_min=-50,
                    tracking_step=5,
                    font_size_min_ratio=0.5,
                    tolerance=0.05,
                )

                connector = runtime["PhotoshopConnector"]()
                connector.connect()

                for output_name, tasks in grouped_tasks.items():
                    if state.cancel_event.is_set():
                        state.status = "cancelled"
                        state.message = "Execution cancelled before writing output"
                        break

                    target_name = output_name or photoshop_service._default_output_name(source_psd)
                    output_path = photoshop_service._exports_dir(workspace) / ticket_id / target_name
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    if not dry_run:
                        shutil.copy2(source_psd, output_path)
                        doc = connector.open_document(str(output_path))
                    else:
                        if not connector.app.Documents.Count:
                            raise RuntimeError("No open Photoshop document found for dry run")
                        doc = connector.app.ActiveDocument

                    scan_rows = runtime["scan_document_for_ticket"](connector, doc, source_psd)
                    scan_map = {row.layer_id: row for row in scan_rows}

                    for task in tasks:
                        if state.cancel_event.is_set():
                            state.status = "cancelled"
                            state.message = "Execution cancelled"
                            break

                        state.message = f"Applying {task.layer_name}"
                        completed += 1
                        state.progress = round(completed / max(total_tasks, 1) * 100.0, 2)
                        if on_progress:
                            on_progress(state.message, state.progress)

                        row = scan_map.get(task.layer_id)
                        if row is None:
                            task.status = "error"
                            task.notes = "Layer id not found during execution"
                            continue

                        mapping = runtime["TextMapping"](
                            match_mode="exact",
                            original_text=row.raw_text,
                            new_text=(task.target_text or "").strip() or None,
                            font=(task.target_font or "").strip() or None,
                        )

                        result = runtime["modify_text_layer"](connector, row.layer_obj, mapping, params)
                        task.status = "done" if result.success else "error"
                        task.notes = result.message or ""

                    if state.cancel_event.is_set():
                        if not dry_run and doc is not None:
                            connector.close_document(doc, save=False)
                            doc = None
                            if output_path.exists():
                                output_path.unlink(missing_ok=True)
                        break

                    if not dry_run and doc is not None:
                        doc.Save()
                        connector.close_document(doc, save=False)
                        doc = None
                        output_paths.append(str(output_path))

                runtime["save_ticket_json"](ticket, str(ticket_path))

                if state.status == "cancelled":
                    state.finished_at = time.time()
                    state.output_paths = output_paths
                    if on_finish:
                        on_finish(False, {"status": "cancelled", "output_paths": output_paths, "ticket_id": ticket_id})
                    return

                state.status = "done"
                state.progress = 100.0
                state.output_paths = output_paths
                state.message = "Photoshop execution completed"
                state.finished_at = time.time()
                if on_finish:
                    on_finish(True, {"status": "done", "output_paths": output_paths, "ticket_id": ticket_id, "dry_run": dry_run})
            except Exception as exc:
                state.status = "error"
                state.error = str(exc)
                state.message = str(exc)
                state.finished_at = time.time()
                if doc is not None and connector:
                    try:
                        connector.close_document(doc, save=False)
                    except Exception:
                        pass
                if on_finish:
                    on_finish(False, {"status": "error", "error": str(exc), "ticket_id": ticket_id})
            finally:
                if connector:
                    try:
                        connector.disconnect()
                    except Exception:
                        pass
                pythoncom.CoUninitialize()

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        return {"ok": True, "ticket_id": ticket_id, "job_id": job_id}
