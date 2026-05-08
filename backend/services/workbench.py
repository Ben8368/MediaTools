"""Editing workbench services inspired by the legacy MediaTools-Work flow."""

from __future__ import annotations

import json
from pathlib import Path

from backend.config import get_api_config
from backend.services.media.core import run_batch_slice_job
from backend.services.workspace import get_current_workspace, get_workspace_dir, workspace_path
from modules.fetcher.analyzer import SubtitleAnalyzer
from modules.fetcher.subtitle import SubtitleProcessor


def list_workspace_media() -> dict:
    from modules.assets.library import AssetLibrary

    workspace = get_current_workspace()
    library = AssetLibrary(workspace["project_root"])
    assets = library.scan()

    videos = [asset for asset in assets if asset["type"] == "video"]
    subtitles = [asset for asset in assets if asset["type"] == "subtitle"]

    video_rows = [[item["name"], item["directory"], item["size_mb"], item["path"]] for item in videos]
    subtitle_rows = [[item["name"], item["directory"], item["size_mb"], item["path"]] for item in subtitles]
    recent_exports = sorted(
        [
            asset
            for asset in assets
            if asset["type"] == "video"
            and (
                workspace["exports_dir"] in asset["path"]
                or workspace["clips_dir"] in asset["path"]
            )
        ],
        key=lambda item: item["modified"],
        reverse=True,
    )[:20]
    export_rows = [[item["name"], item["directory"], item["size_mb"], item["path"]] for item in recent_exports]

    return {
        "workspace": workspace,
        "video_rows": video_rows,
        "subtitle_rows": subtitle_rows,
        "export_rows": export_rows,
    }


def analyze_subtitle_for_workbench(subtitle_path: str, extra_context: str = "", expected_duration: float = 0.0) -> dict:
    subtitle_file = Path(subtitle_path)
    if not subtitle_file.exists():
        return {"ok": False, "message": f"字幕文件不存在: {subtitle_path}"}

    config = get_api_config()
    processor = SubtitleProcessor()
    working_path = str(subtitle_file)
    if subtitle_file.suffix.lower() == ".vtt":
        working_path = processor.convert_vtt_to_srt(str(subtitle_file))

    analyzer = SubtitleAnalyzer(
        api_key=config["api_key"],
        base_url=config["api_base_url"],
        model=config["analysis_model"],
    )
    highlights, _ = analyzer.analyze_from_srt(
        working_path,
        processor,
        model=config["analysis_model"],
        extra_context=extra_context,
        expected_duration=expected_duration,
    )
    selected = []
    for idx, item in enumerate(highlights, 1):
        if not item.get("start_time") or not item.get("end_time"):
            continue
        selected.append({
            "index": idx,
            "title": item.get("category", f"clip_{idx}"),
            "start_time": item.get("start_time", ""),
            "end_time": item.get("end_time", ""),
            "summary_zh": item.get("summary_zh", item.get("reason", "")),
            "quote": item.get("quote", ""),
        })

    analysis_path = workspace_path(
        "analysis",
        f"{subtitle_file.stem}_workbench_analysis.json",
        workspace=get_current_workspace(),
    )
    analysis_path.write_text(
        json.dumps({"subtitle_path": working_path, "clips": selected}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "ok": True,
        "subtitle_path": working_path,
        "clips": selected,
        "clips_json": json.dumps(selected, ensure_ascii=False, indent=2),
        "analysis_path": str(analysis_path),
    }


def export_clips_from_workbench(
    video_path: str,
    subtitle_path: str,
    clips_json: str,
    burn_subtitles: bool = True,
    start_padding: float = 0.8,
    end_padding: float = 1.0,
) -> dict:
    if not video_path.strip():
        return {"ok": False, "message": "请输入视频路径"}
    if not clips_json.strip():
        return {"ok": False, "message": "没有可导出的片段"}

    try:
        clips = json.loads(clips_json)
    except json.JSONDecodeError as exc:
        return {"ok": False, "message": f"片段 JSON 无效: {exc}"}

    workspace = get_current_workspace()
    export_dir = get_workspace_dir("clips", workspace) / f"{Path(video_path).stem}_workbench_clips"
    result = run_batch_slice_job(
        video_path,
        clips,
        output_dir=str(export_dir),
        start_padding=start_padding,
        end_padding=end_padding,
        subtitle_path=subtitle_path or None,
        burn_subtitles=burn_subtitles and bool(subtitle_path.strip()),
    )
    return {
        "ok": bool(result.get("output_paths")),
        "message": result.get("log", ""),
        "summary_rows": result.get("summary_rows", []),
        "export_rows": [[Path(path).name, str(Path(path).parent), round(Path(path).stat().st_size / (1024 * 1024), 2), path] for path in result.get("output_paths", []) if Path(path).exists()],
        "clips": result.get("clips", []),
    }
