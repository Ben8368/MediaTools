"""Tests for workbench service"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


class TestWorkbenchService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("services.workbench.get_current_workspace")
    def test_list_workspace_media(self, mock_ws):
        mock_ws.return_value = {
            "project_root": self.temp_dir,
            "exports_dir": str(Path(self.temp_dir) / "exports"),
            "clips_dir": str(Path(self.temp_dir) / "clips"),
        }
        (Path(self.temp_dir) / "video.mp4").write_bytes(b"\x00" * 100)
        (Path(self.temp_dir) / "sub.srt").write_text("1\n00:00:01,000 --> 00:00:03,000\nHello\n", encoding="utf-8")

        from services.workbench import list_workspace_media
        result = list_workspace_media()

        self.assertIn("workspace", result)
        self.assertIn("video_rows", result)
        self.assertIn("subtitle_rows", result)
        self.assertIn("export_rows", result)
        self.assertEqual(len(result["video_rows"]), 1)
        self.assertEqual(len(result["subtitle_rows"]), 1)

    def test_analyze_subtitle_not_found(self):
        from services.workbench import analyze_subtitle_for_workbench
        result = analyze_subtitle_for_workbench("/nonexistent/sub.srt")
        self.assertFalse(result["ok"])
        self.assertIn("不存在", result["message"])

    @patch("services.workbench.get_current_workspace")
    @patch("services.workbench.workspace_path")
    @patch("services.workbench.SubtitleAnalyzer")
    @patch("services.workbench.get_api_config")
    def test_analyze_subtitle_srt(self, mock_config, mock_analyzer_class, mock_ws_path, mock_ws):
        mock_config.return_value = {
            "api_key": "test",
            "api_base_url": "http://test",
            "analysis_model": "test-model",
        }
        mock_ws.return_value = {"project_root": self.temp_dir}

        analysis_file = Path(self.temp_dir) / "analysis.json"
        mock_ws_path.return_value = analysis_file

        mock_analyzer = Mock()
        mock_analyzer.analyze_from_srt.return_value = (
            [
                {
                    "start_time": "00:00:10",
                    "end_time": "00:00:20",
                    "category": "highlight",
                    "summary_zh": "精彩片段",
                    "quote": "test quote",
                }
            ],
            "llm text",
        )
        mock_analyzer_class.return_value = mock_analyzer

        srt_content = "1\n00:00:01,000 --> 00:00:03,000\nHello\n"
        srt_path = Path(self.temp_dir) / "test.srt"
        srt_path.write_text(srt_content, encoding="utf-8")

        from services.workbench import analyze_subtitle_for_workbench
        result = analyze_subtitle_for_workbench(str(srt_path), clip_count=1)

        self.assertTrue(result["ok"])
        self.assertEqual(len(result["clips"]), 1)
        self.assertEqual(result["clips"][0]["title"], "highlight")

    def test_export_clips_no_video(self):
        from services.workbench import export_clips_from_workbench
        result = export_clips_from_workbench("", "", "[]")
        self.assertFalse(result["ok"])
        self.assertIn("视频路径", result["message"])

    def test_export_clips_no_clips(self):
        from services.workbench import export_clips_from_workbench
        result = export_clips_from_workbench("/path/video.mp4", "", "")
        self.assertFalse(result["ok"])

    def test_export_clips_invalid_json(self):
        from services.workbench import export_clips_from_workbench
        result = export_clips_from_workbench("/path/video.mp4", "", "not json")
        self.assertFalse(result["ok"])
        self.assertIn("JSON", result["message"])

    @patch("services.workbench.get_current_workspace")
    @patch("services.workbench.get_workspace_dir")
    @patch("services.workbench.run_batch_slice_job")
    def test_export_clips_success(self, mock_slice, mock_ws_dir, mock_ws):
        mock_ws.return_value = {"project_root": self.temp_dir}
        mock_ws_dir.return_value = Path(self.temp_dir) / "clips"
        mock_slice.return_value = {
            "output_paths": [],
            "log": "done",
            "summary_rows": [],
            "clips": [],
        }

        clips = json.dumps([{"start_time": "00:00:10", "end_time": "00:00:20", "title": "clip1"}])
        from services.workbench import export_clips_from_workbench
        result = export_clips_from_workbench("/path/video.mp4", "", clips)
        self.assertIn("ok", result)


if __name__ == "__main__":
    unittest.main()
