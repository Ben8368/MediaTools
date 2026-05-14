"""Notification system for real-time events."""

from __future__ import annotations

import json
import threading
import time
from collections import deque
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.config import BASE_DIR


@dataclass
class Notification:
    """Notification record."""
    id: str
    level: str
    module: str
    message: str
    timestamp: float
    read: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class NotificationManager:
    """Manages notifications with persistence."""

    def __init__(self, max_notifications: int = 1000):
        self._notifications: deque[Notification] = deque(maxlen=max_notifications)
        self._lock = threading.Lock()
        self._db_path = BASE_DIR / "data" / "notifications.json"
        self._load_from_disk()

    def add_notification(self, level: str, module: str, message: str) -> Notification:
        """Add a new notification."""
        notification = Notification(
            id=f"{int(time.time() * 1000)}_{len(self._notifications)}",
            level=level,
            module=module,
            message=message,
            timestamp=time.time(),
            read=False,
        )
        with self._lock:
            self._notifications.append(notification)
        self._save_to_disk()
        return notification

    def get_notifications(self, unread_only: bool = False) -> list[dict[str, Any]]:
        """Get all notifications, optionally filtered to unread only."""
        with self._lock:
            notifications = list(self._notifications)
        if unread_only:
            notifications = [n for n in notifications if not n.read]
        return [n.to_dict() for n in reversed(notifications)]

    def mark_as_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        found = False
        with self._lock:
            for notification in self._notifications:
                if notification.id == notification_id:
                    notification.read = True
                    found = True
                    break
        if found:
            self._save_to_disk()
        return found

    def mark_all_as_read(self) -> int:
        """Mark all notifications as read."""
        with self._lock:
            count = sum(1 for n in self._notifications if not n.read)
            for notification in self._notifications:
                notification.read = True
        if count > 0:
            self._save_to_disk()
        return count

    def get_unread_count(self) -> int:
        """Get count of unread notifications."""
        with self._lock:
            return sum(1 for n in self._notifications if not n.read)

    def clear_all(self) -> None:
        """Clear all notifications."""
        with self._lock:
            self._notifications.clear()
        self._save_to_disk()

    def _save_to_disk(self) -> None:
        """Save notifications to disk. Must be called without holding self._lock."""
        try:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            with self._lock:
                data = [n.to_dict() for n in self._notifications]
            self._db_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _load_from_disk(self) -> None:
        """Load notifications from disk."""
        try:
            if not self._db_path.exists():
                return
            data = json.loads(self._db_path.read_text(encoding="utf-8"))
            with self._lock:
                for item in data:
                    notification = Notification(
                        id=item.get("id", ""),
                        level=item.get("level", ""),
                        module=item.get("module", ""),
                        message=item.get("message", ""),
                        timestamp=item.get("timestamp", time.time()),
                        read=item.get("read", False),
                    )
                    self._notifications.append(notification)
        except Exception:
            pass


_manager = NotificationManager()


def get_notification_manager() -> NotificationManager:
    """Get the global notification manager instance."""
    return _manager
