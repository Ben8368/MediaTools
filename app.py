#!/usr/bin/env python3
"""
MediaTools Web 服务入口

用法:
    python app.py                     # 启动服务（默认端口 7860）
    python app.py --port 8080         # 指定端口
    python app.py --reload            # 开发模式（代码变更自动重载）
"""
import argparse
import asyncio
import ipaddress
import sys
from pathlib import Path

import uvicorn

sys.path.insert(0, str(Path(__file__).parent))

from backend.config import API_SECRET_KEY, GUI_SERVER_NAME, GUI_SERVER_PORT


def configure_windows_event_loop() -> None:
    """Avoid noisy Proactor disconnect callbacks on Windows console servers."""
    if sys.platform != "win32":
        return
    # Use SelectorEventLoop on Windows to avoid ProactorEventLoop issues
    # Note: WindowsSelectorEventLoopPolicy is deprecated in Python 3.16+
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            policy = getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
            if policy is not None:
                asyncio.set_event_loop_policy(policy())
    except Exception:
        # If the policy is not available or fails, continue with default
        pass


def _is_loopback_host(host: str) -> bool:
    normalized = (host or "").strip().lower()
    if normalized in {"localhost", "127.0.0.1", "::1"}:
        return True
    if normalized in {"", "0.0.0.0", "::"}:
        return False
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def main():
    configure_windows_event_loop()
    root_dir = Path(__file__).parent.resolve()

    parser = argparse.ArgumentParser(description="MediaTools Web 服务")
    parser.add_argument("--port", type=int, default=GUI_SERVER_PORT, help="服务端口")
    parser.add_argument("--host", default=GUI_SERVER_NAME, help="服务地址")
    parser.add_argument("--reload", action="store_true", help="开发模式（代码变更自动重载）")

    args = parser.parse_args()
    if not API_SECRET_KEY and not _is_loopback_host(args.host):
        parser.error("API_SECRET_KEY must be set before binding MediaTools to a non-loopback host.")

    print("启动 MediaTools Web 服务...")
    print(f"监听地址: {args.host}:{args.port}")
    print(f"本地访问: http://{args.host}:{args.port}")
    print(f"API 文档: http://{args.host}:{args.port}/docs")

    uvicorn.run(
        "backend.api.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,

        reload_dirs=[str(root_dir)] if args.reload else None,
        access_log=False,
    )


if __name__ == "__main__":
    main()
