"""Tests for composite media fetch/analyze/slice workflows."""

from pathlib import Path
from unittest.mock import Mock, patch

import backend.services.media_workflows as media_workflows


def workspace(tmp_path):
    root = tmp_path / "workspace"
    downloads = root / "downloads"
    clips = root / "clips"
    analysis = root / "analysis"
    for path in (downloads, clips, analysis):
        path.mkdir(parents=True)
    return {
        "project_root": str(root),
        "downloads_dir": str(downloads),
        "clips_dir": str(clips),
        "analysis_dir": str(analysis),
    }


class FakeDownloader:
    subtitle_result = {"original": {"srt": ""}, "errors": []}
    video_result = None

    def __init__(self, output_dir, naming_template):
        self.output_dir = Path(output_dir)
        self.naming_template = naming_template

    def get_video_info(self, url):
        return {"title": "Source", "video_id": "video-1"}

    def download_video(self, url, index, info=None, codec_preference="h264"):
        if self.video_result is not None:
            return dict(self.video_result)
        info = dict(info or {})
        info["video_status"] = "success"
        info["video_error"] = ""
        info["local_path"] = str(self.output_dir / "source.mp4")
        info["codec_preference"] = codec_preference
        return info

    def download_subtitles_only(self, *args, **kwargs):
        return dict(self.subtitle_result)


def patch_workflow_runtime(tmp_path, *, downloader_cls=FakeDownloader, highlights=None, slice_result=None):
    ws = workspace(tmp_path)
    analyzer = Mock()
    analyzer.analyze_from_srt.return_value = (highlights or [], {})
    processor = Mock()
    processor.convert_vtt_to_srt.return_value = str(Path(ws["downloads_dir"]) / "converted.srt")
    slice_mock = Mock(return_value=slice_result or {"output_paths": [str(Path(ws["clips_dir"]) / "clip.mp4")], "clips": []})
    analyzer_cls = Mock(return_value=analyzer)
    return (
        ws,
        analyzer,
        processor,
        slice_mock,
        analyzer_cls,
        patch.multiple(
            media_workflows,
            get_current_workspace=Mock(return_value=ws),
            get_workspace_dir=Mock(side_effect=lambda key, workspace: Path(workspace[f"{key}_dir"])),
            VideoDownloader=downloader_cls,
            SubtitleProcessor=Mock(return_value=processor),
            SubtitleAnalyzer=analyzer_cls,
            run_batch_slice_job=slice_mock,
        ),
    )


def test_run_fetch_analyze_slice_rejects_empty_url():
    result = media_workflows.run_fetch_analyze_slice_job("   ")

    assert result == {"ok": False, "message": "请输入视频 URL"}


def test_run_fetch_analyze_slice_reports_download_failure(tmp_path):
    class FailingVideoDownloader(FakeDownloader):
        video_result = {"video_status": "failed", "video_error": "network down", "local_path": ""}

    ws, analyzer, processor, slice_mock, analyzer_cls, runtime = patch_workflow_runtime(tmp_path, downloader_cls=FailingVideoDownloader)
    with runtime:
        result = media_workflows.run_fetch_analyze_slice_job(" https://example.com/video ")

    assert result["ok"] is False
    assert "network down" in result["message"]
    analyzer.analyze_from_srt.assert_not_called()


def test_run_fetch_analyze_slice_reports_missing_subtitle(tmp_path):
    class NoSubtitleDownloader(FakeDownloader):
        subtitle_result = {"original": {}, "errors": ["no subtitles"]}

    ws, analyzer, processor, slice_mock, analyzer_cls, runtime = patch_workflow_runtime(tmp_path, downloader_cls=NoSubtitleDownloader)
    with runtime:
        result = media_workflows.run_fetch_analyze_slice_job("https://example.com/video")

    assert result["ok"] is False
    assert result["video_path"].endswith("source.mp4")
    assert result["subtitle_errors"] == ["no subtitles"]
    assert "没有可分析字幕" in result["message"]


def test_run_fetch_analyze_slice_converts_vtt_before_analysis(tmp_path):
    subtitle_path = tmp_path / "caption.vtt"

    class VttDownloader(FakeDownloader):
        subtitle_result = {"original": {"vtt": str(subtitle_path)}, "errors": []}

    highlights = [{"start_time": "00:00:01", "end_time": "00:00:03", "category": "hook"}]
    ws, analyzer, processor, slice_mock, analyzer_cls, runtime = patch_workflow_runtime(tmp_path, downloader_cls=VttDownloader, highlights=highlights)
    with runtime:
        result = media_workflows.run_fetch_analyze_slice_job("https://example.com/video", model="test-model")

    processor.convert_vtt_to_srt.assert_called_once_with(str(subtitle_path))
    analyzer.analyze_from_srt.assert_called_once_with(processor.convert_vtt_to_srt.return_value, processor, model="test-model")
    assert result["ok"] is True
    assert result["subtitle_path"].endswith("converted.srt")


def test_run_fetch_analyze_slice_reports_no_valid_clips(tmp_path):
    class SubtitleDownloader(FakeDownloader):
        subtitle_result = {"original": {"srt": str(tmp_path / "caption.srt")}, "errors": []}

    ws, analyzer, processor, slice_mock, analyzer_cls, runtime = patch_workflow_runtime(
        tmp_path,
        downloader_cls=SubtitleDownloader,
        highlights=[{"start_time": "", "end_time": "00:00:03", "reason": "missing start"}],
    )
    with runtime:
        result = media_workflows.run_fetch_analyze_slice_job("https://example.com/video")

    assert result["ok"] is False
    assert "没有得到可切片" in result["message"]
    assert result["highlights"][0]["reason"] == "missing start"
    slice_mock.assert_not_called()


def test_run_fetch_analyze_slice_success_writes_analysis_and_passes_slice_options(tmp_path):
    class SubtitleDownloader(FakeDownloader):
        subtitle_result = {"original": {"srt": str(tmp_path / "caption.srt")}, "errors": []}

    highlights = [
        {"start_time": "00:00:01", "end_time": "00:00:03", "category": "hook", "quote": "a", "reason": "good"},
        {"start_time": "00:00:04", "end_time": "00:00:08", "category": "payoff", "quote": "b", "summary_zh": "总结"},
        {"start_time": "", "end_time": "00:00:10", "category": "skip"},
    ]
    slice_result = {"output_paths": [str(tmp_path / "clip.mp4")], "clips": [{"title": "rendered"}]}
    ws, analyzer, processor, slice_mock, analyzer_cls, runtime = patch_workflow_runtime(
        tmp_path,
        downloader_cls=SubtitleDownloader,
        highlights=highlights,
        slice_result=slice_result,
    )
    with runtime:
        result = media_workflows.run_fetch_analyze_slice_job(
            "https://example.com/video",
            index=7,
            video_codec_preference="best",
            clip_count=2,
            accurate_slice=False,
            api_key="key",
            base_url="https://api.example.com",
            model="model-a",
        )

    assert result["ok"] is True
    assert result["message"] == "自动化剪辑完成"
    assert Path(result["analysis_path"]).exists()
    assert result["selected_clips"] == [{"title": "rendered"}]
    slice_mock.assert_called_once()
    _, selected_clips = slice_mock.call_args.args[:2]
    assert len(selected_clips) == 2
    assert slice_mock.call_args.kwargs["accurate"] is False
    assert slice_mock.call_args.kwargs["burn_subtitles"] is True
    analyzer_cls.assert_called_once_with(
        api_key="key",
        base_url="https://api.example.com",
        model="model-a",
    )


def test_run_fetch_analyze_slice_catches_unexpected_errors(tmp_path):
    class ExplodingDownloader(FakeDownloader):
        def get_video_info(self, url):
            raise RuntimeError("metadata exploded")

    ws, analyzer, processor, slice_mock, analyzer_cls, runtime = patch_workflow_runtime(tmp_path, downloader_cls=ExplodingDownloader)
    with runtime:
        result = media_workflows.run_fetch_analyze_slice_job("https://example.com/video")

    assert result["ok"] is False
    assert "metadata exploded" in result["message"]
