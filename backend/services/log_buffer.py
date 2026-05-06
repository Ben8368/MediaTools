"""In-memory application log buffer for the Web UI."""
import logging
import threading
from collections import deque
from datetime import datetime
from typing import Any


class LogBuffer(logging.Handler):
    """Thread-safe log buffer with filtering and pagination."""

    def __init__(self, maxlen: int = 5000):
        super().__init__(level=logging.DEBUG)
        self._records: deque[dict[str, Any]] = deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            entry = {
                "level": record.levelname,
                "module": record.name,
                "time": datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S"),
                "timestamp": record.created,
                "user": getattr(record, "user", "system"),
                "event": getattr(record, "event", msg),
                "message": msg,
            }
            with self._lock:
                self._records.append(entry)
        except Exception:
            pass

    def get_records(
        self,
        level: str = "",
        module: str = "",
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        """Return filtered log records, newest first."""
        page = max(int(page or 1), 1)
        page_size = min(max(int(page_size or 50), 1), 200)
        normalized_level = (level or "").upper()
        normalized_module = (module or "").lower()
        with self._lock:
            records = list(self._records)
        records.reverse()
        if normalized_level:
            records = [r for r in records if r["level"] == normalized_level]
        if normalized_module:
            records = [r for r in records if normalized_module in r["module"].lower()]
        total = len(records)
        start = (page - 1) * page_size
        return {
            "ok": True,
            "total": total,
            "items": records[start : start + page_size],
            "page": page,
            "page_size": page_size,
            "levels": self.get_levels(),
        }

    def get_modules(self) -> list[str]:
        """Return all module names currently present in the buffer."""
        with self._lock:
            modules = {r["module"] for r in self._records}
        return sorted(modules)

    def get_levels(self) -> list[str]:
        with self._lock:
            levels = {r["level"] for r in self._records}
        order = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        return [level for level in order if level in levels]

    def clear(self) -> None:
        """Clear all buffered log records."""
        with self._lock:
            self._records.clear()


_buffer = LogBuffer()


def get_log_buffer() -> LogBuffer:
    """Return the global log buffer instance."""
    return _buffer


def attach_log_buffer(logger: logging.Logger) -> None:
    """Attach the shared buffer to a logger without duplicating handlers."""
    if _buffer not in logger.handlers:
        logger.addHandler(_buffer)
    if logger.level == logging.NOTSET or logger.level > logging.DEBUG:
        logger.setLevel(logging.DEBUG)


def install_log_buffer() -> None:
    """Install the buffer on root and common server loggers."""
    root = logging.getLogger()
    attach_log_buffer(root)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi", "starlette"):
        attach_log_buffer(logging.getLogger(name))
