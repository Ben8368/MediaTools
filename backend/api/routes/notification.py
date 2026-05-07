"""Notification API routes."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.services.notification import get_notification_manager

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
async def get_notifications(unread_only: bool = False):
    """Return notifications, optionally filtered to unread only."""
    manager = get_notification_manager()
    notifications = manager.get_notifications(unread_only=unread_only)
    unread_count = manager.get_unread_count()
    return JSONResponse({
        "ok": True,
        "notifications": notifications,
        "unread_count": unread_count,
    })


@router.get("/unread-count")
async def get_unread_count():
    """Return count of unread notifications."""
    manager = get_notification_manager()
    return JSONResponse({
        "ok": True,
        "unread_count": manager.get_unread_count(),
    })


@router.post("/mark-as-read/{notification_id}")
async def mark_as_read(notification_id: str):
    """Mark a notification as read."""
    manager = get_notification_manager()
    success = manager.mark_as_read(notification_id)
    return JSONResponse({
        "ok": success,
        "unread_count": manager.get_unread_count(),
    })


@router.post("/mark-all-as-read")
async def mark_all_as_read():
    """Mark all notifications as read."""
    manager = get_notification_manager()
    count = manager.mark_all_as_read()
    return JSONResponse({
        "ok": True,
        "marked_count": count,
        "unread_count": manager.get_unread_count(),
    })


@router.post("/clear")
async def clear_notifications():
    """Clear all notifications."""
    manager = get_notification_manager()
    manager.clear_all()
    return JSONResponse({
        "ok": True,
        "unread_count": 0,
    })
