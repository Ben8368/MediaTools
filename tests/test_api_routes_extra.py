import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modules.assets.file_manager import FileManager
from tests.api_test_helpers import make_client


class TestIntegrationRoutes(unittest.TestCase):
    @patch("services.api_server.get_current_workspace")
    @patch("services.api_server.get_wechat_moments_status")
    def test_wechat_status(self, mock_status, mock_ws):
        mock_ws.return_value = {"project_root": "/tmp"}
        mock_status.return_value = {"available": True}
        client = make_client()

        resp = client.get("/api/wechat_moments/status")

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["available"])

    @patch("services.api_server.get_current_workspace")
    @patch("services.api_server.save_wechat_moments_draft")
    def test_wechat_save_draft(self, mock_save, mock_ws):
        mock_ws.return_value = {"project_root": "/tmp"}
        mock_save.return_value = {"ok": True, "draft": {"text": "hello"}}
        client = make_client()

        resp = client.put("/api/wechat_moments/draft", json={"draft": {"text": "hello"}})

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])

    @patch("services.api_server.get_current_workspace")
    @patch("services.api_server.export_wechat_moments_image")
    def test_wechat_export(self, mock_export, mock_ws):
        mock_ws.return_value = {"project_root": "/tmp"}
        mock_export.return_value = {"ok": True, "output_path": "/tmp/out.png"}
        client = make_client()

        resp = client.post("/api/wechat_moments/export", json={"image_data_url": "data:image/png;base64,AA==", "draft": {}})

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])

    @patch("services.api_server.get_current_workspace")
    @patch("services.api_server.get_auditor_config")
    def test_auditor_config(self, mock_config, mock_ws):
        mock_ws.return_value = {"project_root": "/tmp"}
        mock_config.return_value = {"ok": True, "config": {"enabled": True}}
        client = make_client()

        resp = client.get("/api/auditor/config")

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])

    @patch("services.api_server.get_current_workspace")
    @patch("services.api_server.save_auditor_config")
    def test_auditor_save_config(self, mock_save, mock_ws):
        mock_ws.return_value = {"project_root": "/tmp"}
        mock_save.return_value = {"ok": True, "config": {"enabled": False}}
        client = make_client()

        resp = client.put("/api/auditor/config", json={"config": {"enabled": False}})

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])

    @patch("services.api_server.run_auditor_scan_once")
    @patch("services.api_server.get_current_workspace")
    def test_auditor_run_once(self, mock_ws, mock_run):
        mock_ws.return_value = {"project_root": "/tmp"}
        mock_run.return_value = {"ok": True, "summary": "done"}
        client = make_client()

        resp = client.post("/api/auditor/run-once")

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])


class TestMediaCommandRoutes(unittest.TestCase):
    @staticmethod
    def _run_immediately(target):
        target()

    @patch("services.api_server.get_current_workspace")
    @patch("services.api_server.run_fetch_batch_stream")
    @patch("services.api_media_routes._start_background", _run_immediately.__func__)
    def test_fetcher_download(self, mock_stream, mock_ws):
        mock_ws.return_value = {"downloads_dir": "/tmp/downloads"}
        mock_stream.return_value = iter([
            {
                "summary_text": "done",
                "progress_percent": 100,
                "progress_text": "done",
                "items": [{"info": {"local_path": "/tmp/downloads/video.mp4", "title": "Video"}}],
            }
        ])
        client = make_client()

        resp = client.post("/api/fetcher/download", json={"url": "https://example.com/video", "quality": "h264"})

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])
        self.assertEqual(resp.json()["status"], "pending")
        self.assertIn("task_id", resp.json())

    @patch("services.api_server.get_current_workspace")
    @patch("services.api_server.resolve_allowed_path")
    @patch("services.api_server.run_fetch_batch_stream")
    @patch("services.api_media_routes._start_background", _run_immediately.__func__)
    def test_fetcher_download_uses_selected_output_dir(self, mock_stream, mock_resolve, mock_ws):
        temp_dir = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
        target_dir = temp_dir / "picked"
        mock_ws.return_value = {"downloads_dir": str(temp_dir / "downloads"), "project_root": str(temp_dir)}
        mock_resolve.return_value = target_dir
        mock_stream.return_value = iter([
            {
                "summary_text": "done",
                "progress_percent": 100,
                "progress_text": "done",
                "items": [{"info": {"local_path": str(target_dir / "video.mp4"), "title": "Video"}}],
            }
        ])
        client = make_client()

        resp = client.post(
            "/api/fetcher/download",
            json={"url": "https://example.com/video", "output_dir": str(target_dir)},
        )

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])
        mock_resolve.assert_called_once()
        self.assertEqual(mock_stream.call_args.kwargs["output_dir"], str(target_dir))

    @patch("services.api_server.get_current_workspace")
    @patch("services.api_server.resolve_allowed_path")
    def test_fetcher_download_rejects_outside_output_dir(self, mock_resolve, mock_ws):
        mock_ws.return_value = {"downloads_dir": "/tmp/downloads", "project_root": "/tmp"}
        mock_resolve.side_effect = ValueError("Path is outside allowed roots")
        client = make_client()

        resp = client.post(
            "/api/fetcher/download",
            json={"url": "https://example.com/video", "output_dir": "/etc"},
        )

        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()["ok"])

    @patch("services.api_server.run_transcode_job")
    def test_encoder_transcode(self, mock_run):
        mock_run.return_value = {"summary_rows": [["状态", "成功"]], "output_path": "/tmp/out.mp4"}
        client = make_client()

        resp = client.post("/api/encoder/transcode", json={"input_path": "/tmp/in.mp4"})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["output_path"], "/tmp/out.mp4")

    @patch("services.api_server.run_decrypt_job")
    def test_decryptor_decrypt(self, mock_run):
        mock_run.return_value = {"summary_rows": [["状态", "成功"]], "result_text": "ok"}
        client = make_client()

        resp = client.post("/api/decryptor/decrypt", json={"input_path": "/tmp/song.ncm"})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["result_text"], "ok")


class TestFileRoutes(unittest.TestCase):
    @patch("services.api_server.file_manager")
    def test_files_list(self, mock_fm):
        mock_fm.list_directory.return_value = {"files": [], "directories": []}
        client = make_client()
        resp = client.get("/api/files/list?directory=.")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("files", data)

    @patch("services.api_server.file_manager")
    def test_files_info(self, mock_fm):
        mock_fm.get_file_info.return_value = {
            "name": "test.txt",
            "is_file": True,
            "size": 100
        }
        client = make_client()
        resp = client.get("/api/files/info?path=test.txt")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["name"], "test.txt")

    @patch("services.api_server.file_manager")
    def test_files_mkdir(self, mock_fm):
        mock_fm.create_directory.return_value = {"path": "newdir"}
        client = make_client()
        resp = client.post("/api/files/mkdir", json={"path": "newdir"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])

    @patch("services.api_server.file_manager")
    def test_files_delete(self, mock_fm):
        mock_fm.delete.return_value = {"path": "delete_me.txt"}
        client = make_client()
        resp = client.request("DELETE", "/api/files/delete", json={"path": "delete_me.txt", "recursive": False})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])

    @patch("services.api_server.PREVIEW_MAX_BYTES", 3)
    def test_files_preview_rejects_large_file(self):
        temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(temp_dir, ignore_errors=True))
        large_file = Path(temp_dir) / "large.jpg"
        large_file.write_bytes(b"1234")

        with patch("services.api_server.file_manager", FileManager(temp_dir)):
            client = make_client()
            resp = client.get("/api/files/preview?path=large.jpg")

        self.assertEqual(resp.status_code, 413)


class TestAssetsRoutes(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("services.api_server.get_current_workspace")
    def test_assets_list(self, mock_ws):
        root = Path(self.temp_dir)
        (root / "video.mp4").write_bytes(b"\x00" * 100)
        mock_ws.return_value = {
            "project_root": str(root),
            "downloads_dir": str(root / "downloads"),
            "assets_dir": str(root / "assets"),
            "exports_dir": str(root / "exports"),
        }
        client = make_client()
        with patch("services.api_server.ASSET_SCAN_MAX_FILES", 1):
            resp = client.get("/api/assets/list")
            self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("items", data)
        self.assertEqual(data["scan_limit"], 1)
        self.assertFalse(data["truncated"])

    @patch("services.api_server.get_current_workspace")
    def test_assets_list_rejects_outside_path(self, mock_ws):
        root = Path(self.temp_dir)
        mock_ws.return_value = {
            "project_root": str(root),
            "downloads_dir": str(root / "downloads"),
            "assets_dir": str(root / "assets"),
            "exports_dir": str(root / "exports"),
        }
        with patch("services.path_picker.WORKSPACE_ALLOWED_ROOTS", [root]):
            client = make_client()
            resp = client.get("/api/assets/list", params={"directory": str(root.parent)})

        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()["ok"])


class TestPhotoshopRoutes(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        root = Path(self.temp_dir)
        self.workspace = {
            "project_root": str(root),
            "manifests_dir": str(root / "manifests"),
            "exports_dir": str(root / "exports"),
        }
        tickets_dir = root / "manifests" / "photoshop" / "tickets"
        tickets_dir.mkdir(parents=True)
        (tickets_dir / "ticket-1.json").write_text(
            json.dumps(
                {
                    "meta": {"source_psd": "sample.psd", "created_at": "2026-04-24T10:00:00"},
                    "tasks": [{"status": "confirmed"}, {"status": "pending"}],
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("services.api_server.get_current_workspace")
    def test_photoshop_tickets_do_not_require_runtime_imports(self, mock_ws):
        mock_ws.return_value = self.workspace
        client = make_client()

        resp = client.get("/api/photoshop/tickets")

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["items"][0]["ticket_id"], "ticket-1")
        self.assertEqual(data["items"][0]["confirmed_count"], 1)

    @patch("services.api_server.get_current_workspace")
    def test_photoshop_ticket_detail_reads_plain_json(self, mock_ws):
        mock_ws.return_value = self.workspace
        client = make_client()

        resp = client.get("/api/photoshop/tickets/ticket-1")

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["ticket"]["meta"]["source_psd"], "sample.psd")

    @patch("services.api_server.start_ticket_execution")
    @patch("services.api_server.get_current_workspace")
    def test_photoshop_execute_passes_selected_task_indexes(self, mock_ws, mock_start):
        mock_ws.return_value = self.workspace
        mock_start.return_value = {"ok": True, "ticket_id": "ticket-1"}
        client = make_client()

        resp = client.post(
            "/api/photoshop/tickets/ticket-1/execute",
            json={"dry_run": True, "selected_task_indexes": [0, 2]},
        )

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["ok"])
        self.assertEqual(mock_start.call_args.kwargs["selected_task_indexes"], [0, 2])
        self.assertTrue(mock_start.call_args.kwargs["dry_run"])
