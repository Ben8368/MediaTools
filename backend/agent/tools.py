"""Executable MediaTools agent tool implementations."""

from __future__ import annotations

from pathlib import Path

from modules.fetcher.analyzer import SubtitleAnalyzer
from modules.fetcher.subtitle import SubtitleProcessor


def tool_execute_decrypt_to_assets_impl(*, get_current_workspace_fn, run_decrypt_job_fn, summary_success_fn, input_path: str) -> dict:
    workspace = get_current_workspace_fn()
    result = run_decrypt_job_fn("自动解密", input_path, workspace["assets_dir"], remove_source=False, add_to_assets=True)
    return {
        "ok": summary_success_fn(result),
        "summary_rows": result.get("summary_rows", []),
        "result_text": result.get("result_text", ""),
        "output_dir": workspace["assets_dir"],
    }


def tool_get_video_info_impl(*, fetch_video_info_fn, get_current_workspace_fn, url: str) -> dict:
    info = fetch_video_info_fn(url, get_current_workspace_fn()["downloads_dir"], "{index}_{title}_{upload_date}")
    return {
        "ok": True,
        "video": info,
        "subtitle_summary": {
            "has_manual_subs": info.get("has_manual_subs", False),
            "has_auto_subs": info.get("has_auto_subs", False),
            "language": info.get("language", ""),
        },
    }


def tool_inspect_subtitle_impl(subtitle_path: str) -> dict:
    path = Path(subtitle_path)
    if not path.exists():
        return {"ok": False, "error": f"字幕文件不存在: {subtitle_path}"}

    processor = SubtitleProcessor()
    srt_path = processor.convert_vtt_to_srt(str(path)) if path.suffix.lower() == ".vtt" else str(path)
    segments = processor.parse_srt(srt_path)
    duration_seconds = 0
    if segments:
        end = segments[-1].get("end", "").replace(",", ":").replace(".", ":")
        parts = [int(part) for part in end.split(":") if part.isdigit()]
        if len(parts) >= 3:
            duration_seconds = parts[0] * 3600 + parts[1] * 60 + parts[2]
    return {
        "ok": True,
        "subtitle_path": srt_path,
        "segment_count": len(segments),
        "duration_seconds": duration_seconds,
        "preview": segments[:8],
    }


def tool_analyze_subtitle_impl(subtitle_path: str, api_key: str, base_url: str, model: str) -> dict:
    path = Path(subtitle_path)
    if not path.exists():
        return {"ok": False, "error": f"字幕文件不存在: {subtitle_path}"}

    processor = SubtitleProcessor()
    working_path = processor.convert_vtt_to_srt(str(path)) if path.suffix.lower() == ".vtt" else str(path)
    analyzer = SubtitleAnalyzer(api_key=api_key, base_url=base_url, model=model)
    highlights, llm_text = analyzer.analyze_from_srt(working_path, processor, model=model)
    return {
        "ok": True,
        "subtitle_path": working_path,
        "highlight_count": len(highlights),
        "highlights": highlights,
        "clip_suggestions": [
            {
                "clip_index": idx,
                "start_time": item.get("start_time", ""),
                "end_time": item.get("end_time", ""),
                "title": item.get("category", "亮点片段"),
                "reason": item.get("reason", ""),
                "summary_zh": item.get("summary_zh", ""),
                "quote": item.get("quote", ""),
            }
            for idx, item in enumerate(highlights[:10], 1)
        ],
        "llm_input_preview": llm_text[:1500],
    }


def tool_recommend_transcode_impl(input_path: str, goal: str) -> dict:
    suffix = Path(input_path).suffix.lower()
    normalized_goal = goal.strip() or "通用发布"
    recommendations = {
        "通用发布": {"codec": "H.264 (AVC)", "crf": 23, "preset": "medium", "reason": "兼顾体积与兼容性。"},
        "长期存档": {"codec": "H.265 (HEVC)", "crf": 24, "preset": "slow", "reason": "更适合长期保存和压缩率。"},
        "只要音频": {"codec": "音频提取", "crf": 0, "preset": "medium", "reason": "只导出音频内容。"},
        "快速预览": {"codec": "H.264 (AVC)", "crf": 28, "preset": "medium", "reason": "优先缩短等待时间。"},
    }
    return {
        "ok": True,
        "input_path": input_path,
        "input_ext": suffix,
        "goal": normalized_goal,
        "recommendation": recommendations.get(normalized_goal, recommendations["通用发布"]),
    }


def tool_execute_transcode_impl(*, run_transcode_job_fn, input_path: str, codec: str, output_path: str = "", crf: int = 23, preset: str = "medium") -> dict:
    result = run_transcode_job_fn(input_path, output_path, codec, crf, preset, "", "")
    return {
        "ok": bool(result.get("output_path")),
        "log": result.get("log", ""),
        "output_path": result.get("output_path", ""),
        "summary_rows": result.get("summary_rows", []),
    }


def tool_execute_slice_video_impl(*, run_slice_job_fn, input_path: str, start_time: str, end_time: str, output_path: str = "", accurate: bool = True) -> dict:
    result = run_slice_job_fn(input_path, start_time, end_time, output_path, accurate=accurate)
    return {
        "ok": bool(result.get("output_path")),
        "log": result.get("log", ""),
        "output_path": result.get("output_path", ""),
        "summary_rows": result.get("summary_rows", []),
    }


def tool_execute_fetch_analyze_slice_impl(*, run_fetch_analyze_slice_job_fn, url: str, api_key: str, base_url: str, model: str, clip_count: int = 3, video_codec_preference: str = "h264") -> dict:
    return run_fetch_analyze_slice_job_fn(
        url=url,
        index=1,
        video_codec_preference=video_codec_preference,
        subtitle_mode="original_only",
        subtitle_formats=["srt"],
        clip_count=clip_count,
        accurate_slice=True,
        api_key=api_key,
        base_url=base_url,
        model=model,
    )


def tool_scan_assets_impl(*, asset_library_cls, directory: str, keyword: str = "", asset_type: str = "") -> dict:
    library = asset_library_cls(directory)
    assets = library.scan()
    if keyword.strip():
        assets = library.search(keyword.strip())
    elif asset_type.strip():
        assets = library.list_assets(asset_type.strip())
    return {"ok": True, "directory": directory, "total": len(assets), "stats": library.get_stats(), "assets": assets[:30]}


def tool_suggest_asset_names_impl(paths: list[str], style: str = "kebab-case") -> dict:
    suggestions = []
    for raw_path in paths[:30]:
        path = Path(raw_path)
        normalized = " ".join(path.stem.strip().replace("_", " ").replace("-", " ").split())
        if style == "snake_case":
            new_stem = normalized.lower().replace(" ", "_")
        elif style == "kebab-case":
            new_stem = normalized.lower().replace(" ", "-")
        else:
            new_stem = normalized.replace(" ", "-")
        suggestions.append({"path": str(path), "suggested_name": f"{new_stem}{path.suffix.lower()}"})
    return {"ok": True, "style": style, "suggestions": suggestions}


def tool_extract_screenshot_impl(*, screenshot_generator_cls, video_path: str, timestamp: str, output_path: str = "") -> dict:
    gen = screenshot_generator_cls()
    if not output_path:
        video = Path(video_path)
        output_path = str(video.parent / f"{video.stem}_{timestamp.replace(':', '-')}.jpg")
    result = gen.extract_frame(video_path, timestamp, output_path)
    return {"ok": result.get("success", False), "output_path": result.get("output_path", ""), "error": result.get("error", "")}


def tool_export_wechat_moments_impl(*, get_current_workspace_fn, get_draft_fn, save_draft_fn, export_image_fn, text: str, author: str = "A", theme: str = "dark") -> dict:
    workspace = get_current_workspace_fn()
    draft = get_draft_fn(workspace)
    draft_data = {**draft.get("draft", {}), "text": text, "author": author, "theme": theme}
    save_draft_fn(draft_data, workspace)
    result = export_image_fn(workspace)
    return {"ok": result.get("ok", False), "image_path": result.get("image_path", ""), "error": result.get("error", "")}


def tool_list_psd_tickets_impl(*, get_current_workspace_fn, list_tickets_fn) -> dict:
    tickets = list_tickets_fn(get_current_workspace_fn())
    return {"ok": True, "count": len(tickets), "tickets": tickets[:20]}


def tool_scan_psd_impl(*, get_current_workspace_fn, scan_psd_fn, psd_path: str, languages: list[str] | None = None) -> dict:
    return scan_psd_fn(psd_path=psd_path, languages=languages or [], workspace=get_current_workspace_fn())


def tool_get_auditor_status_impl(*, get_current_workspace_fn, get_auditor_config_fn) -> dict:
    config_result = get_auditor_config_fn(get_current_workspace_fn())
    return {"ok": True, "config": config_result.get("config", {})}


def tool_run_audit_scan_impl(*, get_current_workspace_fn, run_auditor_scan_once_fn) -> dict:
    result = run_auditor_scan_once_fn(get_current_workspace_fn())
    return {
        "ok": result.get("ok", False),
        "scanned_count": result.get("scanned_count", 0),
        "flagged_count": result.get("flagged_count", 0),
        "summary": result.get("summary", ""),
    }


def tool_get_ae_status_impl(*, get_current_workspace_fn, get_ae_status_fn) -> dict:
    return {"ok": True, "status": get_ae_status_fn(get_current_workspace_fn())}


def tool_list_ae_tickets_impl(*, get_current_workspace_fn, list_ae_tickets_fn) -> dict:
    tickets = list_ae_tickets_fn(get_current_workspace_fn())
    return {"ok": True, "count": len(tickets), "tickets": tickets}


def tool_scan_ae_project_impl(*, get_current_workspace_fn, scan_ae_project_fn, project_path: str) -> dict:
    return scan_ae_project_fn(project_path=project_path, workspace=get_current_workspace_fn())
