from __future__ import annotations

import logging
import shutil
import threading
import time
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from modules.adobe.common.execution import AdobeExecutionState, _executions, _executions_guard

_NOTICE = 25
logging.addLevelName(_NOTICE, "NOTICE")

def _log_notice(logger: logging.Logger, msg: str, *args: Any) -> None:
    logger.log(_NOTICE, msg, *args)

_log = logging.getLogger("photoshop.execution")

ProgressCallback = Callable[[str, float], None]
FinishCallback = Callable[[bool, dict[str, Any]], None]

_PRESERVE_COPY_MESSAGE = "固定文案：已跳过写入，保留从母版复制到该 PSD 后的图层内容"


def _task_preserve_copy(task: Any) -> bool:
    if isinstance(task, dict):
        return bool(task.get("preserve_copy"))
    return bool(getattr(task, "preserve_copy", False))


def _set_task_result(task: Any, result: Any) -> bool:
    task.status = "done" if result.success else "error"
    task.notes = result.message or ""
    return bool(result.success)


def _build_mapping(runtime: dict[str, Any], task: Any) -> Any:
    orig = str(getattr(task, "original_text", "") or "")
    tt = getattr(task, "target_text", None)
    new_text = None if tt is None else str(tt)
    return runtime["TextMapping"](
        match_mode="exact",
        original_text=orig,
        new_text=new_text,
        font=(task.target_font or "").strip() or None,
    )


def _resolve_smart_layer(connector: Any, doc: Any, task: Any) -> tuple[Any | None, int]:
    layer_id = int(getattr(task, "smart_object_layer_id", 0) or 0)
    layer = connector.find_layer_by_id(doc, layer_id) if layer_id else None
    if layer is None:
        return None, 0
    try:
        if not connector.is_smart_object_layer(layer):
            return None, 0
    except Exception:
        return None, 0
    return layer, layer_id


def _output_directory(source_psd: str, ticket_meta: Any) -> Path:
    configured = str(getattr(ticket_meta, "output_dir", "") or "").strip()
    return Path(configured) if configured else Path(source_psd).parent


def _output_filename(output_name: str, source_psd: str) -> str:
    name = Path(str(output_name or "").strip()).name
    return name or photoshop_default_output_name(source_psd)


def photoshop_default_output_name(source_psd: str) -> str:
    return f"{Path(source_psd).stem}_photoshop.psd"


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
            layer_results: list[dict] = []
            log_paths: list[str] = []
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
                    if (selected_indexes is None or index in selected_indexes)
                    and photoshop_service._should_execute_task(task)
                ]
                if not candidate_tasks:
                    raise RuntimeError("Ticket does not contain selected confirmed or filled tasks")

                grouped_tasks = photoshop_service._group_tasks(candidate_tasks)
                total_tasks = len(candidate_tasks)
                completed = 0
                successful_tasks = 0
                failed_tasks = 0
                skipped_tasks = 0
                _log_notice(_log, "🚀 开始执行工单 %s (%d 个任务)", ticket_id, total_tasks)
                params = runtime["AdjustParams"](
                    tracking_min=-50,
                    tracking_step=5,
                    font_size_min_ratio=0.75,
                    font_size_max_ratio=1.25,
                    tolerance=0.05,
                    height_tolerance=0.08,
                )

                connector = runtime["PhotoshopConnector"]()
                connector.connect()

                grouped_items = list(grouped_tasks.items())
                for group_index, (output_name, tasks) in enumerate(grouped_items):
                    if state.cancel_event.is_set():
                        state.status = "cancelled"
                        state.message = "Execution cancelled before writing output"
                        break

                    target_name = _output_filename(output_name, source_psd)
                    output_dir = _output_directory(source_psd, ticket.meta)
                    try:
                        output_dir.mkdir(parents=True, exist_ok=True)
                        candidate = output_dir / target_name
                        # Never overwrite the source PSD itself
                        if candidate.resolve() == Path(source_psd).resolve():
                            candidate = output_dir / photoshop_service._default_output_name(source_psd)
                        output_path = candidate
                    except Exception as exc:
                        raise RuntimeError(f"Cannot prepare Photoshop output directory: {output_dir}") from exc
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    if not dry_run:
                        try:
                            shutil.copy2(source_psd, output_path)
                            doc = connector.open_document(str(output_path))
                        except Exception as exc:
                            _log.error("Failed to prepare output %s: %s", output_path, exc)
                            state.message = f"Failed to open output for {output_name}"
                            failed_tasks += len(tasks)
                            for task in tasks:
                                task.status = "error"
                                task.notes = f"Output preparation failed: {exc}"
                            # Still save partially-updated ticket
                            runtime["save_ticket_json"](ticket, str(ticket_path))
                            continue
                    else:
                        if not connector.app.Documents.Count:
                            raise RuntimeError("No open Photoshop document found for dry run")
                        doc = connector.app.ActiveDocument

                    target_errors: dict[int, str] = {}
                    # Build font index once per output group for reuse across tasks
                    try:
                        _font_index = runtime["build_font_index"](connector.app)
                    except Exception:
                        _font_index = None

                    for task in tasks:
                        if state.cancel_event.is_set():
                            state.status = "cancelled"
                            state.message = "Execution cancelled"
                            break

                        if _task_preserve_copy(task):
                            state.message = f"Skip fixed copy: {task.layer_name}"
                            completed += 1
                            state.progress = round(completed / max(total_tasks, 1) * 100.0, 2)
                            if on_progress:
                                on_progress(state.message, state.progress)
                            if _set_task_result(task, SimpleNamespace(success=True, message=_PRESERVE_COPY_MESSAGE)):
                                successful_tasks += 1
                                _log_notice(_log, "⏭ %s: %s", task.layer_name, _PRESERVE_COPY_MESSAGE)
                            else:
                                failed_tasks += 1
                            skipped_tasks += 1
                            layer_results.append({
                                "layer_name": task.layer_name,
                                "original_text": getattr(task, "original_text", ""),
                                "new_text": getattr(task, "target_text", ""),
                                "skipped": True,
                                "converged": True,
                                "message": _PRESERVE_COPY_MESSAGE,
                                "fit_status": "skipped",
                            })
                            continue

                        if photoshop_service._is_smart_object_task(task):
                            state.message = f"Applying smart object {task.layer_name}"
                            completed += 1
                            state.progress = round(completed / max(total_tasks, 1) * 100.0, 2)
                            if on_progress:
                                on_progress(state.message, state.progress)

                            smart_layer, smart_layer_id = _resolve_smart_layer(connector, doc, task)
                            if smart_layer is None:
                                task.status = "error"
                                task.notes = "Smart object layer not found during execution"
                                failed_tasks += 1
                                _log.warning("❌ [smart_object] %s: %s", task.layer_name, task.notes or "unknown error")
                                continue
                            task.smart_object_layer_id = smart_layer_id
                            result = runtime["modify_smart_object_text_layer"](
                                connector,
                                doc,
                                task,
                                _build_mapping(runtime, task),
                                params,
                            )
                            if _set_task_result(task, result):
                                successful_tasks += 1
                                _log_notice(_log, "✅ [smart_object] %s: %s", task.layer_name, result.message or "success")
                            else:
                                failed_tasks += 1
                                _log.warning("❌ [smart_object] %s: %s", task.layer_name, result.message or "unknown error")
                            if hasattr(result, 'skipped') and result.skipped:
                                skipped_tasks += 1
                            if hasattr(result, 'log_path') and result.log_path:
                                log_paths.append(result.log_path)
                            layer_results.append({
                                "layer_name": getattr(result, "layer_name", task.layer_name),
                                "original_text": getattr(result, "original_text", ""),
                                "new_text": getattr(result, "new_text", ""),
                                "original_font_size": getattr(result, "original_font_size", 0),
                                "final_font_size": getattr(result, "final_font_size", 0),
                                "original_font": getattr(result, "original_font", ""),
                                "new_font": getattr(result, "new_font", ""),
                                "converged": getattr(result, "converged", False),
                                "skipped": getattr(result, "skipped", False),
                                "message": getattr(result, "message", ""),
                                "fit_status": getattr(result, "fit_status", ""),
                                "log_path": getattr(result, "log_path", ""),
                            })
                        else:
                            state.message = f"Applying {task.layer_name}"
                            completed += 1
                            state.progress = round(completed / max(total_tasks, 1) * 100.0, 2)
                            if on_progress:
                                on_progress(state.message, state.progress)

                            layer_obj = connector.find_layer_by_id(doc, int(getattr(task, "layer_id", 0) or 0))
                            if layer_obj is None:
                                task.status = "error"
                                task.notes = "Layer id not found during execution"
                                failed_tasks += 1
                                _log.warning("❌ [text_layer] %s: %s", task.layer_name, task.notes or "unknown error")
                                continue
                            original_font_size = float(getattr(task, "font_size", 0) or 0)
                            result = runtime["modify_text_layer"](
                                connector, layer_obj, _build_mapping(runtime, task), params,
                                font_index=_font_index,
                                output_dir=str(output_dir),
                            )
                            if _set_task_result(task, result):
                                successful_tasks += 1
                                _log_notice(_log, "✅ [text_layer] %s: font_size %.2f→%.2fpx, tracking %d→%d, leading %.1f→%.1f [%s]",
                                    task.layer_name, float(getattr(result, "original_font_size", 0)), float(getattr(result, "final_font_size", 0)),
                                    int(getattr(result, "original_tracking", 0)), int(getattr(result, "final_tracking", 0)),
                                    float(getattr(result, "original_leading", 0)), float(getattr(result, "final_leading", 0)),
                                    str(getattr(result, "fit_status", "ok")))
                            else:
                                failed_tasks += 1
                                _log.warning("❌ [text_layer] %s: %s", task.layer_name, result.message or "unknown error")
                            if hasattr(result, 'skipped') and result.skipped:
                                skipped_tasks += 1
                            if hasattr(result, 'log_path') and result.log_path:
                                log_paths.append(result.log_path)
                            layer_results.append({
                                "layer_name": getattr(result, "layer_name", task.layer_name),
                                "original_text": getattr(result, "original_text", ""),
                                "new_text": getattr(result, "new_text", ""),
                                "original_font_size": getattr(result, "original_font_size", 0),
                                "final_font_size": getattr(result, "final_font_size", 0),
                                "original_font": getattr(result, "original_font", ""),
                                "new_font": getattr(result, "new_font", ""),
                                "converged": getattr(result, "converged", False),
                                "skipped": getattr(result, "skipped", False),
                                "message": getattr(result, "message", ""),
                                "fit_status": getattr(result, "fit_status", ""),
                                "log_path": getattr(result, "log_path", ""),
                            })

                    if state.cancel_event.is_set():
                        if not dry_run and doc is not None:
                            connector.close_document(doc, save=False)
                            doc = None
                            if output_path.exists():
                                output_path.unlink(missing_ok=True)
                        break

                    if not dry_run and doc is not None:
                        try:
                            doc.Save()
                        except Exception as exc:
                            _log.warning("Failed to save output %s: %s", output_path, exc)
                        leave_open = group_index == len(grouped_items) - 1
                        if not leave_open:
                            try:
                                connector.close_document(doc, save=False)
                            except Exception:
                                pass
                        doc = None
                        output_paths.append(str(output_path))

                # Save ticket after every group so partial progress is never lost
                runtime["save_ticket_json"](ticket, str(ticket_path))
                _log_notice(_log, "📄 语种组 %s: %d 成功, %d 失败, %d 跳过 → %s",
                            output_name or "(default)",
                            sum(1 for _ in tasks if getattr(_, "status", None) == "done"),
                            sum(1 for _ in tasks if getattr(_, "status", None) == "error"),
                            sum(1 for _ in tasks if getattr(_, "status", None) == "skip"),
                            output_path if not dry_run else "(dry-run)")

                state.layer_results = layer_results
                state.log_paths = log_paths

                if state.status == "cancelled":
                    state.finished_at = time.time()
                    state.output_paths = output_paths
                    if on_finish:
                        on_finish(False, {
                            "status": "cancelled", "output_paths": output_paths,
                            "ticket_id": ticket_id, "layer_results": layer_results,
                            "log_paths": log_paths,
                        })
                    return

                state.progress = 100.0
                state.output_paths = output_paths
                state.finished_at = time.time()
                if successful_tasks <= 0:
                    state.status = "error"
                    state.error = "Photoshop execution completed without any successful task"
                    state.message = state.error
                    if on_finish:
                        on_finish(
                            False,
                            {
                                "status": "error",
                                "error": state.error,
                                "output_paths": output_paths,
                                "ticket_id": ticket_id,
                                "dry_run": dry_run,
                                "failed_tasks": failed_tasks,
                                "layer_results": layer_results,
                                "log_paths": log_paths,
                            },
                        )
                    return

                state.status = "done"
                state.message = "Photoshop execution completed. The latest output PSD is open in Photoshop."
                if failed_tasks:
                    state.message = f"{state.message} {failed_tasks} selected task(s) failed; check ticket notes."
                if on_finish:
                    on_finish(
                        True,
                        {
                            "status": "done",
                            "output_paths": output_paths,
                            "ticket_id": ticket_id,
                            "dry_run": dry_run,
                            "successful_tasks": successful_tasks,
                            "failed_tasks": failed_tasks,
                            "skipped_tasks": skipped_tasks,
                            "layer_results": layer_results,
                            "log_paths": log_paths,
                        },
                    )
                if successful_tasks > 0:
                    summary = f"工单 {ticket_id} 执行完成: 成功 {successful_tasks} 条，失败 {failed_tasks} 条"
                    _log_notice(_log, "📊 工单 %s 执行完成: 成功 %d 条, 失败 %d 条", ticket_id, successful_tasks, failed_tasks)
            except Exception as exc:
                state.status = "error"
                state.error = str(exc)
                state.message = str(exc)
                state.finished_at = time.time()
                # Save ticket with any partial progress before giving up
                try:
                    runtime["save_ticket_json"](ticket, str(ticket_path))
                except Exception:
                    pass
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
