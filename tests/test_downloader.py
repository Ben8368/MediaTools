"""Tests for video downloader"""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


class TestVideoDownloader(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("modules.fetcher.downloader.YtdlpAdapter")
    @patch("modules.fetcher.downloader.FFmpegAdapter")
    def test_get_video_info_success(self, mock_ffmpeg, mock_ytdlp_class):
        mock_ytdlp = Mock()
        mock_result = Mock(returncode=0, stdout=json.dumps({
            "id": "test123",
            "title": "Test Video",
            "duration": 120,
            "formats": [{"vcodec": "h264", "acodec": "aac", "ext": "mp4"}]
        }), stderr="")
        mock_ytdlp.run.return_value = mock_result
        mock_ytdlp_class.return_value = mock_ytdlp

        from modules.fetcher.downloader import VideoDownloader
        downloader = VideoDownloader(self.temp_dir, "{title}")
        info = downloader.get_video_info("https://example.com/video")

        self.assertEqual(info["video_id"], "test123")
        self.assertEqual(info["title"], "Test Video")

    @patch("modules.fetcher.downloader.YtdlpAdapter")
    @patch("modules.fetcher.downloader.FFmpegAdapter")
    def test_normalize_info(self, mock_ffmpeg, mock_ytdlp_class):
        mock_ytdlp_class.return_value = Mock()

        from modules.fetcher.downloader import VideoDownloader
        downloader = VideoDownloader(self.temp_dir, "{title}")

        raw_info = {
            "id": "abc",
            "title": "My Video",
            "duration": 300,
            "formats": [{"vcodec": "h264", "acodec": "aac", "ext": "mp4", "filesize": 1048576}]
        }
        normalized = downloader._normalize_info(raw_info)

        self.assertEqual(normalized["video_id"], "abc")
        self.assertEqual(normalized["title"], "My Video")
        self.assertEqual(normalized["file_size_mb"], 1.0)

    @patch("modules.fetcher.downloader.YtdlpAdapter")
    @patch("modules.fetcher.downloader.FFmpegAdapter")
    def test_sanitize_filename(self, mock_ffmpeg, mock_ytdlp_class):
        mock_ytdlp_class.return_value = Mock()

        from modules.fetcher.downloader import VideoDownloader
        downloader = VideoDownloader(self.temp_dir, "{title}")

        result = downloader._sanitize_filename("Test<>:Video|?*")
        self.assertNotIn("<", result)
        self.assertNotIn(">", result)
        self.assertNotIn(":", result)

    @patch("modules.fetcher.downloader.YtdlpAdapter")
    @patch("modules.fetcher.downloader.FFmpegAdapter")
    def test_apply_naming_template(self, mock_ffmpeg, mock_ytdlp_class):
        mock_ytdlp_class.return_value = Mock()

        from modules.fetcher.downloader import VideoDownloader
        downloader = VideoDownloader(self.temp_dir, "{index}_{title}")

        info = {"title": "Test", "uploader": "User", "video_id": "123", "duration": 100, "language": "en", "upload_date": "20240101"}
        result = downloader._apply_naming_template(info, 5)

        self.assertIn("005", result)
        self.assertIn("Test", result)

    @patch("modules.fetcher.downloader.YtdlpAdapter")
    @patch("modules.fetcher.downloader.FFmpegAdapter")
    def test_video_format_selector_best(self, mock_ffmpeg, mock_ytdlp_class):
        mock_ytdlp_class.return_value = Mock()

        from modules.fetcher.downloader import VideoDownloader
        downloader = VideoDownloader(self.temp_dir, "{title}")

        result = downloader._video_format_selector("best")
        self.assertEqual(result, "bestvideo+bestaudio/best")

    @patch("modules.fetcher.downloader.YtdlpAdapter")
    @patch("modules.fetcher.downloader.FFmpegAdapter")
    def test_video_format_selector_h264(self, mock_ffmpeg, mock_ytdlp_class):
        mock_ytdlp_class.return_value = Mock()

        from modules.fetcher.downloader import VideoDownloader
        downloader = VideoDownloader(self.temp_dir, "{title}")

        result = downloader._video_format_selector("h264")
        self.assertIn("vcodec^=avc1", result)
        self.assertNotIn("/best[ext=mp4]/best", result)

    @patch("modules.fetcher.downloader.YtdlpAdapter")
    @patch("modules.fetcher.downloader.FFmpegAdapter")
    def test_prune_duplicate_subtitle_outputs_prefers_srt(self, mock_ffmpeg, mock_ytdlp_class):
        mock_ytdlp_class.return_value = Mock()

        from modules.fetcher.downloader import VideoDownloader
        downloader = VideoDownloader(self.temp_dir, "{title}")

        srt_path = Path(self.temp_dir) / "clip.en.srt"
        vtt_path = Path(self.temp_dir) / "clip.en.vtt"
        srt_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nhello\n", encoding="utf-8")
        vtt_path.write_text("WEBVTT\n\n00:00.000 --> 00:01.000\nhello\n", encoding="utf-8")

        outputs = downloader._prune_duplicate_subtitle_outputs(
            {"original": {"srt": str(srt_path), "vtt": str(vtt_path)}, "zh": {}}
        )

        self.assertEqual(outputs["original"]["srt"], str(srt_path))
        self.assertNotIn("vtt", outputs["original"])
        self.assertFalse(vtt_path.exists())

    @patch("modules.fetcher.downloader.YtdlpAdapter")
    @patch("modules.fetcher.downloader.FFmpegAdapter")
    def test_ensure_srt_subtitle_outputs_converts_vtt_with_deduplication(self, mock_ffmpeg, mock_ytdlp_class):
        mock_ytdlp_class.return_value = Mock()

        from modules.fetcher.downloader import VideoDownloader
        downloader = VideoDownloader(self.temp_dir, "{title}")

        vtt_path = Path(self.temp_dir) / "clip.en.vtt"
        vtt_path.write_text(
            """WEBVTT

00:00:00.000 --> 00:00:02.000
hello world from

00:00:02.000 --> 00:00:04.000
hello world from youtube
""",
            encoding="utf-8",
        )
        errors = []

        downloader._ensure_srt_subtitle_outputs("clip", ["srt"], errors)

        srt_path = Path(self.temp_dir) / "clip.en.srt"
        self.assertTrue(srt_path.exists())
        srt_text = srt_path.read_text(encoding="utf-8")
        # Rolling-window cues are now split: prefix kept in seg 1, new tail in seg 2.
        self.assertIn("hello world from", srt_text)
        self.assertIn("youtube", srt_text)
        self.assertEqual(len([b for b in srt_text.strip().split("\n\n") if b.strip()]), 2)
        self.assertEqual(errors, [])

    @patch("modules.fetcher.downloader.YtdlpAdapter")
    @patch("modules.fetcher.downloader.FFmpegAdapter")
    def test_get_video_info_nonzero_exit_raises(self, mock_ffmpeg, mock_ytdlp_class):
        mock_ytdlp = Mock()
        mock_ytdlp.run.return_value = Mock(returncode=1, stdout="", stderr="ERROR: unavailable")
        mock_ytdlp_class.return_value = mock_ytdlp

        from modules.fetcher.downloader import VideoDownloader
        downloader = VideoDownloader(self.temp_dir, "{title}")

        with self.assertRaisesRegex(RuntimeError, "unavailable"):
            downloader.get_video_info("https://example.com/video")

    @patch("modules.fetcher.downloader.YtdlpAdapter")
    @patch("modules.fetcher.downloader.FFmpegAdapter")
    def test_get_video_info_invalid_json_raises(self, mock_ffmpeg, mock_ytdlp_class):
        mock_ytdlp = Mock()
        mock_ytdlp.run.return_value = Mock(returncode=0, stdout="not-json", stderr="")
        mock_ytdlp_class.return_value = mock_ytdlp

        from modules.fetcher.downloader import VideoDownloader
        downloader = VideoDownloader(self.temp_dir, "{title}")

        with self.assertRaisesRegex(RuntimeError, "解析视频信息失败"):
            downloader.get_video_info("https://example.com/video")

    @patch("modules.fetcher.downloader.subprocess.run")
    @patch("modules.fetcher.downloader.YtdlpAdapter")
    @patch("modules.fetcher.downloader.FFmpegAdapter")
    def test_download_video_success_sets_local_path(self, mock_ffmpeg, mock_ytdlp_class, mock_run):
        mock_ffmpeg.return_value.get_ffmpeg_location.return_value = str(Path(self.temp_dir) / "ffmpeg")
        mock_ytdlp = Mock()
        mock_ytdlp.build_command.return_value = ["yt-dlp", "https://example.com/video"]
        mock_ytdlp_class.return_value = mock_ytdlp
        mock_run.return_value = Mock(returncode=0)

        from modules.fetcher.downloader import VideoDownloader
        downloader = VideoDownloader(self.temp_dir, "{title}")
        expected = Path(self.temp_dir) / "Good.mp4"
        expected.write_bytes(b"video")

        result = downloader.download_video(
            "https://example.com/video",
            info={"title": "Good", "video_id": "good"},
        )

        self.assertEqual(result["video_status"], "success")
        self.assertEqual(Path(result["local_path"]), expected)
        self.assertIn("--ffmpeg-location", mock_ytdlp.build_command.call_args.args[0])

    @patch("modules.fetcher.downloader.subprocess.run")
    @patch("modules.fetcher.downloader.YtdlpAdapter")
    @patch("modules.fetcher.downloader.FFmpegAdapter")
    def test_download_video_failure_reads_log_tail(self, mock_ffmpeg, mock_ytdlp_class, mock_run):
        mock_ytdlp = Mock()
        mock_ytdlp.build_command.return_value = ["yt-dlp", "https://example.com/video"]
        mock_ytdlp_class.return_value = mock_ytdlp

        def fake_run(*args, **kwargs):
            kwargs["stdout"].write("line one\nERROR: no formats\n")
            return Mock(returncode=1)

        mock_run.side_effect = fake_run

        from modules.fetcher.downloader import VideoDownloader
        downloader = VideoDownloader(self.temp_dir, "{title}")
        result = downloader.download_video(
            "https://example.com/video",
            info={"title": "Bad", "video_id": "bad"},
        )

        self.assertEqual(result["video_status"], "failed")
        self.assertIn("no formats", result["video_error"])
        self.assertEqual(result["local_path"], "")

    @patch("modules.fetcher.downloader.subprocess.run")
    @patch("modules.fetcher.downloader.YtdlpAdapter")
    @patch("modules.fetcher.downloader.FFmpegAdapter")
    def test_download_video_timeout_records_failure(self, mock_ffmpeg, mock_ytdlp_class, mock_run):
        mock_ytdlp = Mock()
        mock_ytdlp.build_command.return_value = ["yt-dlp"]
        mock_ytdlp_class.return_value = mock_ytdlp
        mock_run.side_effect = subprocess.TimeoutExpired("yt-dlp", 3600)

        from modules.fetcher.downloader import VideoDownloader
        downloader = VideoDownloader(self.temp_dir, "{title}")
        result = downloader.download_video(
            "https://example.com/video",
            info={"title": "Slow", "video_id": "slow"},
        )

        self.assertEqual(result["video_status"], "failed")
        self.assertEqual(result["video_error"], "下载超时")

    @patch("modules.fetcher.downloader.YtdlpAdapter")
    @patch("modules.fetcher.downloader.FFmpegAdapter")
    def test_collect_subtitle_outputs_splits_original_and_chinese(self, mock_ffmpeg, mock_ytdlp_class):
        mock_ytdlp_class.return_value = Mock()

        from modules.fetcher.downloader import VideoDownloader
        downloader = VideoDownloader(self.temp_dir, "{title}")
        (Path(self.temp_dir) / "clip.en.srt").write_text("original", encoding="utf-8")
        (Path(self.temp_dir) / "clip.zh-Hans.vtt").write_text("zh", encoding="utf-8")

        outputs = downloader._collect_subtitle_outputs("clip")

        self.assertIn("srt", outputs["original"])
        self.assertIn("vtt", outputs["zh"])

    @patch("modules.fetcher.downloader.subprocess.run")
    @patch("modules.fetcher.downloader.YtdlpAdapter")
    @patch("modules.fetcher.downloader.FFmpegAdapter")
    def test_download_subtitle_family_records_cli_errors(self, mock_ffmpeg, mock_ytdlp_class, mock_run):
        mock_ytdlp = Mock()
        mock_ytdlp.build_command.return_value = ["yt-dlp"]
        mock_ytdlp_class.return_value = mock_ytdlp
        mock_run.return_value = Mock(returncode=1, stderr="warning\nERROR: subtitles unavailable")

        from modules.fetcher.downloader import VideoDownloader
        downloader = VideoDownloader(self.temp_dir, "{title}")
        errors = []

        downloader._download_subtitle_family(
            "https://example.com/video",
            str(Path(self.temp_dir) / "clip.%(ext)s"),
            "en",
            ["srt"],
            errors,
            include_manual=True,
            include_auto=False,
        )

        self.assertEqual(errors, ["en/srt: ERROR: subtitles unavailable"])
        built_cmd = mock_ytdlp.build_command.call_args.args[0]
        self.assertIn("--sub-format", built_cmd)
        self.assertIn("vtt", built_cmd)
        self.assertNotIn("--convert-subs", built_cmd)

    @patch("modules.fetcher.downloader.subprocess.run")
    @patch("modules.fetcher.downloader.YtdlpAdapter")
    @patch("modules.fetcher.downloader.FFmpegAdapter")
    def test_download_subtitle_family_records_exceptions(self, mock_ffmpeg, mock_ytdlp_class, mock_run):
        mock_ytdlp = Mock()
        mock_ytdlp.build_command.return_value = ["yt-dlp"]
        mock_ytdlp_class.return_value = mock_ytdlp
        mock_run.side_effect = RuntimeError("boom")

        from modules.fetcher.downloader import VideoDownloader
        downloader = VideoDownloader(self.temp_dir, "{title}")
        errors = []

        downloader._download_subtitle_family(
            "https://example.com/video",
            str(Path(self.temp_dir) / "clip.%(ext)s"),
            "en",
            ["vtt"],
            errors,
            include_manual=False,
            include_auto=True,
        )

        self.assertEqual(errors, ["en/vtt: boom"])

    @patch("modules.fetcher.downloader.YtdlpAdapter")
    @patch("modules.fetcher.downloader.FFmpegAdapter")
    def test_extract_error_detail_uses_last_error_line(self, mock_ffmpeg, mock_ytdlp_class):
        mock_ytdlp_class.return_value = Mock()

        from modules.fetcher.downloader import VideoDownloader
        downloader = VideoDownloader(self.temp_dir, "{title}")

        detail = downloader._extract_error_detail("first\nERROR: one\nERROR: two\n")
        self.assertEqual(detail, "ERROR: two")


if __name__ == "__main__":
    unittest.main()
