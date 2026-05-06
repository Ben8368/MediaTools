import tempfile
import unittest
from pathlib import Path

from backend.services.task_center import TaskCenter, TaskStatus, TaskType


class TestTaskCenter(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "tasks.db")
        self.task_center = TaskCenter(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_pause_resume_are_not_fake_supported(self):
        self.task_center.create_task("task-1", TaskType.DOWNLOAD, "download")
        self.task_center.update_task("task-1", status=TaskStatus.RUNNING)

        with self.assertRaises(NotImplementedError):
            self.task_center.pause_task("task-1")
        with self.assertRaises(NotImplementedError):
            self.task_center.resume_task("task-1")

        self.assertEqual(self.task_center.get_task("task-1")["status"], TaskStatus.RUNNING.value)

    def test_active_tasks_exclude_legacy_paused_tasks(self):
        self.task_center.create_task("pending", TaskType.DOWNLOAD, "pending")
        self.task_center.create_task("paused", TaskType.DOWNLOAD, "paused")
        self.task_center.update_task("paused", status=TaskStatus.PAUSED)

        active_ids = {task["id"] for task in self.task_center.get_active_tasks()}

        self.assertIn("pending", active_ids)
        self.assertNotIn("paused", active_ids)


if __name__ == "__main__":
    unittest.main()
