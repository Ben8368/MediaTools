"""Input validation helpers for URLs, filesystem paths, and simple parameters."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class ValidationError(Exception):
    """Raised when user supplied input fails validation."""


def validate_url(url: str, allowed_schemes: list[str] | None = None) -> str:
    """Validate URL shape and scheme."""
    if not url or not isinstance(url, str):
        raise ValidationError("URL cannot be empty")

    url = url.strip()
    if len(url) > 2048:
        raise ValidationError("URL exceeds the 2048 character limit")

    try:
        parsed = urlparse(url)
    except Exception as exc:
        raise ValidationError(f"Invalid URL format: {exc}") from exc

    if not parsed.scheme or not parsed.netloc:
        raise ValidationError("URL must include a scheme and host")

    allowed = allowed_schemes or ["http", "https"]
    if parsed.scheme not in allowed:
        raise ValidationError(f"Unsupported URL scheme: {parsed.scheme}; allowed: {', '.join(allowed)}")

    return url


def validate_file_path(
    path: str,
    must_exist: bool = False,
    allowed_extensions: list[str] | None = None,
    base_dir: Path | None = None,
) -> Path:
    """Validate a filesystem path, optionally restricting it to a base directory."""
    if not path or not isinstance(path, str):
        raise ValidationError("Path cannot be empty")

    try:
        raw_path = Path(path).expanduser()
        resolved_base = Path(base_dir).expanduser().resolve() if base_dir else None
        file_path = (raw_path if raw_path.is_absolute() else (resolved_base or Path.cwd()) / raw_path).resolve()
    except Exception as exc:
        raise ValidationError(f"Invalid path format: {exc}") from exc

    if resolved_base:
        try:
            file_path.relative_to(resolved_base)
        except ValueError as exc:
            raise ValidationError(f"Path must be inside {resolved_base}") from exc

    if must_exist and not file_path.exists():
        raise ValidationError(f"File does not exist: {file_path}")

    if allowed_extensions:
        ext = file_path.suffix.lower()
        allowed = [item.lower() for item in allowed_extensions]
        if ext not in allowed:
            raise ValidationError(f"Unsupported file type: {ext}; allowed: {', '.join(allowed_extensions)}")

    return file_path


def validate_timestamp(timestamp: str) -> str:
    """Validate HH:MM:SS, MM:SS, or plain seconds timestamp strings."""
    if not timestamp or not isinstance(timestamp, str):
        raise ValidationError("Timestamp cannot be empty")

    timestamp = timestamp.strip()
    if ":" in timestamp:
        match = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", timestamp)
        if not match:
            raise ValidationError("Timestamp must be HH:MM:SS or MM:SS")

        _hours, minutes, seconds = match.groups()
        minutes_int = int(minutes)
        if seconds:
            seconds_int = int(seconds)
            if minutes_int >= 60 or seconds_int >= 60:
                raise ValidationError("Minutes and seconds must be less than 60")
        elif minutes_int >= 60:
            raise ValidationError("Minutes must be less than 60")

        return timestamp

    try:
        seconds_value = float(timestamp)
    except ValueError as exc:
        raise ValidationError("Timestamp must be HH:MM:SS, MM:SS, or seconds") from exc

    if seconds_value < 0:
        raise ValidationError("Timestamp cannot be negative")
    return timestamp


def validate_integer(
    value: Any,
    min_value: int | None = None,
    max_value: int | None = None,
    name: str = "value",
) -> int:
    """Validate an integer parameter with optional inclusive bounds."""
    try:
        int_value = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{name} must be an integer") from exc

    if min_value is not None and int_value < min_value:
        raise ValidationError(f"{name} must be at least {min_value}")
    if max_value is not None and int_value > max_value:
        raise ValidationError(f"{name} must be at most {max_value}")

    return int_value


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """Remove unsafe filename characters and enforce a maximum length."""
    if not filename:
        return "unnamed"

    safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", filename)
    safe_name = safe_name.strip(". ")

    if len(safe_name) > max_length:
        name, ext = safe_name.rsplit(".", 1) if "." in safe_name else (safe_name, "")
        max_name_len = max_length - len(ext) - 1 if ext else max_length
        safe_name = f"{name[:max_name_len]}.{ext}" if ext else name[:max_length]

    return safe_name or "unnamed"
