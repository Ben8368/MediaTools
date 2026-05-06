"""
ai_client.py — OpenAI-compatible API 封装，支持双模型交叉审核
"""
import base64
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi"}

MIME_MAP = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


class AIClient:
    def __init__(self, sys_config: Dict[str, str]):
        self.api_key = os.getenv("TEC_CHI_API_KEY", "") or sys_config.get("TEC_CHI_API_KEY", "").strip()
        self.base_url = os.getenv("OPENAI_BASE_URL", "") or sys_config.get("OPENAI_BASE_URL", "").strip()
        self.model_auditor1 = sys_config.get("MODEL_AUDITOR_1", "qwen3.6-plus")
        self.model_auditor2 = sys_config.get("MODEL_AUDITOR_2", "gpt-5.4")
        self.timeout = int(sys_config.get("API_TIMEOUT_SECONDS", "300"))
        self.retry = int(sys_config.get("API_RETRY_COUNT", "3"))
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError("请在环境变量中设置 TEC_CHI_API_KEY")
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    def analyze(self, file_path: str, prompt: str, auditor_id: int = 1) -> List[Dict]:
        """调用 AI 分析，auditor_id 选择模型（1=一审, 2=二审）"""
        client = self._get_client()

        ext = Path(file_path).suffix.lower()
        model_name = self.model_auditor1 if auditor_id == 1 else self.model_auditor2
        mime = MIME_MAP.get(ext, "application/octet-stream")

        with open(file_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")

        content_url = f"data:{mime};base64,{data}"

        for attempt in range(self.retry):
            try:
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": content_url}},
                            ],
                        }
                    ],
                    response_format={"type": "json_object"},
                )
                text = resp.choices[0].message.content.strip()
                if text.startswith("```"):
                    text = re.sub(r"^```(?:json)?\n?|```$", "", text, flags=re.MULTILINE).strip()
                return json.loads(text)
            except Exception as e:
                logger.warning(
                    "AI attempt %d/%d failed for %s (model=%s): %s",
                    attempt + 1, self.retry, file_path, model_name, e
                )
                if attempt < self.retry - 1:
                    time.sleep(5 * (attempt + 1))
        raise RuntimeError(f"AI failed after {self.retry} attempts: {file_path}")