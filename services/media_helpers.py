"""Shared path and artifact helpers for media workflows."""

import json
import re
import shutil
from pathlib import Path

from services.workspace import derive_output_path, get_workspace_dir, workspace_path


def _ensure_explicit_output_path(path: str | None) -> str | None:
    if not path:
        return None
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return str(output_path)

def _move_file_to_workspace_dir(file_path: str, target_dir: Path) -> str:
    source = Path(file_path)
    if not source.exists():
        return file_path

    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / source.name
    if source.resolve() == target.resolve():
        return str(source)

    counter = 1
    while target.exists():
        target = target_dir / f"{source.stem}_{counter}{source.suffix}"
        counter += 1

    shutil.move(str(source), str(target))
    return str(target)

def _normalize_subtitle_outputs(subtitle_result: dict, workspace: dict) -> dict:
    subtitle_dir = get_workspace_dir("subtitles", workspace)
    normalized = {"original": {}, "zh": {}, "errors": list(subtitle_result.get("errors", []))}
    for bucket in ("original", "zh"):
        for fmt, raw_path in subtitle_result.get(bucket, {}).items():
            normalized[bucket][fmt] = _move_file_to_workspace_dir(raw_path, subtitle_dir)
    return normalized

def _default_transcode_output_path(input_path: str, codec: str, workspace: dict) -> str:
    if codec == "H.265 (HEVC)":
        return str(derive_output_path("transcoded", input_path, suffix=".h265", extension=".mp4", workspace=workspace))
    if codec == "H.264 (AVC)":
        return str(derive_output_path("transcoded", input_path, suffix=".h264", extension=".mp4", workspace=workspace))
    if codec == "提取音频":
        return str(derive_output_path("transcoded", input_path, extension=".mp3", workspace=workspace))
    return str(derive_output_path("transcoded", input_path, suffix=".out", extension=".mp4", workspace=workspace))

def _default_slice_output_path(input_path: str, start_time: str, end_time: str, workspace: dict) -> str:
    safe_start = re.sub(r"[^0-9]", "", start_time)[:12] or "start"
    safe_end = re.sub(r"[^0-9]", "", end_time)[:12] or "end"
    return str(derive_output_path("clips", input_path, suffix=f"_{safe_start}_{safe_end}", extension=".mp4", workspace=workspace))

def _write_analysis_artifact(name: str, payload: dict, workspace: dict) -> str:
    target = workspace_path("analysis", f"{name}.json", workspace=workspace)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(target)
