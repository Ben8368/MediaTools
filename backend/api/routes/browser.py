"""Browser session API routes."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from backend.services.browser_manager import browser_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/browser", tags=["browser"])


@router.post("/session")
async def create_browser_session(body: dict[str, Any] | None = None):
    """Create a new browser session."""
    if body is None:
        body = {}
    url = body.get("url", "https://chatgpt.com")
    browser_type = body.get("browser_type", "chrome")
    width = body.get("width", 1280)
    height = body.get("height", 720)
    
    try:
        session = await browser_manager.create_session(url, browser_type, width, height)
        return JSONResponse({
            "ok": True,
            "session_id": session.session_id,
            "browser_type": session.browser_type,
            "browser_exe": session.browser_exe,
            "cdp_port": session.cdp_port,
            "cdp_url": session.cdp_url,
            "url": session.url,
        })
    except Exception as e:
        logger.error(f"Failed to create browser session: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.get("/session/{session_id}")
async def get_browser_session(session_id: str):
    """Get session info."""
    session = await browser_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return JSONResponse({
        "ok": True,
        "session_id": session.session_id,
        "url": session.url,
        "cdp_port": session.cdp_port,
        "cdp_url": session.cdp_url,
    })


@router.get("/session/{session_id}/cookies")
async def get_session_cookies(session_id: str):
    """Get cookies from a browser session."""
    session = await browser_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        cookies = await session.get_cookies()
        return JSONResponse({
            "ok": True,
            "cookies": cookies,
            "cookie_count": len(cookies),
        })
    except Exception as e:
        logger.error(f"Failed to get cookies: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.delete("/session/{session_id}")
async def close_browser_session(session_id: str):
    """Close a browser session."""
    success = await browser_manager.close_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return JSONResponse({"ok": True, "message": "Session closed"})


@router.get("/sessions")
async def list_browser_sessions():
    """List all active browser sessions."""
    sessions = browser_manager.list_sessions()
    return JSONResponse({
        "ok": True,
        "sessions": sessions,
        "count": len(sessions),
    })


@router.get("/status")
async def get_browser_status():
    """Get supported browser availability and session status."""
    return JSONResponse({
        "ok": True,
        "browsers": browser_manager.get_browser_statuses(),
    })


@router.websocket("/ws/cdp/{session_id}")
async def cdp_proxy(websocket: WebSocket, session_id: str):
    """WebSocket proxy to browser CDP endpoint."""
    import aiohttp
    
    session = await browser_manager.get_session(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return
    
    await websocket.accept()
    
    try:
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get(f"{session.cdp_url}/json/version") as resp:
                version_data = await resp.json()
                ws_url = version_data.get("webSocketDebuggerUrl")
            
            if not ws_url:
                await websocket.close(code=4005, reason="CDP WebSocket URL not available")
                return
            
            async with http_session.ws_connect(ws_url) as cdp_ws:
                async def client_to_cdp():
                    try:
                        while True:
                            data = await websocket.receive_text()
                            await cdp_ws.send_str(data)
                    except WebSocketDisconnect:
                        pass
                
                async def cdp_to_client():
                    try:
                        async for msg in cdp_ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                await websocket.send_text(msg.data)
                            elif msg.type == aiohttp.WSMsgType.ERROR:
                                break
                    except Exception:
                        pass
                
                await asyncio.gather(client_to_cdp(), cdp_to_client())
    
    except Exception as e:
        logger.error(f"CDP proxy error: {e}")
        try:
            await websocket.close(code=4006, reason=str(e))
        except Exception:
            pass
