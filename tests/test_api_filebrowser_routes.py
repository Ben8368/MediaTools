import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.api.server import app


class TestApiFilebrowserRoutes(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("services.api_filebrowser_routes.list_filebrowser_disks")
    def test_disks_route_returns_available_disks(self, mock_list_disks):
        mock_list_disks.return_value = [{"name": "C:", "path": "C:\\"}]

        response = self.client.get("/api/filebrowser/disks")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(response.json()["disks"], [{"name": "C:", "path": "C:\\"}])

    @patch("services.api_filebrowser_routes.get_filebrowser_status")
    def test_status_route_wraps_success(self, mock_status):
        mock_status.return_value = {"running": True, "pid": 123}

        response = self.client.get("/api/filebrowser/status")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(response.json()["pid"], 123)

    @patch("services.api_filebrowser_routes.start_filebrowser_service")
    @patch("services.api_filebrowser_routes.stop_filebrowser_service")
    @patch("services.api_filebrowser_routes.restart_filebrowser_service")
    def test_service_control_routes_delegate(self, mock_restart, mock_stop, mock_start):
        mock_start.return_value = {"ok": True, "action": "start"}
        mock_stop.return_value = {"ok": True, "action": "stop"}
        mock_restart.return_value = {"ok": True, "action": "restart"}

        start_resp = self.client.post("/api/filebrowser/start")
        stop_resp = self.client.post("/api/filebrowser/stop")
        restart_resp = self.client.post("/api/filebrowser/restart")

        self.assertEqual(start_resp.json()["action"], "start")
        self.assertEqual(stop_resp.json()["action"], "stop")
        self.assertEqual(restart_resp.json()["action"], "restart")

    @patch("services.api_filebrowser_routes.read_filebrowser_log")
    def test_log_route_returns_tail_text(self, mock_log):
        mock_log.return_value = "line-1\nline-2"

        response = self.client.get("/api/filebrowser/log", params={"lines": 10})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["log"], "line-1\nline-2")

    @patch("services.api_filebrowser_routes.fb_list")
    @patch("services.api_filebrowser_routes.fb_info")
    def test_list_and_info_routes_delegate(self, mock_info, mock_list):
        mock_list.return_value = {"path": "C:\\", "directories": [], "files": []}
        mock_info.return_value = {"path": "C:\\clip.mp4", "name": "clip.mp4"}

        list_resp = self.client.get("/api/filebrowser/list", params={"directory": "C:\\"})
        info_resp = self.client.get("/api/filebrowser/info", params={"path": "C:\\clip.mp4"})

        self.assertEqual(list_resp.status_code, 200)
        self.assertTrue(list_resp.json()["ok"])
        self.assertEqual(info_resp.status_code, 200)
        self.assertEqual(info_resp.json()["name"], "clip.mp4")

    @patch("services.api_filebrowser_routes.fb_mkdir")
    @patch("services.api_filebrowser_routes.fb_rename")
    @patch("services.api_filebrowser_routes.fb_move")
    @patch("services.api_filebrowser_routes.fb_copy")
    @patch("services.api_filebrowser_routes.fb_delete")
    def test_mutation_routes_delegate(self, mock_delete, mock_copy, mock_move, mock_rename, mock_mkdir):
        mock_mkdir.return_value = {"path": "C:\\new-folder"}
        mock_rename.return_value = {"path": "C:\\renamed.txt"}
        mock_move.return_value = {"destination": "D:\\moved.txt"}
        mock_copy.return_value = {"destination": "D:\\copied.txt"}
        mock_delete.return_value = {"deleted": "C:\\old.txt"}

        mkdir_resp = self.client.post("/api/filebrowser/mkdir", json={"path": "C:\\new-folder"})
        rename_resp = self.client.post("/api/filebrowser/rename", json={"old_path": "C:\\old.txt", "new_name": "renamed.txt"})
        move_resp = self.client.post("/api/filebrowser/move", json={"source_path": "C:\\a.txt", "dest_path": "D:\\moved.txt"})
        copy_resp = self.client.post("/api/filebrowser/copy", json={"source_path": "C:\\a.txt", "dest_path": "D:\\copied.txt"})
        delete_resp = self.client.request("DELETE", "/api/filebrowser/delete", json={"path": "C:\\old.txt", "recursive": False})

        self.assertEqual(mkdir_resp.status_code, 200)
        self.assertTrue(rename_resp.json()["ok"])
        self.assertEqual(move_resp.json()["destination"], "D:\\moved.txt")
        self.assertEqual(copy_resp.json()["destination"], "D:\\copied.txt")
        self.assertEqual(delete_resp.json()["deleted"], "C:\\old.txt")

    @patch("services.api_filebrowser_routes.fb_delete")
    def test_route_errors_return_400_payloads(self, mock_delete):
        mock_delete.side_effect = ValueError("unsafe path")

        response = self.client.request("DELETE", "/api/filebrowser/delete", json={"path": "C:\\bad.txt", "recursive": False})

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])
        self.assertIn("unsafe path", response.json()["error"])

    def test_all_route_errors_return_400_payloads(self):
        cases = [
            ("get_filebrowser_status", "GET", "/api/filebrowser/status", None),
            ("start_filebrowser_service", "POST", "/api/filebrowser/start", None),
            ("stop_filebrowser_service", "POST", "/api/filebrowser/stop", None),
            ("restart_filebrowser_service", "POST", "/api/filebrowser/restart", None),
            ("read_filebrowser_log", "GET", "/api/filebrowser/log?lines=5", None),
            ("fb_list", "GET", "/api/filebrowser/list?directory=C%3A%5C", None),
            ("fb_info", "GET", "/api/filebrowser/info?path=C%3A%5Cclip.mp4", None),
            ("fb_mkdir", "POST", "/api/filebrowser/mkdir", {"path": "C:\\new-folder"}),
            ("fb_rename", "POST", "/api/filebrowser/rename", {"old_path": "C:\\old.txt", "new_name": "new.txt"}),
            ("fb_move", "POST", "/api/filebrowser/move", {"source_path": "C:\\a.txt", "dest_path": "D:\\a.txt"}),
            ("fb_copy", "POST", "/api/filebrowser/copy", {"source_path": "C:\\a.txt", "dest_path": "D:\\a.txt"}),
            ("fb_list_trash", "GET", "/api/filebrowser/trash", None),
            ("fb_restore_trash", "POST", "/api/filebrowser/trash/restore", {"id": "trash-1"}),
            ("fb_purge_trash", "POST", "/api/filebrowser/trash/purge", {"id": "trash-1"}),
            ("fb_empty_trash", "DELETE", "/api/filebrowser/trash/empty", None),
        ]

        for target_name, method, url, payload in cases:
            with self.subTest(target_name=target_name), patch(
                f"services.api_filebrowser_routes.{target_name}",
                side_effect=RuntimeError(f"{target_name} failed"),
            ):
                response = self.client.request(method, url, json=payload)

            self.assertEqual(response.status_code, 400)
            self.assertFalse(response.json()["ok"])
            self.assertIn(f"{target_name} failed", response.json()["error"])

    @patch("services.api_filebrowser_routes.fb_list_trash")
    @patch("services.api_filebrowser_routes.fb_restore_trash")
    @patch("services.api_filebrowser_routes.fb_purge_trash")
    @patch("services.api_filebrowser_routes.fb_empty_trash")
    def test_trash_routes_delegate(self, mock_empty, mock_purge, mock_restore, mock_list):
        mock_list.return_value = {"items": [{"id": "trash-1"}]}
        mock_restore.return_value = {"restored": "C:\\old.txt"}
        mock_purge.return_value = {"purged": "trash-1"}
        mock_empty.return_value = {"deleted": 1}

        list_resp = self.client.get("/api/filebrowser/trash")
        restore_resp = self.client.post("/api/filebrowser/trash/restore", json={"id": "trash-1"})
        purge_resp = self.client.post("/api/filebrowser/trash/purge", json={"id": "trash-1"})
        empty_resp = self.client.request("DELETE", "/api/filebrowser/trash/empty")

        self.assertEqual(list_resp.json()["items"], [{"id": "trash-1"}])
        self.assertEqual(restore_resp.json()["restored"], "C:\\old.txt")
        self.assertEqual(purge_resp.json()["purged"], "trash-1")
        self.assertEqual(empty_resp.json()["deleted"], 1)


if __name__ == "__main__":
    unittest.main()
