"""Runtime management for the capcut-mate service."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time

import requests

from config import BASE_DIR, CAPCUT_MATE_BASE_URL

RUNTIME_DIR = BASE_DIR / "runtime"
CAPCUT_PID_FILE = RUNTIME_DIR / "capcut-mate.pid"
CAPCUT_LOG_FILE = RUNTIME_DIR / "capcut-mate.log"
CAPCUT_WORKDIR = BASE_DIR / "vendor" / "capcut-mate"

_CREATE_FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def _ensure_runtime_dir() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def _base_url() -> str:
    return CAPCUT_MATE_BASE_URL.rstrip("/")


def is_capcut_running(timeout: float = 1.5) -> bool:
    try:
        resp = requests.get(f"{_base_url()}/docs", timeout=timeout)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def _read_pid() -> int | None:
    try:
        return int(CAPCUT_PID_FILE.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def _write_pid(pid: int) -> None:
    _ensure_runtime_dir()
    CAPCUT_PID_FILE.write_text(str(pid), encoding="utf-8")


def _clear_pid() -> None:
    CAPCUT_PID_FILE.unlink(missing_ok=True)


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
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15, creationflags=_CREATE_FLAGS)
    else:
        os.kill(pid, signal.SIGTERM)


def get_capcut_status() -> dict:
    running = is_capcut_running()
    pid = _read_pid()
    return {
        "running": running,
        "pid": pid if pid and _process_exists(pid) else None,
        "base_url": CAPCUT_MATE_BASE_URL,
        "workdir": str(CAPCUT_WORKDIR),
        "log_path": str(CAPCUT_LOG_FILE),
    }


def start_capcut_service(wait_seconds: float = 8.0) -> dict:
    if is_capcut_running():
        return {"ok": True, "message": f"capcut-mate 已在运行: {CAPCUT_MATE_BASE_URL}"}

    if not CAPCUT_WORKDIR.exists():
        return {"ok": False, "message": f"capcut-mate 目录不存在: {CAPCUT_WORKDIR}"}

    _ensure_runtime_dir()

    # 从 CAPCUT_MATE_BASE_URL 解析端口
    from urllib.parse import urlparse
    parsed = urlparse(CAPCUT_MATE_BASE_URL)
    port = str(parsed.port or 30000)

    with open(CAPCUT_LOG_FILE, "a", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", port],
            cwd=str(CAPCUT_WORKDIR),
            stdout=log_file,
            stderr=log_file,
            creationflags=_CREATE_FLAGS,
        )

    _write_pid(process.pid)

    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if is_capcut_running(timeout=1.0):
            return {"ok": True, "message": f"capcut-mate 启动成功: {CAPCUT_MATE_BASE_URL} (PID {process.pid})"}
        if process.poll() is not None:
            break
        time.sleep(0.5)

    if process.poll() is not None:
        _clear_pid()
        return {"ok": False, "message": f"capcut-mate 启动失败，进程已退出。\n{read_capcut_log(20)}"}

    return {"ok": False, "message": f"capcut-mate 启动超时，请查看日志。\n{read_capcut_log(20)}"}


def stop_capcut_service() -> dict:
    pid = _read_pid()
    if pid and _process_exists(pid):
        try:
            _stop_pid(pid)
        except Exception as exc:
            return {"ok": False, "message": f"停止失败: {exc}"}

        deadline = time.time() + 8
        while time.time() < deadline:
            if not is_capcut_running(timeout=0.8) and not _process_exists(pid):
                _clear_pid()
                return {"ok": True, "message": "capcut-mate 已停止"}
            time.sleep(0.4)

        _clear_pid()
        return {"ok": False, "message": "已发送停止命令，但服务可能仍未完全退出"}

    if is_capcut_running():
        return {"ok": False, "message": "检测到服务仍在运行，但没有可管理的 PID。请手动停止或使用强制刷新检查状态。"}

    _clear_pid()
    return {"ok": True, "message": "capcut-mate 当前未运行"}


def restart_capcut_service() -> dict:
    stop_capcut_service()
    time.sleep(0.6)
    return start_capcut_service()


def read_capcut_log(lines: int = 40) -> str:
    if not CAPCUT_LOG_FILE.exists():
        return "暂无日志"
    try:
        content = CAPCUT_LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
        return "\n".join(content[-lines:]) if content else "暂无日志"
    except Exception as exc:
        return f"读取日志失败: {exc}"


def ensure_capcut_service_started() -> dict:
    if is_capcut_running():
        return {"ok": True, "message": f"capcut-mate 已运行: {CAPCUT_MATE_BASE_URL}"}
    return start_capcut_service()
