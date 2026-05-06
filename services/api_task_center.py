"""Task center API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.task_center import TaskStatus, TaskType, get_task_center

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskResponse(BaseModel):
    ok: bool
    message: str = ""
    task: dict[str, Any] | None = None
    tasks: list[dict[str, Any]] | None = None


class TaskDeleteBody(BaseModel):
    ids: list[str] = Field(default_factory=list)
    terminal_only: bool = True


def _enum_by_name(enum_cls, value: str | None):
    if not value:
        return None
    try:
        return enum_cls[value.upper()]
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=f"Unknown value: {value}") from exc


@router.get("/list", response_model=TaskResponse)
async def list_tasks(status: str | None = None, task_type: str | None = None, limit: int = 100):
    task_center = get_task_center()
    tasks = task_center.list_tasks(
        status=_enum_by_name(TaskStatus, status),
        task_type=_enum_by_name(TaskType, task_type),
        limit=max(1, min(limit, 1000)),
    )
    return TaskResponse(ok=True, message=f"Found {len(tasks)} tasks", tasks=tasks)


@router.get("/active", response_model=TaskResponse)
async def get_active_tasks():
    tasks = get_task_center().get_active_tasks()
    return TaskResponse(ok=True, message=f"Found {len(tasks)} active tasks", tasks=tasks)


@router.get("/history/week", response_model=TaskResponse)
async def get_weekly_history():
    task_center = get_task_center()
    tasks = (
        task_center.list_tasks(status=TaskStatus.COMPLETED, limit=1000)
        + task_center.list_tasks(status=TaskStatus.FAILED, limit=1000)
        + task_center.list_tasks(status=TaskStatus.CANCELLED, limit=1000)
    )
    tasks.sort(key=lambda item: item["created_at"], reverse=True)
    return TaskResponse(ok=True, message=f"Found {len(tasks)} historical tasks", tasks=tasks[:100])


@router.delete("/history/cleanup", response_model=TaskResponse)
async def cleanup_history():
    get_task_center()._cleanup_old_tasks()
    return TaskResponse(ok=True, message="Task history cleaned")


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    task = get_task_center().get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(ok=True, message="Task loaded", task=task)


@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(task_id: str):
    task_center = get_task_center()
    task = task_center.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not task_center.cancel_task(task_id):
        raise HTTPException(status_code=400, detail="Task cannot be cancelled")
    return TaskResponse(ok=True, message="Task cancelled", task=task_center.get_task(task_id))


@router.delete("/{task_id}", response_model=TaskResponse)
async def delete_task(task_id: str, allow_active: bool = False):
    task_center = get_task_center()
    task = task_center.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not task_center.delete_task(task_id, allow_active=allow_active):
        raise HTTPException(status_code=400, detail="Active tasks must be cancelled before deletion")
    return TaskResponse(ok=True, message="Task deleted")


@router.post("/clear", response_model=TaskResponse)
async def clear_tasks(body: TaskDeleteBody):
    task_center = get_task_center()
    deleted = task_center.delete_tasks(
        task_ids=body.ids or None,
        statuses=None if not body.terminal_only else [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED],
        task_type=TaskType.DOWNLOAD if not body.ids else None,
        allow_active=not body.terminal_only,
    )
    return TaskResponse(ok=True, message=f"Deleted {deleted} tasks")
