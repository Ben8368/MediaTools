"""Video fetch and subtitle download workflows."""

import queue
import threading
from pathlib import Path

from modules.fetcher.analyzer import SubtitleAnalyzer
from modules.fetcher.csv_manager import CSVManager
from modules.fetcher.downloader import VideoDownloader
from modules.fetcher.subtitle import SubtitleProcessor
from services.media_helpers import _normalize_subtitle_outputs
from services.workspace import get_current_workspace


def fetch_video_info(url: str, output_dir: str, naming_template: str, *, downloader_cls=None) -> dict:
    downloader_cls = downloader_cls or VideoDownloader
    downloader = downloader_cls(output_dir, naming_template)
    return downloader.get_video_info(url)

def _build_fetch_state(urls: list[str]) -> dict:
    return {
        "logs": [],
        "task_rows": [],
        "highlight_rows": [],
        "items": [],
        "success_count": 0,
        "current_index": 0,
        "total": len(urls),
        "current_stage": "等待开始",
        "progress_percent": 0.0,
        "progress_text": "等待开始",
    }

def _compute_fetch_progress(total: int, item_index: int, stage: str, stage_progress: float) -> float:
    if total <= 0:
        return 0.0

    item_base = max(item_index - 1, 0) / total
    item_weight = 1 / total

    stage_weights = {
        "获取视频信息": (0.0, 0.08),
        "视频下载中": (0.08, 0.78),
        "字幕下载中": (0.78, 0.92),
        "字幕分析中": (0.92, 0.98),
        "单条完成": (0.98, 1.0),
        "处理失败": (0.98, 1.0),
        "全部完成": (1.0, 1.0),
        "准备开始": (0.0, 0.0),
    }

    start, end = stage_weights.get(stage, (0.0, 0.0))
    within_item = start + (end - start) * max(0.0, min(stage_progress, 1.0))
    return round((item_base + item_weight * within_item) * 100, 1)

def _stage_key(stage: str) -> str:
    if stage.startswith("获取视频信息"):
        return "获取视频信息"
    if stage.startswith("视频下载中"):
        return "视频下载中"
    if stage.startswith("字幕下载中"):
        return "字幕下载中"
    if stage.startswith("字幕分析中"):
        return "字幕分析中"
    if stage.startswith("单条完成"):
        return "单条完成"
    if stage.startswith("处理失败"):
        return "处理失败"
    if stage.startswith("全部完成"):
        return "全部完成"
    if stage.startswith("准备开始"):
        return "准备开始"
    return stage

def _snapshot_fetch_state(state: dict) -> dict:
    subtitle_success = sum(1 for item in state["items"] if item.get("subtitle_status") not in {"未处理", "无字幕或下载失败"})
    summary_lines = [
        f"任务数: {state['total']}",
        f"成功处理: {state['success_count']}",
        f"失败处理: {state['total'] - state['success_count']}",
        f"字幕成功: {subtitle_success}",
        f"当前阶段: {state['current_stage']}",
        f"当前进度: {state['progress_percent']:.1f}%",
    ]
    return {
        "summary_text": "\n".join(summary_lines),
        "logs_text": "\n".join(state["logs"]),
        "task_rows": [row[:] for row in state["task_rows"]],
        "highlight_rows": [row[:] for row in state["highlight_rows"]],
        "items": list(state["items"]),
        "progress_percent": state["progress_percent"],
        "progress_text": state["progress_text"],
    }

def _run_fetch_batch_internal(
    urls: list[str],
    output_dir: str,
    naming_template: str,
    sub_only: bool = False,
    analyze: bool = False,
    emit=None,
    download_video: bool | None = None,
    video_codec_preference: str = "h264",
    subtitle_mode: str = "original_only",
    subtitle_formats: list[str] | None = None,
    cancel_check=None,
    *,
    downloader_cls=None,
    get_current_workspace_fn=None,
) -> dict:
    state = _build_fetch_state(urls)
    downloader_cls = downloader_cls or VideoDownloader
    get_current_workspace_fn = get_current_workspace_fn or get_current_workspace
    workspace = get_current_workspace_fn()
    normalize_to_workspace = Path(output_dir).resolve().is_relative_to(Path(workspace["project_root"]).resolve())
    if download_video is None:
        download_video = not sub_only

    def publish(stage: str | None = None, log_line: str | None = None):
        if stage:
            state["current_stage"] = stage
            state["progress_text"] = stage
            state["progress_percent"] = _compute_fetch_progress(
                state["total"],
                max(current_item["index"], 1),
                _stage_key(stage),
                0.0 if _stage_key(stage) not in {"单条完成", "处理失败", "全部完成"} else 1.0,
            )
        if log_line:
            state["logs"].append(log_line)
        snapshot = _snapshot_fetch_state(state)
        if emit:
            emit(snapshot)
        return snapshot

    current_item = {"index": 0, "title": ""}

    def on_progress(message: str):
        if message.startswith("__DOWNLOAD_PERCENT__:"):
            try:
                raw_percent = float(message.split(":", 1)[1]) / 100
            except ValueError:
                return
            stage_name = f"视频下载中 ({current_item['index']}/{len(urls)})"
            state["current_stage"] = stage_name
            state["progress_text"] = f"{stage_name} {raw_percent * 100:.1f}%"
            state["progress_percent"] = _compute_fetch_progress(
                state["total"],
                max(current_item["index"], 1),
                "视频下载中",
                raw_percent,
            )
            if emit:
                emit(_snapshot_fetch_state(state))
            return
        prefix = f"[{current_item['index']}/{len(urls)}] {current_item['title']}" if current_item["index"] else "[progress]"
        publish(log_line=f"{prefix}: {message}")

    downloader = downloader_cls(output_dir, naming_template, progress_callback=on_progress)
    processor = SubtitleProcessor()
    csv_mgr = CSVManager()

    publish("准备开始")

    for idx, url in enumerate(urls, 1):
        # 检查是否应该取消
        if cancel_check and cancel_check():
            publish("任务已取消", f"任务在处理第 {idx} 个URL时被取消")
            state["current_stage"] = "任务已取消"
            return publish("任务已取消")

        highlights = []
        current_item["index"] = idx
        current_item["title"] = url
        try:
            publish(f"获取视频信息 ({idx}/{len(urls)})", f"[{idx}/{len(urls)}] 处理: {url}")
            info = downloader.get_video_info(url)
            current_item["title"] = info.get("title", url)
            publish(log_line=f"标题: {info.get('title', '未知')}")
            subtitle_status = "未处理"
            video_status = "跳过视频"

            if download_video:
                # 再次检查取消标志
                if cancel_check and cancel_check():
                    publish("任务已取消", "任务在下载视频前被取消")
                    return publish("任务已取消")

                publish(f"视频下载中 ({idx}/{len(urls)})")
                info = downloader.download_video(url, idx, info=info, codec_preference=video_codec_preference)
                if info.get("video_status") == "failed":
                    publish(log_line=f"视频下载失败: {info.get('video_error', '')[:100]}")
                    video_status = "下载失败"
                else:
                    publish(log_line=f"视频下载成功: {info.get('local_path', '')}")
                    video_status = "下载成功"
            else:
                info["video_status"] = "skipped"
                info["video_error"] = ""

            if subtitle_mode == "none":
                subtitle_result = {"original": {}, "zh": {}}
                subtitle_status = "未下载字幕"
            else:
                # 再次检查取消标志
                if cancel_check and cancel_check():
                    publish("任务已取消", "任务在下载字幕前被取消")
                    return publish("任务已取消")

                publish(f"字幕下载中 ({idx}/{len(urls)})")
                subtitle_result = downloader.download_subtitles_only(
                    url,
                    idx,
                    info=info,
                    subtitle_mode=subtitle_mode,
                    subtitle_formats=subtitle_formats,
                )
                if normalize_to_workspace:
                    subtitle_result = _normalize_subtitle_outputs(subtitle_result, workspace)
            analyze_srt = ""

            original_outputs = subtitle_result.get("original", {})
            zh_outputs = subtitle_result.get("zh", {})
            subtitle_errors = subtitle_result.get("errors", [])
            primary_original = original_outputs.get("srt") or original_outputs.get("vtt") or ""
            primary_zh = zh_outputs.get("srt") or zh_outputs.get("vtt") or ""

            if primary_original:
                publish(log_line=f"原字幕输出: {Path(primary_original).name}")
                analyze_srt = original_outputs.get("srt", "")
                subtitle_status = "原语言字幕"
                info["subtitle_path"] = primary_original

            if primary_zh:
                publish(log_line=f"中文字幕输出: {Path(primary_zh).name}")
                info["chinese_subs_status"] = "已下载"
                if not analyze_srt:
                    analyze_srt = zh_outputs.get("srt", "")
                    subtitle_status = "中文字幕"
                    info["subtitle_path"] = primary_zh
                elif subtitle_status == "原语言字幕":
                    subtitle_status = "原语言 + 中文"
            elif primary_original:
                info["chinese_subs_status"] = "仅原语言"
            elif subtitle_mode != "none":
                subtitle_status = "无字幕或下载失败"
                info["chinese_subs_status"] = "无"

            if subtitle_errors:
                info["subtitle_errors"] = subtitle_errors
                publish(log_line=f"字幕警告: {subtitle_errors[0][:160]}")

            if analyze and analyze_srt:
                publish(f"字幕分析中 ({idx}/{len(urls)})")
                analyzer = SubtitleAnalyzer()
                highlights, _ = analyzer.analyze_from_srt(analyze_srt, processor)
                publish(log_line=f"找到 {len(highlights)} 个亮点")

            info["highlights_count"] = len(highlights)
            csv_mgr.add_video(info, highlights if analyze else None)

            for highlight in highlights:
                state["highlight_rows"].append([
                    info.get("title", "未知"),
                    highlight.get("start_time", ""),
                    highlight.get("end_time", ""),
                    highlight.get("category", ""),
                    highlight.get("quote", ""),
                    highlight.get("reason", ""),
                ])

            state["success_count"] += 1
            item = {
                "index": idx,
                "url": url,
                "info": info,
                "video_status": video_status,
                "subtitle_status": subtitle_status,
                "subtitle_errors": subtitle_errors,
                "highlights": highlights,
            }
            state["items"].append(item)
            state["task_rows"].append([
                idx,
                info.get("title", "未知"),
                video_status,
                subtitle_status,
                len(highlights),
                info.get("local_path", "") or info.get("subtitle_path", ""),
            ])
            publish(f"单条完成 ({idx}/{len(urls)})")
        except Exception as exc:
            state["task_rows"].append([idx, url, "失败", "失败", 0, ""])
            publish(f"处理失败 ({idx}/{len(urls)})", f"[{idx}] 处理失败: {str(exc)[:200]}")

    return publish("全部完成")

def run_fetch_batch(
    urls: list[str],
    output_dir: str,
    naming_template: str,
    sub_only: bool = False,
    analyze: bool = False,
    download_video: bool | None = None,
    video_codec_preference: str = "h264",
    subtitle_mode: str = "original_only",
    subtitle_formats: list[str] | None = None,
    cancel_check=None,
    *,
    downloader_cls=None,
    get_current_workspace_fn=None,
) -> dict:
    return _run_fetch_batch_internal(
        urls,
        output_dir,
        naming_template,
        sub_only,
        analyze,
        download_video=download_video,
        video_codec_preference=video_codec_preference,
        subtitle_mode=subtitle_mode,
        subtitle_formats=subtitle_formats,
        cancel_check=cancel_check,
        downloader_cls=downloader_cls,
        get_current_workspace_fn=get_current_workspace_fn,
    )

def run_fetch_batch_stream(
    urls: list[str],
    output_dir: str,
    naming_template: str,
    sub_only: bool = False,
    analyze: bool = False,
    download_video: bool | None = None,
    video_codec_preference: str = "h264",
    subtitle_mode: str = "original_only",
    subtitle_formats: list[str] | None = None,
    cancel_check=None,
    *,
    downloader_cls=None,
    get_current_workspace_fn=None,
):
    updates: queue.Queue = queue.Queue()
    final_result = {}

    def emit(snapshot: dict):
        updates.put(snapshot)

    def worker():
        try:
            final_result["result"] = _run_fetch_batch_internal(
                urls,
                output_dir,
                naming_template,
                sub_only,
                analyze,
                emit=emit,
                download_video=download_video,
                video_codec_preference=video_codec_preference,
                subtitle_mode=subtitle_mode,
                subtitle_formats=subtitle_formats,
                cancel_check=cancel_check,
                downloader_cls=downloader_cls,
                get_current_workspace_fn=get_current_workspace_fn,
            )
        except Exception as exc:
            emit({
                "summary_text": "任务执行异常",
                "logs_text": str(exc),
                "task_rows": [],
                "highlight_rows": [],
                "items": [],
                "progress_percent": 0.0,
                "progress_text": "任务执行异常",
            })
            final_result["result"] = None

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    while thread.is_alive() or not updates.empty():
        try:
            yield updates.get(timeout=0.2)
        except queue.Empty:
            continue

    if final_result.get("result"):
        yield final_result["result"]
