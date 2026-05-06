"""Adobe 统一模块入口

提供 Photoshop 和 After Effects 的统一接口。
"""

from modules.adobe.after_effects import (
    get_ae_status,
    list_ae_tickets,
    scan_ae_project,
)
from modules.adobe.photoshop import (
    cancel_execution,
    get_execution_state,
    get_photoshop_status,
    get_photoshop_ticket,
    list_photoshop_tickets,
    save_photoshop_ticket,
    scan_photoshop_document,
    start_ticket_execution,
)

__all__ = [
    # Photoshop
    "cancel_execution",
    "get_execution_state",
    "get_photoshop_status",
    "get_photoshop_ticket",
    "list_photoshop_tickets",
    "save_photoshop_ticket",
    "scan_photoshop_document",
    "start_ticket_execution",
    # After Effects
    "get_ae_status",
    "list_ae_tickets",
    "scan_ae_project",
]
