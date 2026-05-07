"""Runtime controls for the optional filebrowser process."""

from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

import requests

from backend.config import (
    BASE_DIR,
    FILEBROWSER_BASE_URL,
    FILEBROWSER_BINARY,
    FILEBROWSER_DB_PATH,
    FILEBROWSER_ENABLED,
    FILEBROWSER_HOST,
    FILEBROWSER_PORT,
    WORKSPACE_ALLOWED_ROOTS,
)

RUNTIME_DIR = BASE_DIR / "runtime"
FILEBROWSER_PID_FILE = RUNTIME_DIR / "filebrowser.pid"
FILEBROWSER_LOG_FILE = RUNTIME_DIR / "filebrowser.log"


def _is_loopback_host(host: str) -> bool:
    normalized = (host or "").strip().lower()
    return normalized in {"127.0.0.1", "localhost", "::1"}


def _base_url() -> str:
    return FILEBROWSER_BASE_URL.rstrip("/")


def _health_url() -> str:
    return f"{_base_url()}/health"


def _workspace_root() -> Path:
    for root in WORKSPACE_ALLOWED_ROOTS:
        if root:
            return Path(root)
    return BASE_DIR / "projects"


def _read_pid() -> int | None:
    try:
        return int(FILEBROWSER_PID_FILE.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _write_pid(pid: int) -> None:
    FILEBROWSER_PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    FILEBROWSER_PID_FILE.write_text(str(pid), encoding="utf-8")


def _clear_pid() -> None:
    try:
        FILEBROWSER_PID_FILE.unlink()
    except FileNotFoundError:
        pass


def _process_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _stop_pid(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, check=True)
        return
    os.kill(pid, signal.SIGTERM)


def is_filebrowser_running(timeout: float = 0.5) -> bool:
    try:
        return requests.get(_health_url(), timeout=timeout).status_code < 500
    except requests.RequestException:
        return False


def get_filebrowser_status() -> dict[str, Any]:
    pid = _read_pid()
    process_alive = bool(pid and _process_exists(pid))
    running = is_filebrowser_running()
    if pid and not process_alive and not running:
        _clear_pid()
        pid = None

    return {
        "enabled": FILEBROWSER_ENABLED,
        "running": running,
        "pid": pid if process_alive or running else None,
        "host": FILEBROWSER_HOST,
        "port": FILEBROWSER_PORT,
        "url": _base_url(),
        "root": str(_workspace_root()),
        "binary": str(FILEBROWSER_BINARY),
        "binary_exists": FILEBROWSER_BINARY.exists(),
        "database": str(FILEBROWSER_DB_PATH),
        "log_file": str(FILEBROWSER_LOG_FILE),
    }


def _start_command(root: Path) -> list[str]:
    return [
        str(FILEBROWSER_BINARY),
        "--address",
        FILEBROWSER_HOST,
        "--port",
        str(FILEBROWSER_PORT),
        "--database",
        str(FILEBROWSER_DB_PATH),
        "--root",
        str(root),
        "--noauth",
    ]


def start_filebrowser_service(wait_seconds: int = 8) -> dict[str, Any]:
    if is_filebrowser_running():
        return {"ok": True, "message": "filebrowser 已在运行", **get_filebrowser_status()}
    if not _is_loopback_host(FILEBROWSER_HOST):
        return {"ok": False, "message": "filebrowser 只能绑定到 127.0.0.1 或 localhost"}
    if not FILEBROWSER_BINARY.exists():
        return {"ok": False, "message": f"filebrowser binary not found: {FILEBROWSER_BINARY}"}

    root = _workspace_root()
    root.mkdir(parents=True, exist_ok=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    FILEBROWSER_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    FILEBROWSER_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    log_handle = FILEBROWSER_LOG_FILE.open("a", encoding="utf-8")
    try:
        process = subprocess.Popen(
            _start_command(root),
            cwd=str(BASE_DIR),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    finally:
        log_handle.close()

    _write_pid(process.pid)
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if process.poll() is not None:
            _clear_pid()
            return {"ok": False, "message": f"filebrowser 进程已退出，退出码: {process.poll()}"}
        if is_filebrowser_running():
            return {"ok": True, "message": f"filebrowser 已启动，PID {process.pid}", **get_filebrowser_status()}
        time.sleep(0.5)

    if process.poll() is not None:
        _clear_pid()
        return {"ok": False, "message": f"filebrowser 进程已退出，退出码: {process.poll()}"}
    return {"ok": False, "message": "filebrowser 启动超时", "pid": process.pid, "log_file": str(FILEBROWSER_LOG_FILE)}


def stop_filebrowser_service(wait_seconds: int = 8) -> dict[str, Any]:
    pid = _read_pid()
    if pid and _process_exists(pid):
        try:
            _stop_pid(pid)
        except Exception as exc:
            return {"ok": False, "message": f"停止 filebrowser 失败: {exc}"}
    elif is_filebrowser_running():
        subprocess.run(["taskkill", "/IM", "filebrowser.exe", "/T", "/F"], capture_output=True, check=False)
    else:
        _clear_pid()
        return {"ok": True, "message": "filebrowser 当前未运行"}

    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if not is_filebrowser_running():
            _clear_pid()
            return {"ok": True, "message": "filebrowser 已停止"}
        time.sleep(0.5)

    _clear_pid()
    return {"ok": False, "message": "filebrowser 可能仍未完全退出"}


def restart_filebrowser_service() -> dict[str, Any]:
    stopped = stop_filebrowser_service()
    if not stopped.get("ok"):
        return stopped
    time.sleep(1)
    return start_filebrowser_service()


def read_filebrowser_log(lines: int = 40) -> str:
    try:
        if not FILEBROWSER_LOG_FILE.exists():
            return "暂无日志"
        content = FILEBROWSER_LOG_FILE.read_text(encoding="utf-8", errors="replace").strip()
    except OSError as exc:
        return f"读取日志失败: {exc}"
    if not content:
        return "暂无日志"
    return "\n".join(content.splitlines()[-max(lines, 1) :])
