"""Tests for additional agent tool functions"""
import shutil
import tempfile
import unittest
from unittest.mock import Mock, patch


class TestAgentAdditionalTools(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("services.agent.AssetLibrary")
    def test_tool_scan_assets_with_keyword(self, mock_lib_class):
        mock_lib = Mock()
        mock_lib.scan.return_value = [{"name": "video.mp4"}]
        mock_lib.search.return_value = [{"name": "test_video.mp4"}]
        mock_lib.get_stats.return_value = {"total": 1}
        mock_lib_class.return_value = mock_lib

        from backend.agent.service import _tool_scan_assets
        result = _tool_scan_assets(self.temp_dir, keyword="test")
        self.assertTrue(result["ok"])
        mock_lib.search.assert_called_once_with("test")

    @patch("services.agent.AssetLibrary")
    def test_tool_scan_assets_with_type(self, mock_lib_class):
        mock_lib = Mock()
        mock_lib.scan.return_value = [{"name": "video.mp4"}]
        mock_lib.list_assets.return_value = [{"name": "video.mp4", "type": "video"}]
        mock_lib.get_stats.return_value = {"total": 1}
        mock_lib_class.return_value = mock_lib

        from backend.agent.service import _tool_scan_assets
        result = _tool_scan_assets(self.temp_dir, asset_type="video")
        self.assertTrue(result["ok"])
        mock_lib.list_assets.assert_called_once_with("video")

    @patch("services.agent.ScreenshotGenerator")
    def test_tool_extract_screenshot_success(self, mock_gen_class):
        mock_gen = Mock()
        mock_gen.extract_frame.return_value = {
            "success": True,
            "output_path": "/output/frame.jpg"
        }
        mock_gen_class.return_value = mock_gen

        from backend.agent.service import _tool_extract_screenshot
        result = _tool_extract_screenshot("/video.mp4", "00:01:30", "/output/frame.jpg")
        self.assertTrue(result["ok"])
        self.assertEqual(result["output_path"], "/output/frame.jpg")

    @patch("services.agent.ScreenshotGenerator")
    def test_tool_extract_screenshot_auto_path(self, mock_gen_class):
        mock_gen = Mock()
        mock_gen.extract_frame.return_value = {
            "success": True,
            "output_path": "/video_00-01-30.jpg"
        }
        mock_gen_class.return_value = mock_gen

        from backend.agent.service import _tool_extract_screenshot
        result = _tool_extract_screenshot("/video.mp4", "00:01:30")
        self.assertTrue(result["ok"])

    @patch("services.agent.export_wechat_moments_image")
    @patch("services.agent.save_wechat_moments_draft")
    @patch("services.agent.get_wechat_moments_draft")
    @patch("services.agent.get_current_workspace")
    def test_tool_export_wechat_moments(self, mock_ws, mock_draft, mock_save, mock_export):
        mock_ws.return_value = {"exports_dir": self.temp_dir}
        mock_draft.return_value = {"draft": {}}
        mock_export.return_value = {"ok": True, "image_path": "/output/moments.jpg"}

        from backend.agent.service import _tool_export_wechat_moments
        result = _tool_export_wechat_moments("测试文本", "A", "dark")
        self.assertTrue(result["ok"])

    @patch("services.agent.list_photoshop_tickets")
    @patch("services.agent.get_current_workspace")
    def test_tool_list_psd_tickets(self, mock_ws, mock_list):
        mock_ws.return_value = {"project_root": self.temp_dir}
        mock_list.return_value = [{"id": "1", "name": "ticket1"}]

        from backend.agent.service import _tool_list_psd_tickets
        result = _tool_list_psd_tickets()
        self.assertTrue(result["ok"])
        self.assertEqual(result["count"], 1)

    @patch("services.agent.scan_photoshop_document")
    @patch("services.agent.get_current_workspace")
    def test_tool_scan_psd(self, mock_ws, mock_scan):
        mock_ws.return_value = {"project_root": self.temp_dir}
        mock_scan.return_value = {"ok": True, "layers": []}

        from backend.agent.service import _tool_scan_psd
        result = _tool_scan_psd("/path/file.psd", ["en", "zh"])
        self.assertIn("ok", result)

    @patch("services.agent.get_auditor_config")
    @patch("services.agent.get_current_workspace")
    def test_tool_get_auditor_status(self, mock_ws, mock_config):
        mock_ws.return_value = {"project_root": self.temp_dir}
        mock_config.return_value = {"config": {"enabled": True}}

        from backend.agent.service import _tool_get_auditor_status
        result = _tool_get_auditor_status()
        self.assertTrue(result["ok"])

    @patch("services.agent.run_auditor_scan_once")
    @patch("services.agent.get_current_workspace")
    def test_tool_run_audit_scan(self, mock_ws, mock_scan):
        mock_ws.return_value = {"project_root": self.temp_dir}
        mock_scan.return_value = {
            "ok": True,
            "scanned_count": 10,
            "flagged_count": 2,
            "summary": "Scan complete"
        }

        from backend.agent.service import _tool_run_audit_scan
        result = _tool_run_audit_scan()
        self.assertTrue(result["ok"])
        self.assertEqual(result["scanned_count"], 10)


class TestSummarizeToolResultExtended(unittest.TestCase):
    def test_execute_slice_video_result(self):
        from backend.agent.service import _summarize_tool_result
        result = {"ok": True, "output_path": "/clip.mp4", "log": "success"}
        actions, artifacts = _summarize_tool_result(
            "execute_slice_video",
            {"input_path": "/video.mp4", "start_time": "00:00:10", "end_time": "00:00:20"},
            result
        )
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["kind"], "slice")
        self.assertEqual(len(artifacts), 1)

    def test_execute_fetch_analyze_slice_result(self):
        from backend.agent.service import _summarize_tool_result
        result = {
            "ok": True,
            "video_path": "/video.mp4",
            "subtitle_path": "/sub.srt",
            "analysis_path": "/analysis.json",
            "slice_result": {
                "output_paths": ["/clip1.mp4", "/clip2.mp4"],
                "output_dir": "/clips"
            }
        }
        actions, artifacts = _summarize_tool_result(
            "execute_fetch_analyze_slice",
            {"url": "https://example.com"},
            result
        )
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["kind"], "pipeline")
        self.assertGreater(len(artifacts), 3)

    def test_suggest_asset_names_result(self):
        from backend.agent.service import _summarize_tool_result
        result = {
            "ok": True,
            "style": "kebab-case",
            "suggestions": [{"path": "/file.mp4", "suggested_name": "new-name.mp4"}]
        }
        actions, artifacts = _summarize_tool_result(
            "suggest_asset_names",
            {"paths": ["/file.mp4"], "style": "kebab-case"},
            result
        )
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["kind"], "rename_suggestion")


if __name__ == "__main__":
    unittest.main()
