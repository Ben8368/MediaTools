"""Composite media workflows that combine fetching, analysis, and clipping."""

from pathlib import Path

from modules.fetcher.analyzer import SubtitleAnalyzer
from modules.fetcher.downloader import VideoDownloader
from modules.fetcher.subtitle import SubtitleProcessor
from backend.services.media.encoding import run_batch_slice_job
from backend.services.media.helpers import _write_analysis_artifact
from backend.services.workspace import get_current_workspace, get_workspace_dir


def run_fetch_analyze_slice_job(
    url: str,
    index: int = 1,
    naming_template: str = "{index}_{title}_{upload_date}",
    video_codec_preference: str = "h264",
    subtitle_mode: str = "original_only",
    subtitle_formats: list[str] | None = None,
    clip_count: int = 3,
    accurate_slice: bool = True,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    *,
    downloader_cls=None,
    subtitle_processor_cls=None,
    subtitle_analyzer_cls=None,
    run_batch_slice_job_fn=None,
    get_current_workspace_fn=None,
    get_workspace_dir_fn=None,
) -> dict:
    if not url.strip():
        return {"ok": False, "message": "请输入视频 URL"}

    downloader_cls = downloader_cls or VideoDownloader
    subtitle_processor_cls = subtitle_processor_cls or SubtitleProcessor
    subtitle_analyzer_cls = subtitle_analyzer_cls or SubtitleAnalyzer
    run_batch_slice_job_fn = run_batch_slice_job_fn or run_batch_slice_job
    get_current_workspace_fn = get_current_workspace_fn or get_current_workspace
    get_workspace_dir_fn = get_workspace_dir_fn or get_workspace_dir

    workspace = get_current_workspace_fn()
    downloader = downloader_cls(workspace["downloads_dir"], naming_template)
    processor = subtitle_processor_cls()

    try:
        info = downloader.get_video_info(url.strip())
        info = downloader.download_video(url.strip(), index, info=info, codec_preference=video_codec_preference)
        if info.get("video_status") == "failed" or not info.get("local_path"):
            return {"ok": False, "message": f"视频下载失败: {info.get('video_error', '未知错误')}"}

        subtitle_result = downloader.download_subtitles_only(
            url.strip(),
            index,
            info=info,
            subtitle_mode=subtitle_mode,
            subtitle_formats=subtitle_formats or ["srt"],
        )

        original_outputs = subtitle_result.get("original", {})
        subtitle_errors = subtitle_result.get("errors", [])
        analysis_subtitle = original_outputs.get("srt") or original_outputs.get("vtt")
        if not analysis_subtitle:
            return {
                "ok": False,
                "message": "下载完成，但没有可分析字幕。请确认视频存在原语言字幕。",
                "video_path": info.get("local_path", ""),
                "subtitle_errors": subtitle_errors,
            }

        if analysis_subtitle.lower().endswith(".vtt"):
            analysis_subtitle = processor.convert_vtt_to_srt(analysis_subtitle)

        analyzer = subtitle_analyzer_cls(api_key=api_key, base_url=base_url, model=model)
        highlights, _ = analyzer.analyze_from_srt(analysis_subtitle, processor, model=model)
        selected_clips = [
            {
                "title": item.get("category", f"clip_{idx+1}"),
                "start_time": item.get("start_time", ""),
                "end_time": item.get("end_time", ""),
                "reason": item.get("reason", ""),
                "summary_zh": item.get("summary_zh", item.get("reason", "")),
                "quote": item.get("quote", ""),
            }
            for idx, item in enumerate(highlights[:clip_count])
            if item.get("start_time") and item.get("end_time")
        ]
        if not selected_clips:
            return {
                "ok": False,
                "message": "字幕分析完成，但没有得到可切片的时间区间。",
                "video_path": info.get("local_path", ""),
                "subtitle_path": analysis_subtitle,
                "highlights": highlights,
            }

        export_dir = get_workspace_dir_fn("clips", workspace) / f"{Path(info['local_path']).stem}_clips"
        slice_result = run_batch_slice_job_fn(
            info["local_path"],
            selected_clips,
            output_dir=str(export_dir),
            accurate=accurate_slice,
            subtitle_path=analysis_subtitle,
            burn_subtitles=True,
        )
        executed_clips = slice_result.get("clips", []) or selected_clips
        analysis_path = _write_analysis_artifact(
            f"{Path(info['local_path']).stem}_analysis",
            {
                "video_path": info.get("local_path", ""),
                "subtitle_path": analysis_subtitle,
                "highlights": highlights,
                "selected_clips": executed_clips,
            },
            workspace,
        )

        return {
            "ok": bool(slice_result.get("output_paths")),
            "message": "自动化剪辑完成" if slice_result.get("output_paths") else "自动化剪辑执行失败",
            "video_info": info,
            "video_path": info.get("local_path", ""),
            "subtitle_path": analysis_subtitle,
            "analysis_path": analysis_path,
            "subtitle_errors": subtitle_errors,
            "highlights": highlights,
            "selected_clips": executed_clips,
            "slice_result": slice_result,
        }
    except Exception as exc:
        return {"ok": False, "message": f"自动化剪辑异常: {str(exc)[:300]}"}
