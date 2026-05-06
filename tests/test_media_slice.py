"""Tests for media service slice functions"""
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


class TestSliceJobs(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("services.media.Transcoder")
    @patch("services.media.get_current_workspace")
    def test_run_slice_job_empty_input(self, mock_ws, mock_transcoder):
        mock_ws.return_value = {"clips_dir": self.temp_dir}
        from services.media import run_slice_job
        result = run_slice_job("", "00:00:10", "00:00:20")
        self.assertIn("请输入视频文件路径", result["log"])

    @patch("services.media.Transcoder")
    @patch("services.media.get_current_workspace")
    def test_run_slice_job_empty_times(self, mock_ws, mock_transcoder):
        mock_ws.return_value = {"clips_dir": self.temp_dir}
        from services.media import run_slice_job
        result = run_slice_job("/video.mp4", "", "00:00:20")
        self.assertIn("请输入开始时间和结束时间", result["log"])

    @patch("services.media.Transcoder")
    @patch("services.media.get_current_workspace")
    def test_run_slice_job_invalid_time_format(self, mock_ws, mock_transcoder):
        mock_ws.return_value = {"clips_dir": self.temp_dir}
        from services.media import run_slice_job
        result = run_slice_job("/video.mp4", "invalid", "00:00:20")
        self.assertIn("时间格式无效", result["log"])

    @patch("services.media.Transcoder")
    @patch("services.media.get_current_workspace")
    def test_run_slice_job_end_before_start(self, mock_ws, mock_transcoder):
        mock_ws.return_value = {"clips_dir": self.temp_dir}
        from services.media import run_slice_job
        result = run_slice_job("/video.mp4", "00:00:30", "00:00:10")
        self.assertIn("结束时间必须大于开始时间", result["log"])

    @patch("services.media.Transcoder")
    @patch("services.media.get_current_workspace")
    def test_run_slice_job_success(self, mock_ws, mock_transcoder_class):
        mock_ws.return_value = {"clips_dir": self.temp_dir}

        output_file = Path(self.temp_dir) / "clip.mp4"
        output_file.write_bytes(b"\x00" * 1024)

        mock_transcoder = Mock()
        mock_transcoder.slice_video.return_value = {
            "success": True,
            "output_path": str(output_file),
            "error": ""
        }
        mock_transcoder_class.return_value = mock_transcoder

        from services.media import run_slice_job
        result = run_slice_job("/video.mp4", "00:00:10", "00:00:20", str(output_file))
        self.assertIn("成功", result["summary_rows"][0][1])
        self.assertEqual(result["output_path"], str(output_file))

    @patch("services.media.Transcoder")
    @patch("services.media.get_current_workspace")
    def test_run_slice_job_failure(self, mock_ws, mock_transcoder_class):
        mock_ws.return_value = {"clips_dir": self.temp_dir}

        mock_transcoder = Mock()
        mock_transcoder.slice_video.return_value = {
            "success": False,
            "output_path": "",
            "error": "FFmpeg error"
        }
        mock_transcoder_class.return_value = mock_transcoder

        from services.media import run_slice_job
        result = run_slice_job("/video.mp4", "00:00:10", "00:00:20")
        self.assertIn("失败", result["summary_rows"][0][1])

    @patch("services.media.get_current_workspace")
    @patch("services.media.get_workspace_dir")
    def test_run_batch_slice_job_empty_input(self, mock_ws_dir, mock_ws):
        mock_ws.return_value = {"clips_dir": self.temp_dir}
        from services.media import run_batch_slice_job
        result = run_batch_slice_job("", [])
        self.assertIn("请输入视频文件路径", result["log"])

    @patch("services.media.get_current_workspace")
    @patch("services.media.get_workspace_dir")
    def test_run_batch_slice_job_no_clips(self, mock_ws_dir, mock_ws):
        mock_ws.return_value = {"clips_dir": self.temp_dir}
        from services.media import run_batch_slice_job
        result = run_batch_slice_job("/video.mp4", [])
        self.assertIn("没有可执行的切片区间", result["log"])

    @patch("services.media.run_slice_job")
    @patch("services.media.get_current_workspace")
    @patch("services.media.get_workspace_dir")
    def test_run_batch_slice_job_success(self, mock_ws_dir, mock_ws, mock_slice):
        mock_ws.return_value = {"clips_dir": self.temp_dir}
        mock_ws_dir.return_value = Path(self.temp_dir)

        mock_slice.return_value = {
            "log": "success",
            "output_path": "/output/clip1.mp4",
            "summary_rows": [["状态", "成功"]]
        }

        clips = [
            {"start_time": "00:00:10", "end_time": "00:00:20", "title": "clip1"},
            {"start_time": "00:00:30", "end_time": "00:00:40", "title": "clip2"}
        ]

        from services.media import run_batch_slice_job
        result = run_batch_slice_job("/video.mp4", clips, output_dir=self.temp_dir)

        self.assertEqual(len(result["output_paths"]), 2)
        self.assertIn("成功", result["summary_rows"][0][1])

    @patch("services.media.run_slice_job")
    @patch("services.media.get_current_workspace")
    @patch("services.media.get_workspace_dir")
    def test_run_batch_slice_job_skip_invalid_clips(self, mock_ws_dir, mock_ws, mock_slice):
        mock_ws.return_value = {"clips_dir": self.temp_dir}
        mock_ws_dir.return_value = Path(self.temp_dir)

        mock_slice.return_value = {
            "log": "success",
            "output_path": "/output/clip1.mp4",
            "summary_rows": [["状态", "成功"]]
        }

        clips = [
            {"start_time": "00:00:10", "end_time": "00:00:20", "title": "valid"},
            {"start_time": "", "end_time": "00:00:40", "title": "invalid"},
            {"start_time": "invalid", "end_time": "00:00:50", "title": "invalid2"}
        ]

        from services.media import run_batch_slice_job
        result = run_batch_slice_job("/video.mp4", clips, output_dir=self.temp_dir)

        self.assertEqual(mock_slice.call_count, 1)


if __name__ == "__main__":
    unittest.main()
