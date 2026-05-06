"""Installed system font discovery."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

_FONT_SUFFIX_RE = re.compile(r"\s+\((?:TrueType|OpenType|Type 1|Raster)\)$", re.IGNORECASE)
_FONT_EXTENSIONS = {".ttf", ".otf", ".ttc", ".fon"}


def _clean_font_name(name: str) -> str:
    return _FONT_SUFFIX_RE.sub("", name).strip()


def _font_dirs() -> list[Path]:
    dirs = []
    if sys.platform.startswith("win"):
        windir = os.environ.get("WINDIR", r"C:\Windows")
        dirs.append(Path(windir) / "Fonts")
        local = os.environ.get("LOCALAPPDATA")
        if local:
            dirs.append(Path(local) / "Microsoft" / "Windows" / "Fonts")
    else:
        home = Path.home()
        dirs.extend([Path("/usr/share/fonts"), Path("/usr/local/share/fonts"), home / ".fonts"])
    return dirs


def _registry_fonts() -> list[dict[str, str]]:
    if not sys.platform.startswith("win"):
        return []
    try:
        import winreg
    except Exception:
        return []

    entries: list[dict[str, str]] = []
    keys = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"),
    ]
    font_dir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    for root, subkey in keys:
        try:
            with winreg.OpenKey(root, subkey) as key:
                for index in range(winreg.QueryInfoKey(key)[1]):
                    try:
                        name, value, _ = winreg.EnumValue(key, index)
                    except OSError:
                        continue
                    raw_path = Path(str(value))
                    path = raw_path if raw_path.is_absolute() else font_dir / raw_path
                    entries.append({"name": _clean_font_name(str(name)), "file": raw_path.name, "path": str(path)})
        except OSError:
            continue
    return entries


def _scanned_fonts() -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for directory in _font_dirs():
        if not directory.exists():
            continue
        try:
            files = directory.glob("*")
        except OSError:
            continue
        for path in files:
            if path.suffix.lower() not in _FONT_EXTENSIONS:
                continue
            entries.append({"name": path.stem, "file": path.name, "path": str(path)})
    return entries


def list_system_fonts(query: str = "", limit: int = 500) -> dict[str, Any]:
    """Return installed fonts from OS metadata with a filesystem fallback."""
    needle = query.strip().lower()
    seen: set[str] = set()
    items: list[dict[str, str]] = []
    for item in [*_registry_fonts(), *_scanned_fonts()]:
        name = _clean_font_name(item.get("name", ""))
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        if needle and needle not in key:
            continue
        seen.add(key)
        items.append({**item, "name": name})

    items.sort(key=lambda row: row["name"].lower())
    if limit > 0:
        items = items[:limit]
    return {"ok": True, "items": items, "count": len(items)}
