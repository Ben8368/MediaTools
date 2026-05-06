"""Runtime helpers for the MediaTools API server."""

from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
import threading
import time
import uuid
from collections.abc import Callable
from typing import Any

from fastapi import Request, WebSocket
from fastapi.responses import JSONResponse

from core.auth import api_key_error
from backend.api.routes.system import build_system_snapshot


def _is_loopback_address(host: str | None) -> bool:
    normalized = (host or "").strip().lower()
    if normalized in {"localhost", "127.0.0.1", "::1", "testclient"}:
        return True
    if normalized in {"", "0.0.0.0", "::"}:
        return False
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def _request_user(request: Request) -> str:
    host = request.client.host if request.client else ""
    return host or "local"


def _resolve_api_secret_key(api_secret_key: str | Callable[[], str]) -> str:
    return api_secret_key() if callable(api_secret_key) else api_secret_key


def build_api_key_middleware(access_logger: logging.Logger, api_secret_key: str | Callable[[], str]):
    async def require_api_key_for_api_routes(request: Request, call_next):
        started = time.perf_counter()
        user = _request_user(request)
        client_host = request.client.host if request.client else ""
        secret_key = _resolve_api_secret_key(api_secret_key)
        if not secret_key and not _is_loopback_address(client_host):
            access_logger.warning(
                "Blocked remote request without API_SECRET_KEY: %s %s from %s",
                request.method,
                request.url.path,
                user,
                extra={"user": user, "event": f"{request.method} {request.url.path} blocked: missing API_SECRET_KEY"},
            )
            return JSONResponse({"ok": False, "error": "Remote access requires API_SECRET_KEY."}, status_code=403)
        if request.url.path.startswith("/api/"):
            error = api_key_error(request.headers.get("X-API-Key", ""), secret_key)
            if error:
                status_code, message = error
                access_logger.warning(
                    "Rejected API request: %s %s %s",
                    request.method,
                    request.url.path,
                    message,
                    extra={"user": user, "event": f"{request.method} {request.url.path} rejected: {message}"},
                )
                return JSONResponse({"ok": False, "error": message}, status_code=status_code)
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - started) * 1000
            access_logger.exception(
                "Unhandled request error: %s %s %.1fms",
                request.method,
                request.url.path,
                elapsed_ms,
                extra={"user": user, "event": f"{request.method} {request.url.path} failed after {elapsed_ms:.1f}ms"},
            )
            raise

        elapsed_ms = (time.perf_counter() - started) * 1000
        log_method = access_logger.warning if response.status_code >= 400 else access_logger.info
        log_method(
            "%s %s -> %s %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            extra={"user": user, "event": f"{request.method} {request.url.path} -> {response.status_code} ({elapsed_ms:.1f}ms)"},
        )
        return response

    return require_api_key_for_api_routes


async def accept_authorized_websocket(
    websocket: WebSocket,
    api_secret_key: str | Callable[[], str],
    is_api_key_valid: Callable[[str, str], bool],
) -> bool:
    client_host = websocket.client.host if websocket.client else ""
    secret_key = _resolve_api_secret_key(api_secret_key)
    if not secret_key and not _is_loopback_address(client_host):
        await websocket.close(code=1008)
        return False
    supplied_key = websocket.headers.get("X-API-Key", "") or websocket.query_params.get("api_key", "")
    if not is_api_key_valid(supplied_key, secret_key):
        await websocket.close(code=1008)
        return False
    await websocket.accept()
    return True


class JobRegistry:
    """Thread-safe job registry with websocket broadcasting."""

    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._ws_clients: list[WebSocket] = []
        self._loop: asyncio.AbstractEventLoop | None = None
        self._cancel_flags: dict[str, threading.Event] = {}

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def register(self, job_id: str, job_type: str, name: str) -> str:
        with self._lock:
            self._jobs[job_id] = {
                "id": job_id,
                "type": job_type,
                "name": name,
                "stage": "waiting",
                "percent": 0.0,
                "status": "pending",
            }
            self._cancel_flags[job_id] = threading.Event()
        self._broadcast()
        return job_id

    def update(self, job_id: str, stage: str, percent: float, status: str = "running") -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update({"stage": stage, "percent": percent, "status": status})
        self._broadcast()

    def finish(self, job_id: str, success: bool = True) -> None:
        with self._lock:
            if job_id in self._jobs:
                current = self._jobs[job_id]
                current.update(
                    {
                        "stage": "completed" if success else "failed",
                        "percent": 100.0 if success else current["percent"],
                        "status": "done" if success else "error",
                    }
                )
            if job_id in self._cancel_flags:
                del self._cancel_flags[job_id]
        self._broadcast()

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            if job_id not in self._jobs:
                return False
            if job_id in self._cancel_flags:
                self._cancel_flags[job_id].set()
            if job_id in self._jobs:
                self._jobs[job_id].update({"stage": "cancelled", "status": "cancelled"})
        self._broadcast()
        return True

    def is_cancelled(self, job_id: str) -> bool:
        with self._lock:
            if job_id in self._cancel_flags:
                return self._cancel_flags[job_id].is_set()
        return False

    def add_ws(self, ws: WebSocket) -> None:
        self._ws_clients.append(ws)

    def remove_ws(self, ws: WebSocket) -> None:
        self._ws_clients = [client for client in self._ws_clients if client is not ws]

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            jobs = list(self._jobs.values())
        return {"jobs": jobs, "system": build_system_snapshot()}

    def _broadcast(self) -> None:
        if not self._loop or not self._ws_clients:
            return
        payload = json.dumps(self.snapshot(), ensure_ascii=False)
        asyncio.run_coroutine_threadsafe(self._async_broadcast(payload), self._loop)

    async def _async_broadcast(self, payload: str) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._ws_clients):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.remove_ws(ws)


def _handle_loop_exception(loop: asyncio.AbstractEventLoop, context: dict[str, Any]) -> None:
    exception = context.get("exception")
    handle = str(context.get("handle", ""))
    if (
        isinstance(exception, ConnectionResetError)
        and getattr(exception, "winerror", None) == 10054
        and "_ProactorBasePipeTransport._call_connection_lost" in handle
    ):
        return
    loop.default_exception_handler(context)


def _result_success(result: Any) -> bool:
    if not isinstance(result, dict):
        return bool(result)
    if "ok" in result:
        return bool(result["ok"])
    if result.get("output_path"):
        return True
    if result.get("output_paths"):
        return bool(result["output_paths"])
    rows = result.get("summary_rows") or []
    if rows and len(rows[0]) > 1:
        return rows[0][1] in {"success", "成功"}
    return True


def build_simple_job_runner(job_registry: JobRegistry):
    async def _run_simple_job(job_type: str, name: str, runner) -> dict[str, Any]:
        job_id = job_registry.register(str(uuid.uuid4()), job_type, name)

        def _wrapped():
            job_registry.update(job_id, "running", 10.0)
            return runner()

        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(None, _wrapped)
        except Exception:
            job_registry.finish(job_id, success=False)
            raise

        job_registry.finish(job_id, success=_result_success(result))
        return result

    return _run_simple_job
