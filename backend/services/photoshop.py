"""Photoshop 自动化服务（向后兼容层）

核心逻辑已迁移到 modules/adobe/photoshop/service.py。
此文件保留原有导出接口，确保现有调用方不受影响。
"""

from modules.adobe.common.execution import (
    cancel_execution,
    get_execution_state,
)
from modules.adobe.photoshop.service import (
    delete_photoshop_ticket,
    get_photoshop_status,
    get_photoshop_ticket,
    list_photoshop_tickets,
    save_photoshop_ticket,
    scan_photoshop_document,
    start_ticket_execution,
)

__all__ = [
    "cancel_execution",
    "get_execution_state",
    "delete_photoshop_ticket",
    "get_photoshop_status",
    "get_photoshop_ticket",
    "list_photoshop_tickets",
    "save_photoshop_ticket",
    "scan_photoshop_document",
    "start_ticket_execution",
]
