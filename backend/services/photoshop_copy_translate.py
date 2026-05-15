"""Photoshop 工单：批量本地化翻译 original_text -> target_text（调用配置中的 LLM）。"""

from __future__ import annotations

import json
import re
from typing import Any

from backend.config import get_api_config
from backend.services.llm_translate import localization_batch_translate

# 与 vendor Photoshop config_reader.horizontal_outer_strip 行为一致：不去掉首尾的换行
_HORIZONTAL_WS = frozenset(" \t\v\f\u00a0\u2007\u3000")


def _horizontal_outer_strip(value: str) -> str:
    if not value:
        return value
    s = str(value)
    start = 0
    end = len(s)
    while start < end and s[start] in _HORIZONTAL_WS:
        start += 1
    while end > start and s[end - 1] in _HORIZONTAL_WS:
        end -= 1
    return s[start:end]


def _normalize_newlines(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def _parse_json_object(content: str) -> dict[str, Any]:
    text = content.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("模型未返回 JSON 对象")
    return json.loads(text[start : end + 1])


def translate_photoshop_copy_items(
    items: list[dict[str, Any]],
    *,
    api_key: str = "",
    base_url: str = "",
    model: str = "",
    chunk_size: int = 24,
) -> dict[str, Any]:
    """
    items: {index: int, text: str, locale: str}
    返回: {ok: True, items: [{index, text}]} 或 {ok: False, error}
    """
    cfg = get_api_config()
    effective_api_key = api_key or cfg["api_key"]
    effective_base_url = base_url or cfg["api_base_url"]
    effective_model = model or cfg["analysis_model"]
    if not (effective_api_key or "").strip():
        return {"ok": False, "error": "未配置模型 API Key"}

    normalized: list[dict[str, Any]] = []
    seen: set[int] = set()
    for it in items:
        try:
            idx = int(it.get("index", -1))
        except (TypeError, ValueError):
            continue
        if idx < 0 or idx in seen:
            continue
        text = _horizontal_outer_strip(_normalize_newlines(str(it.get("text", "") or "")))
        loc = str(it.get("locale", "") or "").strip()
        if not loc:
            continue
        if not text:
            continue
        seen.add(idx)
        normalized.append({"i": idx, "text": text, "locale": loc})

    if not normalized:
        return {"ok": False, "error": "没有有效的翻译条目（需要原文与 locale）"}

    translated: dict[int, str] = {}
    for offset in range(0, len(normalized), chunk_size):
        chunk = normalized[offset : offset + chunk_size]
        try:
            raw = localization_batch_translate(
                chunk,
                api_key=effective_api_key,
                base_url=effective_base_url,
                model=effective_model,
            )
            payload = _parse_json_object(raw)
        except Exception as exc:
            return {"ok": False, "error": f"翻译或解析失败: {exc}"}
        arr = payload.get("items")
        if not isinstance(arr, list):
            return {"ok": False, "error": "模型 JSON 缺少 items 数组"}
        expected = {entry["i"] for entry in chunk}
        got: set[int] = set()
        for row in arr:
            if not isinstance(row, dict) or "i" not in row:
                continue
            try:
                i = int(row["i"])
            except (TypeError, ValueError):
                continue
            t = row.get("t")
            if t is None:
                continue
            translated[i] = _horizontal_outer_strip(_normalize_newlines(str(t)))
            got.add(i)
        missing = expected - got
        if missing:
            return {"ok": False, "error": f"模型未返回部分任务译文: {sorted(missing)}"}

        src_by_i = {entry["i"]: entry["text"] for entry in chunk}
        for i in sorted(expected):
            src_t = src_by_i[i]
            out_t = translated[i]
            if src_t.count("\n") != out_t.count("\n"):
                sn = src_t.count("\n") + 1
                on = out_t.count("\n") + 1
                return {
                    "ok": False,
                    "error": f"任务 {i} 译文行数与原文不一致（原文 {sn} 行，译文 {on} 行）。请重试 Ai 翻译或人工改行。",
                }

    return {"ok": True, "items": [{"index": i, "text": translated[i]} for i in sorted(translated.keys())]}
