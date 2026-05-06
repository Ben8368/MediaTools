"""Tests for API server runtime helpers."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.responses import JSONResponse

from services.api_server_runtime import (
    JobRegistry,
    _is_loopback_address,
    accept_authorized_websocket,
    build_api_key_middleware,
    build_simple_job_runner,
)


def _request(path: str, *, host: str = "127.0.0.1", api_key: str = ""):
    return SimpleNamespace(
        client=SimpleNamespace(host=host),
        headers={"X-API-Key": api_key},
        method="GET",
        url=SimpleNamespace(path=path),
    )


def test_loopback_address_detection_handles_common_and_invalid_hosts():
    assert _is_loopback_address("localhost") is True
    assert _is_loopback_address("127.0.0.1") is True
    assert _is_loopback_address("::1") is True
    assert _is_loopback_address("testclient") is True
    assert _is_loopback_address("0.0.0.0") is False
    assert _is_loopback_address("") is False
    assert _is_loopback_address("not a host") is False


def test_api_key_middleware_blocks_remote_requests_without_secret():
    logger = Mock()
    middleware = build_api_key_middleware(logger, "")

    async def call_next(request):
        raise AssertionError("call_next should not run")

    response = asyncio.run(middleware(_request("/api/system/status", host="192.168.1.2"), call_next))

    assert response.status_code == 403
    assert b"Remote access requires API_SECRET_KEY" in response.body
    logger.warning.assert_called_once()


def test_api_key_middleware_rejects_invalid_api_key():
    logger = Mock()
    middleware = build_api_key_middleware(logger, lambda: "secret")

    async def call_next(request):
        raise AssertionError("call_next should not run")

    response = asyncio.run(middleware(_request("/api/system/status", api_key="bad"), call_next))

    assert response.status_code == 403
    assert b"Invalid API key" in response.body
    logger.warning.assert_called_once()


def test_api_key_middleware_logs_success_and_failures():
    logger = Mock()
    middleware = build_api_key_middleware(logger, "secret")

    async def ok_call_next(request):
        return JSONResponse({"ok": True}, status_code=201)

    response = asyncio.run(middleware(_request("/api/system/status", api_key="secret"), ok_call_next))
    assert response.status_code == 201
    logger.info.assert_called_once()

    async def broken_call_next(request):
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(middleware(_request("/assets/app.js", api_key=""), broken_call_next))
    logger.exception.assert_called_once()


def test_websocket_authorization_accepts_key_header_or_query_param():
    websocket = SimpleNamespace(
        client=SimpleNamespace(host="127.0.0.1"),
        headers={"X-API-Key": "secret"},
        query_params={},
        accept=AsyncMock(),
        close=AsyncMock(),
    )

    accepted = asyncio.run(accept_authorized_websocket(websocket, "secret", lambda supplied, expected: supplied == expected))

    assert accepted is True
    websocket.accept.assert_awaited_once()
    websocket.close.assert_not_awaited()

    query_websocket = SimpleNamespace(
        client=SimpleNamespace(host="127.0.0.1"),
        headers={},
        query_params={"api_key": "secret"},
        accept=AsyncMock(),
        close=AsyncMock(),
    )
    accepted = asyncio.run(
        accept_authorized_websocket(query_websocket, "secret", lambda supplied, expected: supplied == expected)
    )
    assert accepted is True
    query_websocket.accept.assert_awaited_once()


def test_websocket_authorization_rejects_remote_without_secret_and_bad_key():
    remote_websocket = SimpleNamespace(
        client=SimpleNamespace(host="10.0.0.5"),
        headers={},
        query_params={},
        accept=AsyncMock(),
        close=AsyncMock(),
    )

    accepted = asyncio.run(accept_authorized_websocket(remote_websocket, "", lambda supplied, expected: True))

    assert accepted is False
    remote_websocket.close.assert_awaited_once_with(code=1008)
    remote_websocket.accept.assert_not_awaited()

    bad_key_websocket = SimpleNamespace(
        client=SimpleNamespace(host="127.0.0.1"),
        headers={"X-API-Key": "bad"},
        query_params={},
        accept=AsyncMock(),
        close=AsyncMock(),
    )
    accepted = asyncio.run(
        accept_authorized_websocket(bad_key_websocket, "secret", lambda supplied, expected: supplied == expected)
    )
    assert accepted is False
    bad_key_websocket.close.assert_awaited_once_with(code=1008)


def test_job_registry_cancel_and_async_broadcast_removes_dead_clients(monkeypatch):
    registry = JobRegistry()
    registry.register("job-1", "download", "Download")

    assert registry.cancel("missing") is False
    assert registry.cancel("job-1") is True
    assert registry.is_cancelled("job-1") is True
    assert registry.snapshot()["jobs"][0]["status"] == "cancelled"

    live = SimpleNamespace(send_text=AsyncMock())
    dead = SimpleNamespace(send_text=AsyncMock(side_effect=RuntimeError("closed")))
    registry.add_ws(live)
    registry.add_ws(dead)

    asyncio.run(registry._async_broadcast("{}"))

    live.send_text.assert_awaited_once_with("{}")
    dead.send_text.assert_awaited_once_with("{}")
    assert dead not in registry._ws_clients
    assert live in registry._ws_clients

    loop = Mock()
    registry.set_loop(loop)

    def close_scheduled_coroutine(coro, loop):
        coro.close()

    with patch(
        "services.api_server_runtime.asyncio.run_coroutine_threadsafe",
        side_effect=close_scheduled_coroutine,
    ) as run_threadsafe:
        registry.update("job-1", "again", 50)
    run_threadsafe.assert_called_once()


def test_simple_job_runner_finishes_success_and_failure():
    async def run_success():
        registry = JobRegistry()
        runner = build_simple_job_runner(registry)
        result = await runner("download", "Download", lambda: {"ok": True})
        return result, registry.snapshot()["jobs"][0]

    result, job = asyncio.run(run_success())
    assert result == {"ok": True}
    assert job["status"] == "done"
    assert job["percent"] == 100.0

    async def run_failure():
        registry = JobRegistry()
        runner = build_simple_job_runner(registry)

        def fail():
            raise ValueError("bad job")

        with pytest.raises(ValueError, match="bad job"):
            await runner("download", "Download", fail)
        return registry.snapshot()["jobs"][0]

    failed_job = asyncio.run(run_failure())
    assert failed_job["status"] == "error"
