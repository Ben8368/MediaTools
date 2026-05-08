"""Transcode and clipping workflows."""

import re
from pathlib import Path

from backend.services.media.helpers import (
    _default_slice_output_path,
    _default_transcode_output_path,
    _ensure_explicit_output_path,
)
from backend.services.workspace import get_current_workspace, get_workspace_dir
from modules.encoder.transcoder import Transcoder


def _normalize_codec(codec: str) -> str:
    aliases = {
        "Audio Only": "提取音频",
        "audio_only": "提取音频",
        "extract_audio": "提取音频",
    }
    return aliases.get((codec or "").strip(), (codec or "").strip())

def run_transcode_job(input_path: str, output_path: str | None, codec: str, crf: int, preset: str, vcodec: str, acodec: str, progress_callback=None, cancel_check=None, *, transcoder_cls=None, get_current_workspace_fn=None) -> dict:
    transcoder_cls = transcoder_cls or Transcoder
    get_current_workspace_fn = get_current_workspace_fn or get_current_workspace
    transcoder = transcoder_cls()
    workspace = get_current_workspace_fn()

    if not input_path.strip():
        return {
            "log": "请输入文件路径",
            "summary_rows": [["状态", "未开始"]],
            "output_path": "",
            "download_value": None,
        }

    if not transcoder.ffmpeg.is_available():
        return {
            "log": f"FFmpeg 未安装，请放置于: {transcoder.ffmpeg.bin_dir}",
            "summary_rows": [["状态", "FFmpeg 未安装"]],
            "output_path": "",
            "download_value": None,
        }

    input_path = input_path.strip()
    codec = _normalize_codec(codec)
    output_path = output_path.strip() if output_path and output_path.strip() else None
    output_path = _ensure_explicit_output_path(output_path) or _default_transcode_output_path(input_path, codec, workspace)
    progress_msg = f"正在处理: {Path(input_path).name}\n编码模式: {codec}\nCRF: {crf}\nPreset: {preset}"

    try:
        if codec == "H.265 (HEVC)":
            result = transcoder.to_h265(input_path, output_path, crf, progress_callback=progress_callback, cancel_check=cancel_check)
        elif codec == "H.264 (AVC)":
            result = transcoder.to_h264(input_path, output_path, crf, progress_callback=progress_callback, cancel_check=cancel_check)
        elif codec == "提取音频":
            result = transcoder.extract_audio(input_path, output_path, progress_callback=progress_callback, cancel_check=cancel_check)
        else:
            options = {"crf": crf, "preset": preset}
            if vcodec.strip():
                options["vcodec"] = vcodec.strip()
            if acodec.strip():
                options["acodec"] = acodec.strip()
            result = transcoder.transcode(input_path, output_path, progress_callback=progress_callback, cancel_check=cancel_check, **options)

        if result["success"]:
            out_path = result["output_path"]
            out_file = Path(out_path)
            summary_rows = [
                ["状态", "成功"],
                ["输入文件", Path(input_path).name],
                ["输出文件", out_file.name],
                ["编码模式", codec],
                ["输出大小", f"{round(out_file.stat().st_size / (1024 * 1024), 2)} MB" if out_file.exists() else "未知"],
            ]
            progress_msg += f"\n\n转码成功!\n输出文件: {out_path}"
            return {
                "log": progress_msg,
                "summary_rows": summary_rows,
                "output_path": out_path,
                "download_value": out_path,
            }

        progress_msg += f"\n\n转码失败: {result['error'][:200]}"
        return {
            "log": progress_msg,
            "summary_rows": [["状态", "失败"], ["错误", result["error"][:200]]],
            "output_path": "",
            "download_value": None,
        }
    except Exception as exc:
        return {
            "log": f"转码异常: {str(exc)[:200]}",
            "summary_rows": [["状态", "异常"], ["错误", str(exc)[:200]]],
            "output_path": "",
            "download_value": None,
        }

def _time_to_seconds(value: str) -> int | None:
    raw = value.strip()
    if not raw:
        return None
    parts = raw.replace(",", ".").split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(float(parts[2]))
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(float(parts[1]))
        if len(parts) == 1:
            return int(float(parts[0]))
    except ValueError:
        return None
    return None

def _seconds_to_timestamp(seconds: float) -> str:
    total_ms = max(int(round(seconds * 1000)), 0)
    hours = total_ms // 3600000
    minutes = (total_ms % 3600000) // 60000
    secs = (total_ms % 60000) // 1000
    millis = total_ms % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

def run_slice_job(input_path: str, start_time: str, end_time: str, output_path: str | None = None, subtitle_path: str | None = None, burn_subtitles: bool = False, *, transcoder_cls=None, get_current_workspace_fn=None) -> dict:
    transcoder_cls = transcoder_cls or Transcoder
    get_current_workspace_fn = get_current_workspace_fn or get_current_workspace
    transcoder = transcoder_cls()
    workspace = get_current_workspace_fn()

    if not input_path.strip():
        return {
            "log": "请输入视频文件路径",
            "summary_rows": [["状态", "未开始"]],
            "output_path": "",
            "download_value": None,
        }

    if not start_time.strip() or not end_time.strip():
        return {
            "log": "请输入开始时间和结束时间",
            "summary_rows": [["状态", "未开始"]],
            "output_path": "",
            "download_value": None,
        }

    start_seconds = _time_to_seconds(start_time)
    end_seconds = _time_to_seconds(end_time)
    if start_seconds is None or end_seconds is None:
        return {
            "log": "时间格式无效，请使用 00:00:10 或 75 这类格式",
            "summary_rows": [["状态", "失败"], ["错误", "时间格式无效"]],
            "output_path": "",
            "download_value": None,
        }
    if end_seconds <= start_seconds:
        return {
            "log": "结束时间必须大于开始时间",
            "summary_rows": [["状态", "失败"], ["错误", "时间区间无效"]],
            "output_path": "",
            "download_value": None,
        }

    output_path = output_path.strip() if output_path and output_path.strip() else None
    output_path = _ensure_explicit_output_path(output_path) or _default_slice_output_path(input_path, start_time, end_time, workspace)
    subtitle_text = "带原字幕" if burn_subtitles and subtitle_path else "不带字幕"
    progress_msg = f"正在切片: {Path(input_path).name}\n字幕: {subtitle_text}\n开始: {start_time}\n结束: {end_time}"

    try:
        result = transcoder.slice_video(input_path.strip(), start_time.strip(), end_time.strip(), output_path, subtitle_path=subtitle_path, burn_subtitles=burn_subtitles)
        if result["success"]:
            out_path = result["output_path"]
            out_file = Path(out_path)
            duration = end_seconds - start_seconds
            summary_rows = [
                ["状态", "成功"],
                ["字幕", subtitle_text],
                ["输入文件", Path(input_path).name],
                ["输出文件", out_file.name],
                ["片段时长", f"{duration} 秒"],
            ]
            progress_msg += f"\n\n切片成功!\n输出文件: {out_path}"
            return {
                "log": progress_msg,
                "summary_rows": summary_rows,
                "output_path": out_path,
                "download_value": out_path,
            }

        progress_msg += f"\n\n切片失败: {result['error'][:200]}"
        return {
            "log": progress_msg,
            "summary_rows": [["状态", "失败"], ["错误", result["error"][:200]]],
            "output_path": "",
            "download_value": None,
        }
    except Exception as exc:
        return {
            "log": f"切片异常: {str(exc)[:200]}",
            "summary_rows": [["状态", "异常"], ["错误", str(exc)[:200]]],
            "output_path": "",
            "download_value": None,
        }

def run_batch_slice_job(input_path: str, clips: list[dict], output_dir: str | None = None, start_padding: float = 0.8, end_padding: float = 1.0, subtitle_path: str | None = None, burn_subtitles: bool = False, *, get_current_workspace_fn=None, get_workspace_dir_fn=None, run_slice_job_fn=None) -> dict:
    if not input_path.strip():
        return {
            "log": "请输入视频文件路径",
            "summary_rows": [["状态", "未开始"]],
            "output_paths": [],
        }

    if not clips:
        return {
            "log": "没有可执行的切片区间",
            "summary_rows": [["状态", "未开始"]],
            "output_paths": [],
        }

    input_file = Path(input_path)
    get_current_workspace_fn = get_current_workspace_fn or get_current_workspace
    get_workspace_dir_fn = get_workspace_dir_fn or get_workspace_dir
    run_slice_job_fn = run_slice_job_fn or run_slice_job
    workspace = get_current_workspace_fn()
    target_dir = Path(output_dir) if output_dir else get_workspace_dir_fn("clips", workspace) / f"{input_file.stem}_clips"
    target_dir.mkdir(parents=True, exist_ok=True)

    outputs = []
    logs = []
    executed_clips = []
    for idx, clip in enumerate(clips, 1):
        start_time = clip.get("start_time", "")
        end_time = clip.get("end_time", "")
        if not start_time or not end_time:
            continue
        start_seconds = _time_to_seconds(start_time)
        end_seconds = _time_to_seconds(end_time)
        if start_seconds is None or end_seconds is None:
            continue
        padded_start = _seconds_to_timestamp(max(start_seconds - start_padding, 0))
        padded_end = _seconds_to_timestamp(max(end_seconds + end_padding, 0))
        clip_title = clip.get("title") or clip.get("category") or f"clip_{idx:02d}"
        safe_title = re.sub(r"[^\w\-\u4e00-\u9fff]+", "_", clip_title).strip("_") or f"clip_{idx:02d}"
        output_path = str(target_dir / f"{idx:02d}_{safe_title}.mp4")
        result = run_slice_job_fn(input_path, padded_start, padded_end, output_path=output_path, subtitle_path=subtitle_path, burn_subtitles=burn_subtitles)
        logs.append(result["log"])
        if result.get("output_path"):
            outputs.append(result["output_path"])
            executed_clips.append({
                **clip,
                "actual_start_time": padded_start,
                "actual_end_time": padded_end,
                "burned_subtitles": bool(burn_subtitles and subtitle_path),
                "output_path": result["output_path"],
            })

    return {
        "log": "\n\n".join(logs),
        "summary_rows": [
            ["状态", "成功" if outputs else "失败"],
            ["切片数量", str(len(outputs))],
            ["输出目录", str(target_dir)],
            ["字幕烧录", "是" if burn_subtitles and subtitle_path else "否"],
        ],
        "output_paths": outputs,
        "output_dir": str(target_dir),
        "clips": executed_clips,
    }
