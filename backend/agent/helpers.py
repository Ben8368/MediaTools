"""Helper utilities for the MediaTools agent."""

from __future__ import annotations

import json
import re
from pathlib import Path


def _json_dumps(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


def _format_tool_trace(tool_traces: list[dict]) -> str:
    if not tool_traces:
        return "未调用工具"
    names = [(item.get("tool") or item.get("route") or "unknown") for item in tool_traces]
    return "已调用工具: " + ", ".join(names) + "\n\n" + _json_dumps(tool_traces)


def _extract_urls(text: str) -> list[str]:
    return re.findall(r"https?://[^\s]+", text or "")


def _extract_local_paths(text: str) -> list[str]:
    matches = re.findall(r"[A-Za-z]:\\[^\n\r\t]+", text or "")
    return [match.strip().strip('"') for match in matches]


def _looks_like_fetch_analyze_slice_task(text: str) -> bool:
    lowered = (text or "").lower()
    raw = text or ""
    return (
        ("下载" in raw and "切片" in raw)
        or "自动切片" in raw
        or ("analyze" in lowered and "slice" in lowered)
    )


def _looks_like_asset_scan_task(text: str) -> bool:
    raw = text or ""
    return "扫描" in raw and ("素材" in raw or "项目" in raw)


def _looks_like_decrypt_task(text: str) -> bool:
    lowered = (text or "").lower()
    return ("解密" in (text or "")) or any(
        ext in lowered for ext in [".ncm", ".qmc", ".mflac", ".kgm", ".kwm", ".xm"]
    )


def _format_fetch_analyze_slice_answer(result: dict) -> str:
    if not result.get("ok"):
        lines = ["执行失败", "", result.get("message", "未知错误")]
        subtitle_errors = result.get("subtitle_errors", [])
        if subtitle_errors:
            lines.extend(["", "字幕处理错误:"])
            lines.extend(f"- {item}" for item in subtitle_errors[:5])
        return "\n".join(lines)

    selected = result.get("selected_clips", [])
    slice_result = result.get("slice_result", {})
    lines = [
        "执行成功",
        f"视频: {result.get('video_info', {}).get('title', '未知视频')}",
        f"视频文件: {result.get('video_path', '')}",
        f"字幕文件: {result.get('subtitle_path', '')}",
        f"分析结果: {result.get('analysis_path', '')}",
        f"切片数量: {len(slice_result.get('output_paths', []))}",
        f"输出目录: {slice_result.get('output_dir', '')}",
        "",
        "选中的切片区间:",
    ]
    for idx, item in enumerate(selected, 1):
        actual_start = item.get("actual_start_time", item.get("start_time", ""))
        actual_end = item.get("actual_end_time", item.get("end_time", ""))
        lines.append(
            f"{idx}. 推荐区间 {item.get('start_time', '')} -> {item.get('end_time', '')} | "
            f"实际切片 {actual_start} -> {actual_end} | "
            f"{item.get('title', '未命名片段')} | {item.get('summary_zh', item.get('reason', ''))}"
        )
        if item.get("quote"):
            lines.append(f"   引用: {item.get('quote', '')}")
    return "\n".join(lines)


def _parse_time_to_seconds(value: str) -> int:
    if not value:
        return 0
    raw = value.replace(",", ":").replace(".", ":")
    parts = [int(part) for part in raw.split(":") if part.isdigit()]
    if len(parts) >= 3:
        hours, minutes, seconds = parts[0], parts[1], parts[2]
        return hours * 3600 + minutes * 60 + seconds
    return 0


def _summary_success(result: dict) -> bool:
    if "ok" in result:
        return bool(result["ok"])
    rows = result.get("summary_rows") or []
    return bool(rows and len(rows[0]) > 1 and rows[0][1] == "成功")


def _make_action(kind: str, title: str, status: str, detail: str, payload: dict | None = None) -> dict:
    safe_detail = detail.strip() if detail else ""
    return {
        "id": f"{kind}:{title}:{abs(hash((kind, title, safe_detail)))}",
        "kind": kind,
        "title": title,
        "status": status,
        "detail": safe_detail,
        "payload": payload or {},
    }


def _make_artifact(path: str, kind: str, label: str | None = None, metadata: dict | None = None) -> dict | None:
    if not path:
        return None
    artifact_path = Path(path)
    return {
        "id": f"{kind}:{artifact_path.resolve() if artifact_path.exists() else artifact_path}",
        "kind": kind,
        "label": label or artifact_path.name or str(artifact_path),
        "path": str(artifact_path),
        "exists": artifact_path.exists(),
        "metadata": metadata or {},
    }


def _extend_unique(target: list[dict], incoming: list[dict]) -> None:
    existing_ids = {item.get("id") for item in target}
    for item in incoming:
        if not item or item.get("id") in existing_ids:
            continue
        target.append(item)
        existing_ids.add(item.get("id"))


def _response(ok: bool, answer: str, tool_traces: list[dict], actions: list[dict], artifacts: list[dict]) -> dict:
    return {
        "ok": ok,
        "answer": answer,
        "tool_trace_text": _format_tool_trace(tool_traces),
        "actions": actions,
        "artifacts": artifacts,
    }


def _summarize_tool_result(name: str, arguments: dict, result: dict) -> tuple[list[dict], list[dict]]:
    ok = _summary_success(result)
    status = "done" if ok else "error"
    actions: list[dict] = []
    artifacts: list[dict] = []

    if name == "get_video_info":
        video = result.get("video", {})
        actions.append(
            _make_action(
                "inspect_video",
                "查看视频信息",
                status,
                video.get("title") or result.get("error", "未获取到视频信息"),
            )
        )
    elif name == "inspect_subtitle":
        subtitle_path = result.get("subtitle_path", "")
        actions.append(
            _make_action(
                "inspect_subtitle",
                "检查字幕",
                status,
                f"共 {result.get('segment_count', 0)} 段，时长 {result.get('duration_seconds', 0)} 秒"
                if ok
                else result.get("error", "字幕检查失败"),
            )
        )
        artifact = _make_artifact(subtitle_path, "subtitle", "字幕文件")
        if artifact:
            artifacts.append(artifact)
    elif name == "analyze_subtitle":
        subtitle_path = result.get("subtitle_path", "")
        actions.append(
            _make_action(
                "analyze_subtitle",
                "分析字幕亮点",
                status,
                f"提取了 {result.get('highlight_count', 0)} 个亮点" if ok else result.get("error", "字幕分析失败"),
            )
        )
        artifact = _make_artifact(subtitle_path, "subtitle", "字幕源文件")
        if artifact:
            artifacts.append(artifact)
    elif name == "recommend_transcode":
        rec = result.get("recommendation", {})
        actions.append(
            _make_action(
                "recommend_transcode",
                "推荐转码参数",
                status,
                f"建议 {rec.get('codec', '未知编码')} / CRF {rec.get('crf', '-')}",
            )
        )
    elif name == "execute_transcode":
        output_path = result.get("output_path", "")
        actions.append(
            _make_action("transcode", "执行转码", status, output_path or result.get("log", "转码失败"))
        )
        artifact = _make_artifact(
            output_path,
            "audio" if arguments.get("codec") == "音频提取" else "video",
            "转码输出",
        )
        if artifact:
            artifacts.append(artifact)
    elif name == "execute_slice_video":
        output_path = result.get("output_path", "")
        actions.append(
            _make_action("slice", "执行视频切片", status, output_path or result.get("log", "切片失败"))
        )
        artifact = _make_artifact(output_path, "clip", "切片输出")
        if artifact:
            artifacts.append(artifact)
    elif name == "execute_fetch_analyze_slice":
        actions.append(
            _make_action(
                "pipeline",
                "下载并分析切片",
                status,
                result.get("message", "执行完成" if ok else "执行失败"),
            )
        )
        for artifact in [
            _make_artifact(result.get("video_path", ""), "video", "下载视频"),
            _make_artifact(result.get("subtitle_path", ""), "subtitle", "字幕文件"),
            _make_artifact(result.get("analysis_path", ""), "analysis", "分析结果"),
            _make_artifact(result.get("slice_result", {}).get("output_dir", ""), "directory", "切片目录"),
        ]:
            if artifact:
                artifacts.append(artifact)
        for idx, clip_path in enumerate(result.get("slice_result", {}).get("output_paths", []), 1):
            artifact = _make_artifact(clip_path, "clip", f"切片 {idx}")
            if artifact:
                artifacts.append(artifact)
    elif name == "scan_assets":
        actions.append(
            _make_action(
                "scan_assets",
                "扫描素材库",
                status,
                f"扫描 {result.get('directory', '')}，共 {result.get('total', 0)} 项" if ok else result.get("error", "素材扫描失败"),
            )
        )
    elif name == "suggest_asset_names":
        actions.append(
            _make_action(
                "rename_suggestion",
                "生成命名建议",
                status,
                f"生成 {len(result.get('suggestions', []))} 条建议" if ok else result.get("error", "命名建议生成失败"),
            )
        )

    return actions, artifacts
