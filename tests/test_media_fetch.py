"""Tests for video fetch batch orchestration."""

from pathlib import Path
from unittest.mock import Mock, patch

import services.media_fetch as media_fetch


class FakeCSVManager:
    instances = []

    def __init__(self):
        self.rows = []
        FakeCSVManager.instances.append(self)

    def add_video(self, info, highlights=None):
        self.rows.append((info.copy(), highlights))


class FakeDownloader:
    instances = []

    def __init__(self, output_dir, naming_template, progress_callback=None):
        self.output_dir = Path(output_dir)
        self.naming_template = naming_template
        self.progress_callback = progress_callback
        FakeDownloader.instances.append(self)

    def get_video_info(self, url):
        return {
            "title": f"Title for {url}",
            "video_id": "vid-1",
            "local_path": "",
            "subtitle_path": "",
        }

    def download_video(self, url, index=1, info=None, codec_preference="h264"):
        if self.progress_callback:
            self.progress_callback("__DOWNLOAD_PERCENT__:50")
            self.progress_callback("download detail")
        info = dict(info or {})
        info["video_status"] = "success"
        info["video_error"] = ""
        info["local_path"] = str(self.output_dir / f"{index}.mp4")
        info["codec_preference"] = codec_preference
        return info

    def download_subtitles_only(
        self,
        url,
        index=1,
        info=None,
        subtitle_mode="original_only",
        subtitle_formats=None,
    ):
        return {
            "original": {"srt": str(self.output_dir / f"{index}.srt")},
            "zh": {},
            "errors": [],
        }


class FailingInfoDownloader(FakeDownloader):
    def get_video_info(self, url):
        raise RuntimeError("metadata failed")


def workspace_for(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return {
        "project_root": str(workspace),
        "subtitles_dir": str(workspace / "subtitles"),
    }


def patch_fetch_runtime(tmp_path, downloader_cls=FakeDownloader):
    return patch.multiple(
        media_fetch,
        VideoDownloader=downloader_cls,
        CSVManager=FakeCSVManager,
        get_current_workspace=Mock(return_value=workspace_for(tmp_path)),
    )


def test_run_fetch_batch_downloads_video_and_subtitle(tmp_path):
    FakeDownloader.instances.clear()
    FakeCSVManager.instances.clear()
    updates = []

    with patch_fetch_runtime(tmp_path):
        result = media_fetch._run_fetch_batch_internal(
            ["https://example.com/video"],
            str(tmp_path / "downloads"),
            "{title}",
            emit=updates.append,
            video_codec_preference="best",
            subtitle_formats=["srt"],
        )

    assert result["progress_text"] == "全部完成"
    assert result["progress_percent"] == 100.0
    assert result["task_rows"][0][2] == "下载成功"
    assert result["task_rows"][0][3] == "原语言字幕"
    assert "视频下载中 (1/1) 50.0%" in [item["progress_text"] for item in updates]
    assert FakeDownloader.instances[0].naming_template == "{title}"
    assert FakeCSVManager.instances[0].rows[0][0]["codec_preference"] == "best"


def test_run_fetch_batch_subtitle_mode_none_skips_subtitle_download(tmp_path):
    with patch_fetch_runtime(tmp_path):
        result = media_fetch._run_fetch_batch_internal(
            ["https://example.com/video"],
            str(tmp_path / "downloads"),
            "{title}",
            download_video=False,
            subtitle_mode="none",
        )

    assert result["task_rows"][0][2] == "跳过视频"
    assert result["task_rows"][0][3] == "未下载字幕"
    assert result["items"][0]["info"]["video_status"] == "skipped"


def test_run_fetch_batch_analyzes_subtitles_when_requested(tmp_path):
    analyzer = Mock()
    analyzer.analyze_from_srt.return_value = (
        [
            {
                "start_time": "00:00:01",
                "end_time": "00:00:05",
                "category": "亮点",
                "quote": "hello",
                "reason": "strong hook",
            }
        ],
        {},
    )

    with patch_fetch_runtime(tmp_path), patch.object(media_fetch, "SubtitleAnalyzer", Mock(return_value=analyzer)):
        result = media_fetch._run_fetch_batch_internal(
            ["https://example.com/video"],
            str(tmp_path / "downloads"),
            "{title}",
            analyze=True,
        )

    assert result["task_rows"][0][4] == 1
    assert result["highlight_rows"][0][3] == "亮点"
    analyzer.analyze_from_srt.assert_called_once()


def test_run_fetch_batch_can_cancel_before_first_item(tmp_path):
    with patch_fetch_runtime(tmp_path):
        result = media_fetch._run_fetch_batch_internal(
            ["https://example.com/video"],
            str(tmp_path / "downloads"),
            "{title}",
            cancel_check=lambda: True,
        )

    assert result["progress_text"] == "任务已取消"
    assert result["task_rows"] == []
    assert "任务在处理第 1 个URL时被取消" in result["logs_text"]


def test_run_fetch_batch_records_item_failure_and_continues(tmp_path):
    with patch_fetch_runtime(tmp_path, downloader_cls=FailingInfoDownloader):
        result = media_fetch._run_fetch_batch_internal(
            ["https://example.com/bad"],
            str(tmp_path / "downloads"),
            "{title}",
        )

    assert result["progress_text"] == "全部完成"
    assert result["task_rows"] == [[1, "https://example.com/bad", "失败", "失败", 0, ""]]
    assert "metadata failed" in result["logs_text"]


def test_run_fetch_batch_stream_yields_error_snapshot_on_worker_exception(tmp_path):
    with patch.object(media_fetch, "_run_fetch_batch_internal", side_effect=RuntimeError("boom")):
        updates = list(
            media_fetch.run_fetch_batch_stream(
                ["https://example.com/video"],
                str(tmp_path / "downloads"),
                "{title}",
            )
        )

    assert len(updates) == 1
    assert updates[0]["progress_text"] == "任务执行异常"
    assert updates[0]["logs_text"] == "boom"
