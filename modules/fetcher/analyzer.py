from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from backend.config import ANALYSIS_MODEL, ANALYSIS_PROMPT, API_BASE_URL, API_KEY
from core.logger import get_logger

logger = get_logger(__name__)

MAX_SUBTITLE_CHARS = 8000
TRUNCATION_MARKER = "\n...(content truncated)"


def _truncate_subtitle_text(text: str, max_len: int = MAX_SUBTITLE_CHARS) -> str:
    """Keep LLM prompts bounded while trying to cut at a line boundary."""
    if len(text) <= max_len:
        return text

    truncated = text[:max_len]
    last_newline = truncated.rfind("\n")
    cut_index = last_newline if last_newline > max_len - 500 else max_len
    return text[:cut_index] + TRUNCATION_MARKER


def _normalize_highlights(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and "highlights" in payload:
        payload = payload["highlights"]
    elif isinstance(payload, dict):
        payload = [payload]

    if not isinstance(payload, list):
        return []

    normalized: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        item.setdefault("summary_zh", item.get("reason", ""))
        normalized.append(item)
    return normalized


class SubtitleAnalyzer:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        client: Any | None = None,
    ):
        from backend.config import get_api_config

        cfg = get_api_config()
        self.api_key = api_key or cfg["api_key"] or API_KEY
        self.base_url = base_url or cfg["api_base_url"] or API_BASE_URL
        self.model = model or cfg["analysis_model"] or ANALYSIS_MODEL
        self.client = client or OpenAI(api_key=self.api_key, base_url=self.base_url)

    def analyze(self, subtitle_text: str, model: str | None = None) -> list[dict[str, Any]]:
        prompt_text = _truncate_subtitle_text(subtitle_text or "")

        try:
            response = self.client.chat.completions.create(
                model=model or self.model,
                messages=[
                    {"role": "system", "content": ANALYSIS_PROMPT},
                    {"role": "user", "content": prompt_text},
                ],
                temperature=0.3,
                max_tokens=4000,
            )
            content = response.choices[0].message.content or ""
            return _normalize_highlights(json.loads(content))
        except json.JSONDecodeError:
            return []
        except Exception as exc:
            logger.error("LLM analysis failed: %s", exc, exc_info=True)
            return []

    def analyze_from_srt(self, srt_path: str, subtitle_processor, model: str | None = None) -> tuple:
        segments = subtitle_processor.parse_srt(srt_path)
        text = subtitle_processor.format_for_llm(segments)
        highlights = self.analyze(text, model)
        return highlights, text
