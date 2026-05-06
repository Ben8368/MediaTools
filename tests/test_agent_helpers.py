"""Tests for agent helper functions"""
import unittest


class TestAgentHelpers(unittest.TestCase):
    def test_json_dumps(self):
        from backend.agent.service import _json_dumps
        data = {"key": "值", "number": 123}
        result = _json_dumps(data)
        self.assertIn("key", result)
        self.assertIn("值", result)
        self.assertIn("123", result)

    def test_format_tool_trace_empty(self):
        from backend.agent.service import _format_tool_trace
        result = _format_tool_trace([])
        self.assertEqual(result, "未调用工具")

    def test_format_tool_trace_with_tools(self):
        from backend.agent.service import _format_tool_trace
        traces = [{"tool": "get_video_info"}, {"route": "slice_video"}]
        result = _format_tool_trace(traces)
        self.assertIn("get_video_info", result)
        self.assertIn("slice_video", result)

    def test_extract_urls(self):
        from backend.agent.service import _extract_urls
        text = "Check https://example.com and http://test.org"
        urls = _extract_urls(text)
        self.assertEqual(len(urls), 2)
        self.assertIn("https://example.com", urls)

    def test_extract_urls_empty(self):
        from backend.agent.service import _extract_urls
        self.assertEqual(_extract_urls(""), [])
        self.assertEqual(_extract_urls(None), [])

    def test_extract_local_paths(self):
        from backend.agent.service import _extract_local_paths
        text = "File at C:\\Users\\test\\file.mp4"
        paths = _extract_local_paths(text)
        self.assertEqual(len(paths), 1)
        self.assertIn("C:\\Users\\test\\file.mp4", paths)

    def test_looks_like_fetch_analyze_slice_task(self):
        from backend.agent.service import _looks_like_fetch_analyze_slice_task
        self.assertTrue(_looks_like_fetch_analyze_slice_task("下载视频并切片"))
        self.assertTrue(_looks_like_fetch_analyze_slice_task("自动切片"))
        self.assertTrue(_looks_like_fetch_analyze_slice_task("analyze and slice"))
        self.assertFalse(_looks_like_fetch_analyze_slice_task("just download"))

    def test_looks_like_asset_scan_task(self):
        from backend.agent.service import _looks_like_asset_scan_task
        self.assertTrue(_looks_like_asset_scan_task("扫描素材库"))
        self.assertTrue(_looks_like_asset_scan_task("扫描项目"))
        self.assertFalse(_looks_like_asset_scan_task("下载视频"))

    def test_looks_like_decrypt_task(self):
        from backend.agent.service import _looks_like_decrypt_task
        self.assertTrue(_looks_like_decrypt_task("解密音乐文件"))
        self.assertTrue(_looks_like_decrypt_task("convert file.ncm"))
        self.assertTrue(_looks_like_decrypt_task("process .qmc files"))
        self.assertFalse(_looks_like_decrypt_task("download video"))

    def test_parse_time_to_seconds(self):
        from backend.agent.service import _parse_time_to_seconds
        self.assertEqual(_parse_time_to_seconds("00:01:30"), 90)
        self.assertEqual(_parse_time_to_seconds("01:00:00"), 3600)
        self.assertEqual(_parse_time_to_seconds("00,00,45"), 45)
        self.assertEqual(_parse_time_to_seconds(""), 0)

    def test_summary_success_with_ok(self):
        from backend.agent.service import _summary_success
        self.assertTrue(_summary_success({"ok": True}))
        self.assertFalse(_summary_success({"ok": False}))

    def test_summary_success_with_rows(self):
        from backend.agent.service import _summary_success
        result = {"summary_rows": [["任务", "成功", "详情"]]}
        self.assertTrue(_summary_success(result))

    def test_make_action(self):
        from backend.agent.service import _make_action
        action = _make_action("download", "视频下载", "success", "已完成")
        self.assertEqual(action["kind"], "download")
        self.assertEqual(action["title"], "视频下载")
        self.assertEqual(action["status"], "success")
        self.assertIn("id", action)

    def test_make_artifact_with_path(self):
        from backend.agent.service import _make_artifact
        artifact = _make_artifact("/path/to/video.mp4", "video", "测试视频")
        self.assertEqual(artifact["kind"], "video")
        self.assertEqual(artifact["label"], "测试视频")
        self.assertIn("video.mp4", artifact["path"])

    def test_make_artifact_empty_path(self):
        from backend.agent.service import _make_artifact
        self.assertIsNone(_make_artifact("", "video"))
        self.assertIsNone(_make_artifact(None, "video"))

    def test_extend_unique(self):
        from backend.agent.service import _extend_unique
        target = [{"id": "1", "name": "a"}]
        incoming = [{"id": "2", "name": "b"}, {"id": "1", "name": "c"}]
        _extend_unique(target, incoming)
        self.assertEqual(len(target), 2)
        self.assertEqual(target[1]["id"], "2")

    def test_format_fetch_analyze_slice_answer_failure(self):
        from backend.agent.service import _format_fetch_analyze_slice_answer
        result = {"ok": False, "message": "下载失败"}
        answer = _format_fetch_analyze_slice_answer(result)
        self.assertIn("执行失败", answer)
        self.assertIn("下载失败", answer)

    def test_format_fetch_analyze_slice_answer_success(self):
        from backend.agent.service import _format_fetch_analyze_slice_answer
        result = {
            "ok": True,
            "video_info": {"title": "测试视频"},
            "video_path": "/path/video.mp4",
            "subtitle_path": "/path/sub.srt",
            "analysis_path": "/path/analysis.json",
            "selected_clips": [
                {
                    "start_time": "00:00:10",
                    "end_time": "00:00:20",
                    "actual_start_time": "00:00:10",
                    "actual_end_time": "00:00:20",
                    "title": "片段1",
                    "summary_zh": "测试片段"
                }
            ],
            "slice_result": {"output_paths": ["/clip1.mp4"], "output_dir": "/clips"}
        }
        answer = _format_fetch_analyze_slice_answer(result)
        self.assertIn("执行成功", answer)
        self.assertIn("测试视频", answer)
        self.assertIn("片段1", answer)
    def test_agent_without_api_key_returns_structured_failure_for_model_route(self):
        from unittest.mock import patch

        with patch("services.agent.get_api_config", return_value={"api_key": "", "api_base_url": "http://example.invalid", "analysis_model": "test-model"}):
            from backend.agent.service import MediaAgentService
            svc = MediaAgentService(api_key="", base_url="http://example.invalid", model="test-model")

        result = svc.execute("please plan a normal media task")

        self.assertFalse(result["ok"])
        self.assertIn("API key", result["answer"])
        self.assertEqual(result["actions"], [])


if __name__ == "__main__":
    unittest.main()
