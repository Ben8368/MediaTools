"""Tests for API server routes using FastAPI TestClient"""
import logging
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services.task_center import TaskCenter, TaskStatus, TaskType
from tests.api_test_helpers import make_client


def _make_client():
    return make_client()


class TestSystemRoutes(unittest.TestCase):
    @patch("services.api_server.API_SECRET_KEY", "secret")
    def test_api_requires_key_when_configured(self):
        client = _make_client()
        resp = client.get("/api/system/status")
        self.assertEqual(resp.status_code, 401)

    @patch("services.api_server.API_SECRET_KEY", "secret")
    def test_api_rejects_invalid_key_when_configured(self):
        client = _make_client()
        resp = client.get("/api/system/status", headers={"X-API-Key": "wrong"})
        self.assertEqual(resp.status_code, 403)

    @patch("services.api_system_routes.YtdlpAdapter")
    @patch("services.api_system_routes.FFmpegAdapter")
    @patch("services.api_system_routes.UmcliAdapter")
    @patch("services.api_system_routes.get_patch_diagnostics")
    def test_system_status(self, mock_patches, mock_umcli, mock_ffmpeg, mock_ytdlp):
        mock_ytdlp.return_value.get_status.return_value = {"installed": True, "version": "2024.1"}
        mock_ffmpeg.return_value.get_info.return_value = {"installed": True, "version": "6.0"}
        mock_umcli.return_value.is_available.return_value = True
        mock_patches.return_value = {}

        client = _make_client()
        resp = client.get("/api/system/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("ffmpeg", data)
        self.assertIn("ytdlp", data)

    @patch("services.api_system_routes.get_runtime_metrics")
    def test_system_metrics(self, mock_metrics):
        mock_metrics.return_value = {
            "ok": True,
            "system": {"cpu_percent": 12.5},
            "network": {"download": {"text": "1.0 MB/s"}},
            "services": [],
            "tasks": [],
        }

        client = _make_client()
        resp = client.get("/api/system/metrics")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["system"]["cpu_percent"], 12.5)
        self.assertIn("network", data)

    @patch("services.api_server.threading.Thread")
    def test_system_shutdown_schedules_background_termination(self, mock_thread):
        client = _make_client()

        resp = client.post("/api/system/shutdown")

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])
        mock_thread.assert_called_once()
        self.assertTrue(mock_thread.call_args.kwargs["daemon"])
        mock_thread.return_value.start.assert_called_once()

    @patch("services.api_server.threading.Thread")
    def test_system_restart_schedules_background_restart(self, mock_thread):
        client = _make_client()

        resp = client.post("/api/system/restart")

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])
        mock_thread.assert_called_once()
        self.assertTrue(mock_thread.call_args.kwargs["daemon"])
        mock_thread.return_value.start.assert_called_once()

    @patch("services.api_server.get_current_workspace")
    def test_get_workspace(self, mock_ws):
        mock_ws.return_value = {"project_root": "/tmp/test"}
        client = _make_client()
        resp = client.get("/api/workspace")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("project_root", data)

    @patch("services.api_server.set_current_workspace")
    def test_set_workspace(self, mock_set):
        mock_set.return_value = {"project_root": "/tmp/new"}
        client = _make_client()
        resp = client.post("/api/workspace", json={"project_root": "/tmp/new"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertTrue(mock_set.call_args.kwargs["enforce_allowed_root"])

    @patch("services.api_server.set_current_workspace")
    def test_set_workspace_error(self, mock_set):
        mock_set.side_effect = ValueError("invalid path")
        client = _make_client()
        resp = client.post("/api/workspace", json={"project_root": "/invalid"})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()["ok"])


class TestLogRoutes(unittest.TestCase):
    def test_logs_capture_backend_records_and_filter(self):
        from services.log_buffer import get_log_buffer

        get_log_buffer().clear()
        client = _make_client()
        logging.getLogger("tests.logviewer").warning(
            "unit warning",
            extra={"user": "tester", "event": "测试告警"},
        )

        resp = client.get("/api/logs", params={"level": "WARNING", "module": "tests.logviewer"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertGreaterEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["level"], "WARNING")
        self.assertEqual(data["items"][0]["user"], "tester")
        self.assertEqual(data["items"][0]["event"], "测试告警")

    def test_log_metadata_and_clear(self):
        from services.log_buffer import get_log_buffer

        get_log_buffer().clear()
        client = _make_client()
        logging.getLogger("tests.metadata").info("metadata probe")

        meta = client.get("/api/logs/modules")
        self.assertEqual(meta.status_code, 200)
        self.assertIn("tests.metadata", meta.json()["modules"])

        clear = client.post("/api/logs/clear")
        self.assertEqual(clear.status_code, 200)
        self.assertTrue(clear.json()["ok"])


class TestPathPickerRoutes(unittest.TestCase):
    def _workspace(self, root):
        return {
            "project_root": str(root),
            "downloads_dir": str(root / "downloads"),
            "assets_dir": str(root / "assets"),
            "exports_dir": str(root / "exports"),
            "cache_dir": str(root / "cache"),
        }

    @patch("services.api_server.get_current_workspace")
    def test_path_picker_roots(self, mock_ws):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            mock_ws.return_value = self._workspace(root)
            client = _make_client()

            resp = client.get("/api/path-picker/roots")

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertIn("workspace", {item["id"] for item in data["roots"]})

    @patch("services.api_server.get_current_workspace")
    def test_path_picker_list_rejects_traversal(self, mock_ws):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            (Path(tmp) / "outside").mkdir()
            mock_ws.return_value = self._workspace(root)
            client = _make_client()

            resp = client.get("/api/path-picker/list", params={"root_id": "workspace", "path": "../outside"})

        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()["ok"])


class TestWorkbenchRoutes(unittest.TestCase):
    @patch("services.api_server.list_workspace_media")
    def test_workbench_media(self, mock_list):
        mock_list.return_value = {
            "workspace": {"project_root": "/tmp"},
            "video_rows": [],
            "subtitle_rows": [],
            "export_rows": []
        }
        client = _make_client()
        resp = client.get("/api/workbench/media")
        self.assertEqual(resp.status_code, 200)

    @patch("services.api_server.analyze_subtitle_for_workbench")
    def test_workbench_analyze(self, mock_analyze):
        mock_analyze.return_value = {
            "ok": True,
            "clips": [],
            "clips_json": "[]",
            "subtitle_path": "/sub.srt",
            "analysis_path": "/analysis.json"
        }
        client = _make_client()
        resp = client.post("/api/workbench/analyze", json={
            "subtitle_path": "/sub.srt",
            "clip_count": 5
        })
        self.assertEqual(resp.status_code, 200)

    @patch("services.api_server.export_clips_from_workbench")
    def test_workbench_export(self, mock_export):
        mock_export.return_value = {
            "ok": True,
            "message": "done",
            "summary_rows": [],
            "export_rows": [],
            "clips": []
        }
        client = _make_client()
        resp = client.post("/api/workbench/export", json={
            "video_path": "/video.mp4",
            "subtitle_path": "/sub.srt",
            "clips_json": "[]",
            "burn_subtitles": True
        })
        self.assertEqual(resp.status_code, 200)


class TestAgentRoutes(unittest.TestCase):
    @patch("services.agent.MediaAgentService.execute")
    def test_agent_chat_returns_structured_error_on_exception(self, mock_execute):
        mock_execute.side_effect = RuntimeError("boom")
        client = _make_client()

        resp = client.post("/api/agent/chat", json={"task": "hello"})

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["ok"])
        self.assertIn("boom", data["answer"])
        self.assertEqual(data["actions"], [])


class TestTaskRoutes(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.task_center = TaskCenter(str(Path(self.temp_dir) / "tasks.db"))
        self.task_center.create_task("task-1", TaskType.DOWNLOAD, "download")
        self.patch_task_center = patch("services.api_task_center.get_task_center", return_value=self.task_center)
        self.patch_task_center.start()

    def tearDown(self):
        self.patch_task_center.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_pause_resume_are_absent_from_api_surface(self):
        client = _make_client()
        paths = client.get("/openapi.json").json()["paths"]
        pause_resp = client.post("/api/tasks/task-1/pause")
        resume_resp = client.post("/api/tasks/task-1/resume")

        self.assertNotIn("/api/tasks/{task_id}/pause", paths)
        self.assertNotIn("/api/tasks/{task_id}/resume", paths)
        self.assertEqual(pause_resp.status_code, 405)
        self.assertEqual(resume_resp.status_code, 405)

    def test_delete_terminal_task_record(self):
        self.task_center.update_task("task-1", status=TaskStatus.COMPLETED)
        client = _make_client()

        resp = client.request("DELETE", "/api/tasks/task-1")

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])
        self.assertIsNone(self.task_center.get_task("task-1"))

    def test_clear_cancelled_download_records(self):
        self.task_center.update_task("task-1", status=TaskStatus.CANCELLED)
        self.task_center.create_task("task-2", TaskType.DOWNLOAD, "download-2")
        self.task_center.update_task("task-2", status=TaskStatus.CANCELLED)
        client = _make_client()

        resp = client.post("/api/tasks/clear", json={"ids": ["task-1", "task-2"], "terminal_only": True})

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])
        self.assertEqual(self.task_center.list_tasks(), [])


if __name__ == "__main__":
    unittest.main()
