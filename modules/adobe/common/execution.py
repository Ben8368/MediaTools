"""统一的 Adobe 工具执行状态管理"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AdobeExecutionState:
    """Adobe 工具执行状态（通用）"""
    ticket_id: str
    job_id: str
    cancel_event: threading.Event
    tool: str = "photoshop"  # "photoshop" | "after_effects"，默认 photoshop 保持向后兼容
    status: str = "running"  # "running" | "done" | "error" | "cancelled"
    message: str = "Waiting to start"
    progress: float = 0.0
    output_paths: list[str] = field(default_factory=list)
    error: str = ""
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticket_id": self.ticket_id,
            "job_id": self.job_id,
            "tool": self.tool,
            "status": self.status,
            "message": self.message,
            "progress": self.progress,
            "output_paths": list(self.output_paths),
            "error": self.error,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }

_executions: dict[str, AdobeExecutionState] = {}
_executions_guard = threading.Lock()

def get_execution_state(ticket_id: str) -> dict[str, Any] | None:
    """获取执行状态"""
    with _executions_guard:
        state = _executions.get(ticket_id)
        return state.to_dict() if state else None

def cancel_execution(ticket_id: str) -> dict[str, Any]:
    """取消执行"""
    with _executions_guard:
        state = _executions.get(ticket_id)
        if not state:
            raise FileNotFoundError(f"No running execution for ticket {ticket_id}")
        if state.status != "running":
            raise RuntimeError(f"Execution for ticket {ticket_id} is not running")
        state.cancel_event.set()
        state.message = "Cancellation requested"
        return state.to_dict()
