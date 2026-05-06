"""Runtime management for filebrowser service."""

from __future__ import annotations

import ipaddress
import os
import signal
import subprocess
import time

import requests

from backend.config import (
    BASE_DIR,
    FILEBROWSER_BASE_URL,
    FILEBROWSER_BINARY,
    FILEBROWSER_DB_PATH,
    FILEBROWSER_HOST,
    FILEBROWSER_PORT,
    WORKSPACE_ALLOWED_ROOTS,
)

RUNTIME_DIR = BASE_DIR / "runtime"
FILEBROWSER_PID_FILE = RUNTIME_DIR / "filebrowser.pid"
FILEBROWSER_LOG_FILE = RUNTIME_DIR / "filebrowser.log"
_CREATE_FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def _is_loopback_host(host: str | None) -> bool:
    normalized = (host or "").strip().lower()
    if normalized in {"localhost", "127.0.0.1", "::1"}:
        return True
    if normalized in {"", "0.0.0.0", "::"}:
        return False
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def _ensure_runtime_dir() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def _base_url() -> str:
    return FILEBROWSER_BASE_URL.rstrip("/")


def _health_url() -> str:
    return f"{_base_url()}/health"


def is_filebrowser_running(timeout: float = 1.5) -> bool:
    try:
        resp = requests.get(_health_url(), timeout=timeout)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def _read_pid() -> int | None:
    try:
        return int(FILEBROWSER_PID_FILE.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def _write_pid(pid: int) -> None:
    _ensure_runtime_dir()
    FILEBROWSER_PID_FILE.write_text(str(pid), encoding="utf-8")


def _clear_pid() -> None:
    FILEBROWSER_PID_FILE.unlink(missing_ok=True)


def _process_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _stop_pid(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            creationflags=_CREATE_FLAGS,
        )
        return
    os.kill(pid, signal.SIGTERM)


def get_filebrowser_status() -> dict:
    running = is_filebrowser_running()
    pid = _read_pid()
    root = WORKSPACE_ALLOWED_ROOTS[0] if WORKSPACE_ALLOWED_ROOTS else BASE_DIR
    return {
        "running": running,
        "pid": pid if pid and _process_exists(pid) else None,
        "base_url": FILEBROWSER_BASE_URL,
        "host": FILEBROWSER_HOST,
        "port": FILEBROWSER_PORT,
        "binary": str(FILEBROWSER_BINARY),
        "db_path": str(FILEBROWSER_DB_PATH),
        "root": str(root),
        "log_path": str(FILEBROWSER_LOG_FILE),
    }


def start_filebrowser_service(wait_seconds: float = 8.0) -> dict:
    if is_filebrowser_running():
        return {"ok": True, "message": f"filebrowser 已在运行: {FILEBROWSER_BASE_URL}"}

    if not _is_loopback_host(FILEBROWSER_HOST):
        return {
            "ok": False,
            "message": "filebrowser runs with --noauth and must bind to 127.0.0.1/localhost.",
        }

    if not FILEBROWSER_BINARY.exists():
        return {
            "ok": False,
            "message": f"filebrowser binary 不存在: {FILEBROWSER_BINARY}。请先基于 GitHub 源码构建到 bin/filebrowser.exe",
        }

    _ensure_runtime_dir()
    root = WORKSPACE_ALLOWED_ROOTS[0] if WORKSPACE_ALLOWED_ROOTS else BASE_DIR

    cmd = [
        str(FILEBROWSER_BINARY),
        "--address", FILEBROWSER_HOST,
        "--port", str(FILEBROWSER_PORT),
        "--root", str(root),
        "--database", str(FILEBROWSER_DB_PATH),
        "--noauth",
    ]

    with open(FILEBROWSER_LOG_FILE, "a", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            cmd,
            cwd=str(BASE_DIR),
            stdout=log_file,
            stderr=log_file,
            creationflags=_CREATE_FLAGS,
        )

    _write_pid(process.pid)

    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if is_filebrowser_running(timeout=1.0):
            return {"ok": True, "message": f"filebrowser 启动成功: {FILEBROWSER_BASE_URL} (PID {process.pid})"}
        if process.poll() is not None:
            break
        time.sleep(0.5)

    if process.poll() is not None:
        _clear_pid()
        return {"ok": False, "message": f"filebrowser 启动失败，进程已退出。\n{read_filebrowser_log(20)}"}

    return {"ok": False, "message": f"filebrowser 启动超时，请查看日志。\n{read_filebrowser_log(20)}"}


def stop_filebrowser_service() -> dict:
    pid = _read_pid()
    if pid and _process_exists(pid):
        try:
            _stop_pid(pid)
        except Exception as exc:
            return {"ok": False, "message": f"停止失败: {exc}"}

        deadline = time.time() + 8
        while time.time() < deadline:
            if not is_filebrowser_running(timeout=0.8):
                _clear_pid()
                return {"ok": True, "message": "filebrowser 已停止"}
            time.sleep(0.4)

        _clear_pid()
        return {"ok": False, "message": "已发送停止命令，但服务可能仍未完全退出"}

    # PID 文件不可用时回退到按进程名停止
    if is_filebrowser_running():
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/IM", "filebrowser.exe"],
                capture_output=True, creationflags=_CREATE_FLAGS,
            )
        else:
            subprocess.run(["pkill", "-f", "filebrowser"], capture_output=True)
        _clear_pid()
        return {"ok": True, "message": "filebrowser 已通过进程名停止"}

    _clear_pid()
    return {"ok": True, "message": "filebrowser 当前未运行"}


def restart_filebrowser_service() -> dict:
    stop_filebrowser_service()
    time.sleep(0.6)
    return start_filebrowser_service()


def read_filebrowser_log(lines: int = 40) -> str:
    if not FILEBROWSER_LOG_FILE.exists():
        return "暂无日志"
    try:
        content = FILEBROWSER_LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
        return "\n".join(content[-lines:]) if content else "暂无日志"
    except Exception as exc:
        return f"读取日志失败: {exc}"
