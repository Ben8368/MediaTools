"""HTTP adapter for a local capcut-mate service.

The old "direct" import mode was only a placeholder: it did not bind to a real
capcut-mate Python API and raised NotImplementedError later during execution.
Keep the public adapter honest by supporting only the HTTP service mode.
"""

from __future__ import annotations

from typing import Any

import requests

from backend.config import CAPCUT_MATE_BASE_URL


class CapcutAdapter:
    """Small client for the capcut-mate OpenAPI endpoints."""

    def __init__(self, mode: str = "http", base_url: str | None = None, timeout: float = 30.0):
        if mode != "http":
            raise ValueError("Only capcut-mate HTTP mode is supported. Start capcut-mate and use mode='http'.")
        self.mode = mode
        self.base_url = (base_url or CAPCUT_MATE_BASE_URL).rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()

    def close(self) -> None:
        self._session.close()

    def status(self) -> dict[str, Any]:
        """Return service availability without raising for connection errors."""
        try:
            response = self._session.get(f"{self.base_url}/docs", timeout=min(self.timeout, 3.0))
            return {
                "available": response.status_code == 200,
                "mode": self.mode,
                "base_url": self.base_url,
                "status_code": response.status_code,
            }
        except requests.RequestException as exc:
            return {
                "available": False,
                "mode": self.mode,
                "base_url": self.base_url,
                "error": str(exc),
            }

    def _post(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._session.post(f"{self.base_url}{endpoint}", json=payload, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _get(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        response = self._session.get(f"{self.base_url}{endpoint}", params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def create_draft(self, width: int = 1080, height: int = 1920) -> dict[str, Any]:
        return self._post(
            "/openapi/capcut-mate/v1/create_draft",
            {"width": width, "height": height},
        )

    def add_videos(self, draft_url: str, video_infos: list[dict[str, Any]]) -> dict[str, Any]:
        return self._post(
            "/openapi/capcut-mate/v1/add_videos",
            {"draft_url": draft_url, "video_infos": video_infos},
        )

    def gen_video(self, draft_id: str) -> dict[str, Any]:
        return self._post(
            "/openapi/capcut-mate/v1/gen_video",
            {"draft_id": draft_id},
        )

    def gen_video_status(self, task_id: str) -> dict[str, Any]:
        return self._get(
            "/openapi/capcut-mate/v1/gen_video_status",
            {"task_id": task_id},
        )
