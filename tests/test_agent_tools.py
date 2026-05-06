"""Tests for agent tool functions"""
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


class TestAgentToolFunctions(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("services.agent.fetch_video_info")
    @patch("services.agent.get_current_workspace")
    def test_tool_get_video_info(self, mock_ws, mock_fetch):
        mock_ws.return_value = {"downloads_dir": self.temp_dir}
        mock_fetch.return_value = {
            "title": "Test Video",
            "has_manual_subs": True,
            "has_auto_subs": False,
            "language": "en",
        }
        from backend.agent.service import _tool_get_video_info
        result = _tool_get_video_info("https://example.com/video")
        self.assertTrue(result["ok"])
        self.assertEqual(result["video"]["title"], "Test Video")

    def test_tool_inspect_subtitle_not_found(self):
        from backend.agent.service import _tool_inspect_subtitle
        result = _tool_inspect_subtitle("/nonexistent/sub.srt")
        self.assertFalse(result["ok"])
        self.assertIn("不存在", result["error"])

    def test_tool_inspect_subtitle_srt(self):
        srt_content = """1
00:00:01,000 --> 00:00:03,000
Hello world

2
00:00:04,000 --> 00:00:06,000
Second line
"""
        srt_path = Path(self.temp_dir) / "test.srt"
        srt_path.write_text(srt_content, encoding="utf-8")

        from backend.agent.service import _tool_inspect_subtitle
        result = _tool_inspect_subtitle(str(srt_path))
        self.assertTrue(result["ok"])
        self.assertEqual(result["segment_count"], 2)

    def test_tool_recommend_transcode(self):
        from backend.agent.service import _tool_recommend_transcode
        result = _tool_recommend_transcode("/path/video.mp4", "通用发布")
        self.assertTrue(result["ok"])
        self.assertIn("codec", result["recommendation"])

    def test_tool_recommend_transcode_archive(self):
        from backend.agent.service import _tool_recommend_transcode
        result = _tool_recommend_transcode("/path/video.mp4", "长期存档")
        self.assertTrue(result["ok"])
        self.assertIn("H.265", result["recommendation"]["codec"])

    def test_tool_recommend_transcode_audio_only(self):
        from backend.agent.service import _tool_recommend_transcode
        result = _tool_recommend_transcode("/path/video.mp4", "只要音频")
        self.assertTrue(result["ok"])
        self.assertIn("音频", result["recommendation"]["codec"])

    def test_tool_suggest_asset_names_kebab(self):
        from backend.agent.service import _tool_suggest_asset_names
        paths = ["/some/My Video File.mp4", "/other/Test_Clip.mp4"]
        result = _tool_suggest_asset_names(paths, "kebab-case")
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["suggestions"]), 2)
        self.assertIn("-", result["suggestions"][0]["suggested_name"])

    def test_tool_suggest_asset_names_snake(self):
        from backend.agent.service import _tool_suggest_asset_names
        paths = ["/some/My Video.mp4"]
        result = _tool_suggest_asset_names(paths, "snake_case")
        self.assertTrue(result["ok"])
        self.assertIn("_", result["suggestions"][0]["suggested_name"])

    @patch("services.agent.run_transcode_job")
    def test_tool_execute_transcode_success(self, mock_transcode):
        mock_transcode.return_value = {
            "output_path": "/output/video.mp4",
            "log": "done",
            "summary_rows": [],
        }
        from backend.agent.service import _tool_execute_transcode
        result = _tool_execute_transcode("/input/video.mp4", "H.264 (AVC)")
        self.assertTrue(result["ok"])
        self.assertEqual(result["output_path"], "/output/video.mp4")

    @patch("services.agent.run_slice_job")
    def test_tool_execute_slice_video(self, mock_slice):
        mock_slice.return_value = {
            "output_path": "/output/clip.mp4",
            "log": "done",
            "summary_rows": [],
        }
        from backend.agent.service import _tool_execute_slice_video
        result = _tool_execute_slice_video("/input/video.mp4", "00:00:10", "00:00:20")
        self.assertTrue(result["ok"])

    @patch("services.agent.AssetLibrary")
    def test_tool_scan_assets(self, mock_lib_class):
        mock_lib = Mock()
        mock_lib.scan.return_value = [{"name": "video.mp4", "type": "video"}]
        mock_lib.get_stats.return_value = {"total": 1}
        mock_lib_class.return_value = mock_lib

        from backend.agent.service import _tool_scan_assets
        result = _tool_scan_assets(self.temp_dir)
        self.assertTrue(result["ok"])
        self.assertEqual(result["total"], 1)


class TestSummarizeToolResult(unittest.TestCase):
    def test_get_video_info_success(self):
        from backend.agent.service import _summarize_tool_result
        result = {"ok": True, "video": {"title": "Test"}}
        actions, artifacts = _summarize_tool_result("get_video_info", {"url": "https://x.com"}, result)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["kind"], "inspect_video")

    def test_inspect_subtitle_success(self):
        from backend.agent.service import _summarize_tool_result
        result = {"ok": True, "subtitle_path": "/path/sub.srt", "segment_count": 50, "duration_seconds": 300}
        actions, artifacts = _summarize_tool_result("inspect_subtitle", {"subtitle_path": "/path/sub.srt"}, result)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["kind"], "inspect_subtitle")

    def test_analyze_subtitle_success(self):
        from backend.agent.service import _summarize_tool_result
        result = {"ok": True, "subtitle_path": "/path/sub.srt", "highlight_count": 5}
        actions, artifacts = _summarize_tool_result("analyze_subtitle", {"subtitle_path": "/path/sub.srt"}, result)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["kind"], "analyze_subtitle")

    def test_execute_transcode_success(self):
        from backend.agent.service import _summarize_tool_result
        result = {"ok": True, "output_path": "/output/video.mp4"}
        actions, artifacts = _summarize_tool_result("execute_transcode", {"input_path": "/in.mp4", "codec": "H.264 (AVC)"}, result)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["kind"], "transcode")

    def test_scan_assets_success(self):
        from backend.agent.service import _summarize_tool_result
        result = {"ok": True, "directory": "/dir", "total": 10}
        actions, artifacts = _summarize_tool_result("scan_assets", {"directory": "/dir"}, result)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["kind"], "scan_assets")


if __name__ == "__main__":
    unittest.main()
