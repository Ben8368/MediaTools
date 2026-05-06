"""Browser session manager - connects to browser launched with CDP."""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import subprocess
import uuid
from typing import Any

logger = logging.getLogger(__name__)

CDP_PORT = 9222

BROWSER_PATHS = {
    "chrome": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ],
    "edge": [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
    ],
}

SHORTCUT_DIR = os.path.expandvars(r"%USERPROFILE%\Desktop")

BROWSER_LABELS = { "chrome": "Chrome", "edge": "Edge" }

LAUNCH_GUIDE = """
璇锋墜鍔ㄥ惎鍔ㄥ甫杩滅▼璋冭瘯鐨勬祻瑙堝櫒锛?
  1. 鎸?Win+R锛岀矘璐翠互涓嬪懡浠ゅ苟鍥炶溅锛堥€夋嫨浣犵殑娴忚鍣級锛?
     Edge:
     "%LOCALAPPDATA%\\Microsoft\\Edge\\Application\\msedge.exe" --remote-debugging-port=9222

     Chrome:
     "%LOCALAPPDATA%\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222

  2. 娴忚鍣ㄤ細浠ヤ綘鐨勯粯璁ら厤缃惎鍔紙淇濈暀鎵€鏈夌櫥褰曟€併€佹彃浠讹級
  3. 鍦ㄦ绐楀彛鐐瑰嚮銆岃繛鎺ャ€嶅嵆鍙?
鎻愮ず锛氶娆¤繛鎺ュ悗锛孧ediaTools 浼氬湪妗岄潰鍒涘缓涓€涓揩鎹锋柟寮忥紝浠ュ悗鍙屽嚮鍗冲彲銆?""".strip()


def find_browser_exe(browser_type: str = "chrome") -> str | None:
    for path in BROWSER_PATHS.get(browser_type, []):
        if os.path.exists(path):
            return path
    return None


def _is_port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except (ConnectionRefusedError, OSError):
        return False


def create_cdp_shortcut(browser_type: str, vbs_path: str) -> str:
    exe = find_browser_exe(browser_type)
    if not exe:
        return ""
    label = BROWSER_LABELS.get(browser_type, "Browser")
    vbs_path = os.path.join(SHORTCUT_DIR, f"MediaTools {label} (CDP).vbs")
    exe_escaped = exe.replace("\\", "\\\\")
    vbs_content = f"""Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """ + '"' + exe_escaped + " --remote-debugging-port=" + str(CDP_PORT) + '"' + """, 1, False
""".lstrip()
    try:
        with open(vbs_path, "w", encoding="utf-8") as f:
            f.write(vbs_content)
        # Create .lnk using PowerShell
        lnk_path = os.path.join(SHORTCUT_DIR, f"MediaTools {label} (CDP).lnk")
        ps_cmd = (
            f'$ws = New-Object -ComObject WScript.Shell; '
            f'$lnk = $ws.CreateShortcut("{lnk_path}"); '
            f'$lnk.TargetPath = "{exe}"; '
            f'$lnk.Arguments = "--remote-debugging-port={CDP_PORT}"; '
            f'$lnk.WorkingDirectory = "{os.path.dirname(exe)}"; '
            f'$lnk.WindowStyle = 1; '
            f'$lnk.Save()'
        )
        subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, timeout=10)
        # Clean up .vbs if created
        if os.path.exists(vbs_path) and os.path.exists(lnk_path):
            os.remove(vbs_path)
        return lnk_path if os.path.exists(lnk_path) else vbs_path
    except Exception as e:
        logger.error(f"Failed to create shortcut: {e}")
        return ""


class BrowserSession:
    def __init__(self, session_id: str, url: str, browser_type: str = "chrome"):
        self.session_id = session_id
        self.url = url
        self.browser_type = browser_type
        self.cdp_port = CDP_PORT
        self.cdp_url = f"http://127.0.0.1:{CDP_PORT}"
        self.browser_exe = ""
        self.shortcut_path = ""
        self.created_at = asyncio.get_event_loop().time()
        self.last_activity = self.created_at

    async def connect(self):
        self.browser_exe = find_browser_exe(self.browser_type)
        if not self.browser_exe:
            raise RuntimeError(f"{self.browser_type} browser executable not found")

        if not _is_port_open(CDP_PORT):
            self.shortcut_path = create_cdp_shortcut(self.browser_type)
            raise RuntimeError(LAUNCH_GUIDE)

        logger.info(f"Connected to {self.browser_type} on CDP port {CDP_PORT}")

    async def get_cookies(self) -> list[dict[str, Any]]:
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.cdp_url}/json/version") as resp:
                    version_data = await resp.json()
                    ws_url = version_data.get("webSocketDebuggerUrl")
                if not ws_url: return []
                async with session.ws_connect(ws_url) as ws:
                    await ws.send_json({"id": 1, "method": "Network.getCookies", "params": {}})
                    response = await ws.receive_json()
                    cookies = response.get("result", {}).get("cookies", [])
                    return [
                        {"name": c["name"], "value": c["value"], "domain": c["domain"],
                         "path": c["path"], "secure": c.get("secure", False),
                         "httpOnly": c.get("httpOnly", False), "sameSite": c.get("sameSite", "Lax")}
                        for c in cookies
                    ]
        except Exception as e:
            logger.error(f"Failed to get cookies: {e}")
            return []

    async def close(self):
        logger.info(f"Session {self.session_id} closed (browser left running)")


class BrowserManager:
    def __init__(self):
        self.sessions: dict[str, BrowserSession] = {}

    async def create_session(self, url: str, browser_type: str = "chrome") -> BrowserSession:
        for s in self.sessions.values():
            if s.browser_type == browser_type:
                s.last_activity = asyncio.get_event_loop().time()
                return s
        session = BrowserSession(str(uuid.uuid4()), url, browser_type)
        await session.connect()
        self.sessions[session.session_id] = session
        return session

    async def get_session(self, session_id: str) -> BrowserSession | None:
        s = self.sessions.get(session_id)
        if s: s.last_activity = asyncio.get_event_loop().time()
        return s

    async def close_session(self, session_id: str) -> bool:
        s = self.sessions.get(session_id)
        if s: await s.close(); del self.sessions[session_id]; return True
        return False

    async def close_all(self):
        for sid in list(self.sessions): await self.close_session(sid)

    def list_sessions(self) -> list[dict[str, Any]]:
        return [{"session_id": s.session_id, "url": s.url, "browser_type": s.browser_type,
                 "cdp_port": s.cdp_port, "shortcut_path": s.shortcut_path} for s in self.sessions.values()]


browser_manager = BrowserManager()
