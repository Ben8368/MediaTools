"""Compatibility facade for MediaTools media workflows.

The implementation lives in focused modules so the service surface stays small
while existing imports from services.media continue to work.
"""

from modules.encoder.transcoder import Transcoder
from modules.fetcher.downloader import VideoDownloader
from services.media_decrypt import (
    build_umcli,
    get_ffmpeg_status_text,
    get_um_status_text,
    get_ytdlp_status_text,
    run_decrypt_job,
)
from services.media_fetch import (
    run_fetch_batch,
    run_fetch_batch_stream,
)
from services.workspace import get_current_workspace, get_workspace_dir

from . import media_encoding as _media_encoding
from . import media_fetch as _media_fetch
from . import media_workflows as _media_workflows


def fetch_video_info(url: str, output_dir: str, naming_template: str) -> dict:
    return _media_fetch.fetch_video_info(url, output_dir, naming_template, downloader_cls=VideoDownloader)


def run_transcode_job(
    input_path: str,
    output_path: str | None,
    codec: str,
    crf: int,
    preset: str,
    vcodec: str,
    acodec: str,
    progress_callback=None,
    cancel_check=None,
) -> dict:
    return _media_encoding.run_transcode_job(
        input_path,
        output_path,
        codec,
        crf,
        preset,
        vcodec,
        acodec,
        progress_callback=progress_callback,
        cancel_check=cancel_check,
        transcoder_cls=Transcoder,
        get_current_workspace_fn=get_current_workspace,
    )


def run_slice_job(
    input_path: str,
    start_time: str,
    end_time: str,
    output_path: str | None = None,
    accurate: bool = True,
    subtitle_path: str | None = None,
    burn_subtitles: bool = False,
) -> dict:
    return _media_encoding.run_slice_job(
        input_path,
        start_time,
        end_time,
        output_path=output_path,
        accurate=accurate,
        subtitle_path=subtitle_path,
        burn_subtitles=burn_subtitles,
        transcoder_cls=Transcoder,
        get_current_workspace_fn=get_current_workspace,
    )


def run_batch_slice_job(
    input_path: str,
    clips: list[dict],
    output_dir: str | None = None,
    accurate: bool = True,
    start_padding: float = 0.8,
    end_padding: float = 1.0,
    subtitle_path: str | None = None,
    burn_subtitles: bool = False,
) -> dict:
    return _media_encoding.run_batch_slice_job(
        input_path,
        clips,
        output_dir=output_dir,
        accurate=accurate,
        start_padding=start_padding,
        end_padding=end_padding,
        subtitle_path=subtitle_path,
        burn_subtitles=burn_subtitles,
        get_current_workspace_fn=get_current_workspace,
        get_workspace_dir_fn=get_workspace_dir,
        run_slice_job_fn=run_slice_job,
    )


def run_fetch_analyze_slice_job(*args, **kwargs) -> dict:
    return _media_workflows.run_fetch_analyze_slice_job(
        *args,
        **kwargs,
        downloader_cls=VideoDownloader,
        subtitle_processor_cls=_media_workflows.SubtitleProcessor,
        subtitle_analyzer_cls=_media_workflows.SubtitleAnalyzer,
        run_batch_slice_job_fn=run_batch_slice_job,
        get_current_workspace_fn=get_current_workspace,
        get_workspace_dir_fn=get_workspace_dir,
    )

__all__ = [
    "fetch_video_info",
    "run_fetch_batch",
    "run_fetch_batch_stream",
    "run_transcode_job",
    "run_slice_job",
    "run_batch_slice_job",
    "run_fetch_analyze_slice_job",
    "run_decrypt_job",
    "get_ytdlp_status_text",
    "get_ffmpeg_status_text",
    "get_um_status_text",
    "build_umcli",
]
