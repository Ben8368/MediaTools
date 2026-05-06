"""Photoshop 执行状态（向后兼容层）

执行状态管理已迁移到 modules/adobe/common/execution.py。
此文件保留原有导出接口，确保现有调用方不受影响。
"""

from modules.adobe.common.execution import (
    AdobeExecutionState as PhotoshopExecutionState,
)
from modules.adobe.common.execution import (
    _executions,
    _executions_guard,
    cancel_execution,
    get_execution_state,
)

__all__ = [
    "PhotoshopExecutionState",
    "_executions",
    "_executions_guard",
    "cancel_execution",
    "get_execution_state",
]
