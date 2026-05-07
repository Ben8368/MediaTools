"""MediaTools FastAPI application and legacy websocket/front-end endpoints."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import threading
import time
from contextlib import asynccontextmanager
from typing import Any

import requests
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from backend.config import (
    API_SECRET_KEY,
    ASSET_SCAN_MAX_FILES,
    BASE_DIR,
    CORS_ALLOWED_ORIGINS,
    PREVIEW_MAX_BYTES,
    get_api_config,
)
from core.auth import is_api_key_valid
from modules.assets import AssetLibrary, FileManager, PreviewGenerator, extract_icon
from backend.api.models import AgentChatBody, AgentTestConnectionBody
from backend.api.runtime import (
    JobRegistry,
    _handle_loop_exception,
    _is_loopback_address,
    _result_success,
    accept_authorized_websocket,
    build_api_key_middleware,
    build_simple_job_runner,
)
from backend.api.setup import configure_application_routes
from backend.services.auditor import get_auditor_config, get_auditor_status, run_auditor_scan_once, save_auditor_config
from backend.services.decryptor import run_decrypt_job
from backend.services.encoder import run_transcode_job
from backend.services.fetcher import run_fetch_batch_stream
from backend.services.path_picker import resolve_allowed_path
from backend.services.photoshop import (
    cancel_execution as cancel_photoshop_execution,
)
from backend.services.photoshop import (
    get_execution_state as get_photoshop_execution_state,
)
from backend.services.photoshop import (
    get_photoshop_status,
    get_photoshop_ticket,
    list_photoshop_tickets,
    save_photoshop_ticket,
    scan_photoshop_document,
    start_ticket_execution,
)
from backend.services.wechat_moments import (
    export_wechat_moments_image,
    get_wechat_moments_draft,
    get_wechat_moments_status,
    save_wechat_moments_draft,
)
from backend.services.workbench import analyze_subtitle_for_workbench, export_clips_from_workbench, list_workspace_media
from backend.services.workspace import get_current_workspace, set_current_workspace

FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
FRONTEND_DEV_SERVER = (os.environ.get("MEDIATOOLS_FRONTEND_DEV_URL") or "").rstrip("/")

app = FastAPI(
    title="MediaTools API",
    version="1.0.0",
    description="""
    MediaTools 是一个面向内容创作场景的本地媒体工作台。

    ## 主要功能

    - **媒体获取**: 视频下载、字幕获取（YouTube + 多平台）
    - **媒体处理**: FFmpeg 转码、音频提取、视频切片
    - **音乐解密**: 加密音乐文件解密（NCM, QMC 等格式）
    - **素材管理**: 工作区素材扫描、搜索、预览
    - **AI 助手**: 字幕分析、亮点提取、自动切片
    - **工作台**: 剪辑工作流、批量导出
    - **Photoshop 自动化**: PSD 批量处理

    ## 认证

    如果服务绑定到非本地地址，需要在请求头中提供 `X-API-Key`。

    ## WebSocket

    部分功能支持 WebSocket 实时通信，用于流式输出和进度更新。
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "workspace", "description": "工作区管理"},
        {"name": "media", "description": "媒体获取与处理"},
        {"name": "agent", "description": "AI 助手"},
        {"name": "assets", "description": "素材管理"},
        {"name": "workbench", "description": "剪辑工作台"},
        {"name": "photoshop", "description": "Photoshop 自动化"},
        {"name": "system", "description": "系统信息"},
    ],
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[*CORS_ALLOWED_ORIGINS, "null"],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$",
    allow_methods=["*"],
    allow_headers=["*"],
)

access_logger = logging.getLogger("api.access")
app.middleware("http")(build_api_key_middleware(access_logger, lambda: API_SECRET_KEY))


async def _accept_authorized_websocket(websocket: WebSocket) -> bool:
    return await accept_authorized_websocket(websocket, lambda: API_SECRET_KEY, is_api_key_valid)


job_registry = JobRegistry()
file_manager: FileManager | None = None
preview_generator = PreviewGenerator()


@asynccontextmanager
async def _lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    loop.set_exception_handler(_handle_loop_exception)
    job_registry.set_loop(loop)
    yield


app.router.lifespan_context = _lifespan
_run_simple_job = build_simple_job_runner(job_registry)


def _get_file_manager() -> FileManager:
    if file_manager is not None:
        return file_manager
    return FileManager(get_current_workspace()["project_root"])


async def _proxy_frontend_dev_request(request: Request, full_path: str) -> Response:
    target = f"{FRONTEND_DEV_SERVER}/{full_path}" if full_path else f"{FRONTEND_DEV_SERVER}/"
    if request.url.query:
        target = f"{target}?{request.url.query}"

    headers = {key: value for key, value in request.headers.items() if key.lower() not in {"host", "content-length", "connection"}}

    def _send() -> requests.Response:
        return requests.request(request.method, target, headers=headers, timeout=10, allow_redirects=False)

    try:
        upstream = await asyncio.to_thread(_send)
    except requests.RequestException as exc:
        return JSONResponse({"ok": False, "error": f"frontend dev server unavailable: {exc}"}, status_code=502)

    excluded_headers = {"connection", "content-encoding", "content-length", "transfer-encoding"}
    response_headers = {key: value for key, value in upstream.headers.items() if key.lower() not in excluded_headers}
    body = b"" if request.method == "HEAD" else upstream.content
    return Response(content=body, status_code=upstream.status_code, headers=response_headers)


@app.post("/api/agent/chat")
async def agent_chat(body: AgentChatBody):
    """Run an Agent task in a worker thread."""
    from backend.agent.service import MediaAgentService

    def _run() -> dict[str, Any]:
        cfg = get_api_config()
        svc = MediaAgentService(
            api_key=body.api_key or cfg["api_key"],
            base_url=body.base_url or cfg["api_base_url"],
            model=body.model or cfg["analysis_model"],
        )
        return svc.execute(body.task, body.extra_context)

    loop = asyncio.get_running_loop()
    try:
        return JSONResponse(await loop.run_in_executor(None, _run))
    except Exception as exc:
        return JSONResponse(
            {
                "ok": False,
                "answer": str(exc),
                "tool_trace_text": "Agent execution failed before a structured result was produced.",
                "actions": [],
                "artifacts": [],
            },
            status_code=200,
        )


@app.post("/api/agent/test-connection")
async def agent_test_connection(body: AgentTestConnectionBody):
    """Test LLM connectivity with optional config override."""
    from backend.agent.service import MediaAgentService

    def _run() -> dict[str, Any]:
        cfg = get_api_config()
        svc = MediaAgentService(
            api_key=body.api_key or cfg["api_key"],
            base_url=body.base_url or cfg["api_base_url"],
            model=body.model or cfg["analysis_model"],
        )
        return svc.test_connection()

    loop = asyncio.get_running_loop()
    try:
        return JSONResponse(await loop.run_in_executor(None, _run))
    except Exception as exc:
        return JSONResponse({"ok": False, "message": str(exc)}, status_code=200)


@app.websocket("/ws/jobs")
async def ws_jobs(websocket: WebSocket):
    """Stream job progress over websocket."""
    if not await _accept_authorized_websocket(websocket):
        return
    job_registry.add_ws(websocket)
    try:
        await websocket.send_text(json.dumps(job_registry.snapshot(), ensure_ascii=False))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        job_registry.remove_ws(websocket)


@app.post("/api/jobs/cancel/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a running job."""
    success = job_registry.cancel(job_id)
    if success:
        return JSONResponse({"ok": True, "message": "cancelled"})
    return JSONResponse({"ok": False, "error": "job not found or already finished"}, status_code=404)


@app.post("/api/system/shutdown")
async def shutdown_server(request: Request):
    """Gracefully shutdown the server. Only allowed from loopback addresses."""
    client_host = request.client.host if request.client else ""
    if not _is_loopback_address(client_host):
        return JSONResponse({"ok": False, "error": "shutdown only allowed from localhost"}, status_code=403)

    def _delayed_shutdown():
        time.sleep(0.5)
        # Use os._exit(0) to force immediate exit
        # This ensures the process terminates and releases the port
        os._exit(0)

    threading.Thread(target=_delayed_shutdown, daemon=True).start()
    return JSONResponse({"ok": True, "message": "server shutting down"})


@app.post("/api/system/restart")
async def restart_server(request: Request):
    """Restart the server. Triggers file change to activate --reload in dev mode,
    or uses watchdog restart in production mode."""
    client_host = request.client.host if request.client else ""
    if not _is_loopback_address(client_host):
        return JSONResponse({"ok": False, "error": "restart only allowed from localhost"}, status_code=403)

    def _delayed_restart():
        time.sleep(0.5)
        # Trigger file change to cause reload in dev mode
        restart_trigger = BASE_DIR / "runtime" / ".restart_trigger"
        restart_trigger.parent.mkdir(exist_ok=True)
        restart_trigger.write_text(str(time.time()))

        # Check if running under reloader (parent is also python)
        parent_pid = os.getppid()
        try:
            import psutil
            parent = psutil.Process(parent_pid)
            parent_name = parent.name().lower()
            if 'python' in parent_name:
                # In reload mode: file change will trigger restart automatically
                # Terminate parent to let uvicorn reloader restart it
                parent.terminate()
                try:
                    parent.wait(timeout=3)
                except psutil.TimeoutExpired:
                    parent.kill()
                return
        except Exception as e:
            logging.debug(f"Failed to check parent process: {e}")

        # Not in reload mode: exit with code 3 to signal restart to watchdog
        # Use os._exit to force immediate termination
        os._exit(3)

    threading.Thread(target=_delayed_restart, daemon=True).start()
    return JSONResponse({"ok": True, "message": "server restarting"})


configure_application_routes(
    app,
    job_registry=job_registry,
    run_simple_job=_run_simple_job,
    get_file_manager=_get_file_manager,
    get_current_workspace=lambda: get_current_workspace(),
    set_current_workspace=lambda *args, **kwargs: set_current_workspace(*args, **kwargs),
    get_auditor_status=lambda *args, **kwargs: get_auditor_status(*args, **kwargs),
    get_auditor_config=lambda *args, **kwargs: get_auditor_config(*args, **kwargs),
    run_auditor_scan_once=lambda *args, **kwargs: run_auditor_scan_once(*args, **kwargs),
    save_auditor_config=lambda *args, **kwargs: save_auditor_config(*args, **kwargs),
    get_wechat_moments_draft=lambda *args, **kwargs: get_wechat_moments_draft(*args, **kwargs),
    get_wechat_moments_status=lambda *args, **kwargs: get_wechat_moments_status(*args, **kwargs),
    save_wechat_moments_draft=lambda *args, **kwargs: save_wechat_moments_draft(*args, **kwargs),
    export_wechat_moments_image=lambda *args, **kwargs: export_wechat_moments_image(*args, **kwargs),
    get_photoshop_status=lambda *args, **kwargs: get_photoshop_status(*args, **kwargs),
    scan_photoshop_document=lambda *args, **kwargs: scan_photoshop_document(*args, **kwargs),
    list_photoshop_tickets=lambda *args, **kwargs: list_photoshop_tickets(*args, **kwargs),
    get_photoshop_ticket=lambda *args, **kwargs: get_photoshop_ticket(*args, **kwargs),
    save_photoshop_ticket=lambda *args, **kwargs: save_photoshop_ticket(*args, **kwargs),
    start_ticket_execution=lambda *args, **kwargs: start_ticket_execution(*args, **kwargs),
    get_photoshop_execution_state=lambda *args, **kwargs: get_photoshop_execution_state(*args, **kwargs),
    cancel_photoshop_execution=lambda *args, **kwargs: cancel_photoshop_execution(*args, **kwargs),
    get_preview_generator=lambda: preview_generator,
    get_preview_max_bytes=lambda: PREVIEW_MAX_BYTES,
    extract_icon=extract_icon,
    resolve_allowed_path=lambda *args, **kwargs: resolve_allowed_path(*args, **kwargs),
    run_fetch_batch_stream=lambda *args, **kwargs: run_fetch_batch_stream(*args, **kwargs),
    run_transcode_job=lambda *args, **kwargs: run_transcode_job(*args, **kwargs),
    run_decrypt_job=lambda *args, **kwargs: run_decrypt_job(*args, **kwargs),
    result_success=_result_success,
    asset_library_cls=AssetLibrary,
    get_asset_scan_max_files=lambda: ASSET_SCAN_MAX_FILES,
    list_workspace_media=lambda *args, **kwargs: list_workspace_media(*args, **kwargs),
    analyze_subtitle_for_workbench=lambda *args, **kwargs: analyze_subtitle_for_workbench(*args, **kwargs),
    export_clips_from_workbench=lambda *args, **kwargs: export_clips_from_workbench(*args, **kwargs),
)


@app.websocket("/ws/agent")
async def ws_agent(websocket: WebSocket):
    """Legacy Agent websocket endpoint."""
    if not await _accept_authorized_websocket(websocket):
        return
    try:
        raw = await websocket.receive_text()
        body = json.loads(raw)
        task = body.get("task", "")
        extra_context = body.get("extra_context", "")

        from backend.agent.service import MediaAgentService

        def _run():
            svc = MediaAgentService(
                api_key=body.get("api_key") or API_KEY,
                base_url=body.get("base_url") or API_BASE_URL,
                model=body.get("model") or ANALYSIS_MODEL,
            )
            return svc.execute(task, extra_context)

        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(None, _run)
        except Exception as exc:
            result = {
                "ok": False,
                "answer": str(exc),
                "tool_trace_text": "Agent execution failed before a structured result was produced.",
                "actions": [],
                "artifacts": [],
            }
        await websocket.send_text(json.dumps(result, ensure_ascii=False))
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_text(json.dumps({"ok": False, "answer": str(exc)}, ensure_ascii=False))
        except Exception:
            pass


if FRONTEND_DEV_SERVER:

    @app.get("/{full_path:path}")
    @app.head("/{full_path:path}")
    async def serve_frontend_dev(request: Request, full_path: str):
        return await _proxy_frontend_dev_request(request, full_path)

elif (FRONTEND_DIST / "index.html").exists():
    frontend_assets_dir = FRONTEND_DIST / "assets"
    if frontend_assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(frontend_assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(FRONTEND_DIST / "index.html"))

else:

    @app.get("/")
    async def dev_placeholder():
        return JSONResponse(
            {
                "message": "MediaTools API running",
                "note": "Frontend has not been built. Run: cd frontend && npm run build",
                "api_docs": "/docs",
            }
        )
