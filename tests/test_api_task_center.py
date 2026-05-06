import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from services.api_server import app
from services.task_center import TaskCenter, TaskStatus, TaskType


class TestApiTaskCenterRoutes(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.task_center = TaskCenter(str(Path(self.temp_dir.name) / "tasks.db"))
        self.task_center.create_task("task-1", TaskType.DOWNLOAD, "Download")
        self.task_center.create_task("task-2", TaskType.TRANSCODE, "Transcode")
        self.task_center.update_task("task-2", status=TaskStatus.RUNNING, progress=20, stage="encoding")
        self.client = TestClient(app)
        self.patch_get = patch("services.api_task_center.get_task_center", return_value=self.task_center)
        self.patch_get.start()

    def tearDown(self):
        self.patch_get.stop()
        self.temp_dir.cleanup()

    def test_list_tasks_filters_by_status_and_type(self):
        response = self.client.get("/api/tasks/list", params={"status": "running", "task_type": "transcode"})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual([task["id"] for task in data["tasks"]], ["task-2"])

    def test_list_tasks_rejects_unknown_enum(self):
        response = self.client.get("/api/tasks/list", params={"status": "bogus"})

        self.assertEqual(response.status_code, 400)

    def test_list_tasks_clamps_limit_to_safe_bounds(self):
        for index in range(3, 8):
            self.task_center.create_task(f"task-{index}", TaskType.DOWNLOAD, f"Download {index}")

        low_response = self.client.get("/api/tasks/list", params={"limit": 0})
        high_response = self.client.get("/api/tasks/list", params={"limit": 5000})

        self.assertEqual(low_response.status_code, 200)
        self.assertEqual(len(low_response.json()["tasks"]), 1)
        self.assertEqual(high_response.status_code, 200)
        self.assertEqual(len(high_response.json()["tasks"]), 7)

    def test_active_tasks(self):
        response = self.client.get("/api/tasks/active")

        self.assertEqual(response.status_code, 200)
        active_ids = {task["id"] for task in response.json()["tasks"]}
        self.assertEqual(active_ids, {"task-1", "task-2"})

    def test_get_and_cancel_task(self):
        get_response = self.client.get("/api/tasks/task-1")
        cancel_response = self.client.post("/api/tasks/task-1/cancel")

        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(cancel_response.status_code, 200)
        self.assertEqual(cancel_response.json()["task"]["status"], "cancelled")

    def test_cancel_missing_task(self):
        response = self.client.post("/api/tasks/missing/cancel")

        self.assertEqual(response.status_code, 404)

    def test_delete_rejects_active_task_unless_explicitly_allowed(self):
        reject_response = self.client.delete("/api/tasks/task-2")
        allow_response = self.client.delete("/api/tasks/task-2", params={"allow_active": True})

        self.assertEqual(reject_response.status_code, 400)
        self.assertEqual(allow_response.status_code, 200)
        self.assertIsNone(self.task_center.get_task("task-2"))

    def test_history_routes_are_not_shadowed_by_task_id_route(self):
        response = self.client.get("/api/tasks/history/week")
        cleanup = self.client.delete("/api/tasks/history/cleanup")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(cleanup.status_code, 200)

    def test_weekly_history_returns_only_terminal_tasks_sorted_newest_first(self):
        self.task_center.update_task("task-1", status=TaskStatus.COMPLETED)
        self.task_center.create_task("task-3", TaskType.DOWNLOAD, "Failed")
        self.task_center.update_task("task-3", status=TaskStatus.FAILED)
        self.task_center.create_task("task-4", TaskType.DOWNLOAD, "Pending")

        response = self.client.get("/api/tasks/history/week")

        self.assertEqual(response.status_code, 200)
        task_ids = [task["id"] for task in response.json()["tasks"]]
        self.assertEqual(task_ids[:2], ["task-3", "task-1"])
        self.assertNotIn("task-2", task_ids)
        self.assertNotIn("task-4", task_ids)

    def test_clear_terminal_download_records_keeps_running_and_non_download_tasks(self):
        self.task_center.update_task("task-1", status=TaskStatus.COMPLETED)
        self.task_center.create_task("task-3", TaskType.DOWNLOAD, "Failed")
        self.task_center.update_task("task-3", status=TaskStatus.FAILED)
        self.task_center.create_task("task-4", TaskType.TRANSCODE, "Done transcode")
        self.task_center.update_task("task-4", status=TaskStatus.COMPLETED)

        response = self.client.post("/api/tasks/clear", json={"terminal_only": True})

        self.assertEqual(response.status_code, 200)
        remaining_ids = {task["id"] for task in self.task_center.list_tasks()}
        self.assertEqual(remaining_ids, {"task-2", "task-4"})

    def test_clear_selected_records_allows_terminal_and_active_ids(self):
        response = self.client.post("/api/tasks/clear", json={"ids": ["task-1", "task-2"], "terminal_only": False})

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.task_center.get_task("task-1"))
        self.assertIsNone(self.task_center.get_task("task-2"))


if __name__ == "__main__":
    unittest.main()
