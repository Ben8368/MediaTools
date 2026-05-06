from __future__ import annotations

import shutil
import threading
import time
from collections.abc import Callable
from typing import Any

from modules.adobe.common.execution import AdobeExecutionState, _executions, _executions_guard

ProgressCallback = Callable[[str, float], None]
FinishCallback = Callable[[bool, dict[str, Any]], None]


def start_ae_ticket_execution_impl(
    ticket_id: str,
    *,
    dry_run: bool = False,
    selected_task_indexes: list[int] | None = None,
    workspace: dict | None = None,
    job_id: str,
    on_progress: ProgressCallback | None = None,
    on_finish: FinishCallback | None = None,
) -> dict[str, Any]:
    from . import service as ae_service

    ticket_file = ae_service._ticket_path(ticket_id, workspace)
    if not ticket_file.exists():
        raise FileNotFoundError(f"Ticket not found: {ticket_id}")

    with ae_service._execution_lock:
        state = AdobeExecutionState(ticket_id=ticket_id, job_id=job_id, tool="after_effects", cancel_event=threading.Event())
        with _executions_guard:
            _executions[ticket_id] = state

        def _worker() -> None:
            runtime = ae_service._adapter.load_runtime()
            pythoncom = runtime["pythoncom"]
            AfterEffectsConnector = runtime["AfterEffectsConnector"]
            pythoncom.CoInitialize()
            connector = AfterEffectsConnector()
            output_paths: list[str] = []

            try:
                payload = ae_service._load_ticket_payload(ticket_file)
                source_project = payload.get("meta", {}).get("source_project", "").strip()
                if not source_project:
                    raise RuntimeError("Ticket is missing source_project")

                all_tasks = [task for task in payload.get("tasks", []) if isinstance(task, dict)]
                selected_indexes = set(selected_task_indexes) if selected_task_indexes is not None else None
                candidate_tasks = [
                    (idx, task)
                    for idx, task in enumerate(all_tasks)
                    if (selected_indexes is None or idx in selected_indexes) and ae_service._should_execute_task(task)
                ]
                if not candidate_tasks:
                    raise RuntimeError("No executable tasks found in ticket")

                groups: dict[str, list[tuple[int, dict[str, Any]]]] = {}
                for idx, task in candidate_tasks:
                    name = (task.get("output_name") or "output.aep").strip()
                    groups.setdefault(name, []).append((idx, task))

                total = len(candidate_tasks)
                completed = 0
                connector.connect()

                for output_name, group_tasks in groups.items():
                    if state.cancel_event.is_set():
                        state.status = "cancelled"
                        state.message = "Execution cancelled"
                        break

                    output_path = ae_service._exports_dir(workspace) / ticket_id / output_name
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    if not dry_run:
                        shutil.copy2(source_project, output_path)
                        connector.open_project(str(output_path))
                    else:
                        connector.open_project(source_project)

                    changes: list[dict[str, Any]] = []
                    for idx, task in group_tasks:
                        if state.cancel_event.is_set():
                            break
                        changes.append({
                            "comp_index": task.get("comp_index"),
                            "layer_index": task.get("layer_index"),
                            "target_text": (task.get("target_text") or "").strip() or None,
                            "target_font": (task.get("target_font") or "").strip() or None,
                            "font_size": task.get("font_size") or None,
                            "tracking": task.get("tracking") if task.get("tracking") is not None else None,
                        })

                    if state.cancel_event.is_set():
                        connector.close_project()
                        break

                    state.message = f"Applying {len(changes)} changes to {output_name}"
                    if on_progress:
                        on_progress(state.message, round(completed / max(total, 1) * 100.0, 2))

                    if not dry_run:
                        apply_results = connector.apply_text_changes(changes)
                        apply_map = {(result.get("comp_index"), result.get("layer_index")): result for result in apply_results}
                        for idx, task in group_tasks:
                            key = (task.get("comp_index"), task.get("layer_index"))
                            result = apply_map.get(key)
                            if result:
                                task["status"] = "done" if result.get("ok") else "error"
                                task["notes"] = result.get("msg", "")
                            else:
                                task["status"] = "error"
                                task["notes"] = "No result returned from AE"
                            completed += 1
                            state.progress = round(completed / max(total, 1) * 100.0, 2)
                            if on_progress:
                                on_progress(f"Applied {task.get('layer_name', '')}", state.progress)

                        connector.save_project(str(output_path))
                        output_paths.append(str(output_path))
                    else:
                        for idx, task in group_tasks:
                            task["status"] = "done"
                            task["notes"] = "dry_run"
                            completed += 1
                        output_paths.append(str(output_path))

                    connector.close_project()

                ae_service._save_ticket_payload(ticket_file, payload)

                if state.cancel_event.is_set() or state.status == "cancelled":
                    state.status = "cancelled"
                    state.finished_at = time.time()
                    state.output_paths = output_paths
                    if on_finish:
                        on_finish(False, {"status": "cancelled", "output_paths": output_paths, "ticket_id": ticket_id})
                    return

                state.status = "done"
                state.progress = 100.0
                state.output_paths = output_paths
                state.message = "After Effects execution completed"
                state.finished_at = time.time()
                if on_finish:
                    on_finish(True, {"status": "done", "output_paths": output_paths, "ticket_id": ticket_id, "dry_run": dry_run})
            except Exception as exc:
                state.status = "error"
                state.error = str(exc)
                state.message = str(exc)
                state.finished_at = time.time()
                if on_finish:
                    on_finish(False, {"status": "error", "error": str(exc), "ticket_id": ticket_id})
            finally:
                try:
                    connector.disconnect()
                except Exception:
                    pass
                pythoncom.CoUninitialize()

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        return {"ok": True, "ticket_id": ticket_id, "job_id": job_id}
