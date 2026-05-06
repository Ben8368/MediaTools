"""Tests for additional media service functions"""
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


class TestMediaServiceFunctions(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_fetch_video_info(self):
        from services.media import fetch_video_info
        with patch("services.media.VideoDownloader") as mock_dl:
            mock_instance = Mock()
            mock_instance.get_video_info.return_value = {"title": "Test"}
            mock_dl.return_value = mock_instance

            result = fetch_video_info("https://example.com", self.temp_dir, "{title}")
            self.assertEqual(result["title"], "Test")

    def test_time_to_seconds_hhmmss(self):
        from services.media import _time_to_seconds
        self.assertEqual(_time_to_seconds("01:30:45"), 5445)

    def test_time_to_seconds_mmss(self):
        from services.media import _time_to_seconds
        self.assertEqual(_time_to_seconds("05:30"), 330)

    def test_time_to_seconds_ss(self):
        from services.media import _time_to_seconds
        self.assertEqual(_time_to_seconds("45"), 45)

    def test_time_to_seconds_empty(self):
        from services.media import _time_to_seconds
        self.assertIsNone(_time_to_seconds(""))

    def test_time_to_seconds_invalid(self):
        from services.media import _time_to_seconds
        self.assertIsNone(_time_to_seconds("invalid"))

    def test_seconds_to_timestamp(self):
        from services.media import _seconds_to_timestamp
        result = _seconds_to_timestamp(90.5)
        self.assertIn("01:30", result)

    def test_stage_key_mapping(self):
        from services.media import _stage_key
        self.assertEqual(_stage_key("获取视频信息 - test"), "获取视频信息")
        self.assertEqual(_stage_key("视频下载中 50%"), "视频下载中")
        self.assertEqual(_stage_key("字幕下载中"), "字幕下载中")
        self.assertEqual(_stage_key("unknown stage"), "unknown stage")

    def test_snapshot_fetch_state(self):
        from services.media import _snapshot_fetch_state
        state = {
            "logs": ["log1", "log2"],
            "task_rows": [["task", "status"]],
            "highlight_rows": [["time", "text"]],
            "items": [{"subtitle_status": "成功"}],
            "success_count": 1,
            "total": 2,
            "current_stage": "processing",
            "progress_percent": 50.0,
            "progress_text": "50%",
        }
        snapshot = _snapshot_fetch_state(state)
        self.assertIn("summary_text", snapshot)
        self.assertIn("logs_text", snapshot)
        self.assertEqual(len(snapshot["task_rows"]), 1)

    @patch("services.media.Transcoder")
    @patch("services.media.get_current_workspace")
    def test_run_transcode_job_empty_input(self, mock_ws, mock_transcoder):
        mock_ws.return_value = {"transcoded_dir": self.temp_dir}
        from services.media import run_transcode_job
        result = run_transcode_job("", None, "H.264 (AVC)", 23, "medium", "", "")
        self.assertIn("请输入文件路径", result["log"])

    @patch("services.media.Transcoder")
    @patch("services.media.get_current_workspace")
    def test_run_transcode_job_ffmpeg_not_available(self, mock_ws, mock_transcoder_class):
        mock_ws.return_value = {"transcoded_dir": self.temp_dir}
        mock_transcoder = Mock()
        mock_transcoder.ffmpeg.is_available.return_value = False
        mock_transcoder.ffmpeg.bin_dir = "/bin"
        mock_transcoder_class.return_value = mock_transcoder

        from services.media import run_transcode_job
        result = run_transcode_job("/input.mp4", None, "H.264 (AVC)", 23, "medium", "", "")
        self.assertIn("FFmpeg 未安装", result["log"])

    @patch("services.media.Transcoder")
    @patch("services.media.get_current_workspace")
    def test_run_transcode_job_h265_success(self, mock_ws, mock_transcoder_class):
        mock_ws.return_value = {"transcoded_dir": self.temp_dir}

        output_file = Path(self.temp_dir) / "output.mp4"
        output_file.write_bytes(b"\x00" * 1024)

        mock_transcoder = Mock()
        mock_transcoder.ffmpeg.is_available.return_value = True
        mock_transcoder.to_h265.return_value = {
            "success": True,
            "output_path": str(output_file),
            "error": ""
        }
        mock_transcoder_class.return_value = mock_transcoder

        from services.media import run_transcode_job
        result = run_transcode_job("/input.mp4", str(output_file), "H.265 (HEVC)", 23, "medium", "", "")
        self.assertIn("成功", result["summary_rows"][0][1])

    @patch("services.media.Transcoder")
    @patch("services.media.get_current_workspace")
    def test_run_transcode_job_extract_audio(self, mock_ws, mock_transcoder_class):
        mock_ws.return_value = {"transcoded_dir": self.temp_dir}

        output_file = Path(self.temp_dir) / "output.mp3"
        output_file.write_bytes(b"\x00" * 512)

        mock_transcoder = Mock()
        mock_transcoder.ffmpeg.is_available.return_value = True
        mock_transcoder.extract_audio.return_value = {
            "success": True,
            "output_path": str(output_file),
            "error": ""
        }
        mock_transcoder_class.return_value = mock_transcoder

        from services.media import run_transcode_job
        result = run_transcode_job("/input.mp4", str(output_file), "提取音频", 23, "medium", "", "")
        self.assertIn("成功", result["summary_rows"][0][1])


if __name__ == "__main__":
    unittest.main()
