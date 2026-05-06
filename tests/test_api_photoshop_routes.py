import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.api_photoshop_routes import create_router


class FakeJobRegistry:
    def __init__(self):
        self.finished = {}
        self.updates = []
        self.registered = []

    def register(self, job_id, job_type, name):
        self.registered.append((job_id, job_type, name))
        return job_id

    def update(self, job_id, stage, percent, status="running"):
        self.updates.append((job_id, stage, percent, status))

    def finish(self, job_id, success=True):
        self.finished[job_id] = success


class TestApiPhotoshopRoutes(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = {"project_root": str(Path(self.temp_dir.name))}
        self.job_registry = FakeJobRegistry()
        self.get_status = MagicMock(return_value={"ok": True, "connected": False})
        self.scan_document = MagicMock(return_value={"ok": True, "ticket_id": "ps-1"})
        self.list_tickets = MagicMock(return_value=[{"id": "ps-1"}])
        self.get_ticket = MagicMock(return_value={"ticket": {"id": "ps-1"}})
        self.save_ticket = MagicMock(return_value={"ticket": {"id": "ps-1", "name": "updated"}})
        self.start_execution = MagicMock(return_value={"ok": True, "execution_id": "job-1"})
        self.get_execution_state = MagicMock(return_value={"status": "running"})
        self.cancel_execution = MagicMock(return_value={"status": "cancelled"})

        app = FastAPI()
        app.include_router(
            create_router(
                self.job_registry,
                lambda: self.workspace,
                self.get_status,
                self.scan_document,
                self.list_tickets,
                self.get_ticket,
                self.save_ticket,
                self.start_execution,
                self.get_execution_state,
                self.cancel_execution,
            )
        )
        self.client = TestClient(app)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_status_and_ticket_listing_delegate_to_service(self):
        self.assertEqual(self.client.get("/api/photoshop/status").json()["connected"], False)

        response = self.client.get("/api/photoshop/tickets")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"], [{"id": "ps-1"}])
        self.list_tickets.assert_called_once_with(self.workspace)

    def test_scan_finishes_registered_job(self):
        response = self.client.post(
            "/api/photoshop/scan",
            json={"psd_path": "design.psd", "languages": ["zh"], "timeout_sec": 5},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertIn("job_id", payload)
        self.assertTrue(self.job_registry.finished[payload["job_id"]])
        self.scan_document.assert_called_once_with(
            psd_path="design.psd",
            languages=["zh"],
            timeout_sec=5,
            workspace=self.workspace,
        )

    def test_scan_error_returns_400_and_marks_job_failed(self):
        self.scan_document.side_effect = RuntimeError("Photoshop unavailable")

        response = self.client.post("/api/photoshop/scan", json={"psd_path": "broken.psd"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("Photoshop unavailable", response.json()["error"])
        self.assertFalse(self.job_registry.finished[response.json()["job_id"]])

    def test_ticket_detail_update_and_error_paths(self):
        self.assertEqual(self.client.get("/api/photoshop/tickets/ps-1").json()["ticket"]["id"], "ps-1")
        self.assertEqual(
            self.client.put("/api/photoshop/tickets/ps-1", json={"ticket": {"id": "ps-1"}}).status_code,
            200,
        )

        self.get_ticket.side_effect = FileNotFoundError("missing")
        self.assertEqual(self.client.get("/api/photoshop/tickets/missing").status_code, 404)

        self.get_ticket.side_effect = ValueError("bad id")
        self.assertEqual(self.client.get("/api/photoshop/tickets/bad").status_code, 400)

        self.save_ticket.side_effect = RuntimeError("cannot save")
        self.assertEqual(
            self.client.put("/api/photoshop/tickets/ps-1", json={"ticket": {"id": "ps-1"}}).status_code,
            400,
        )

    def test_execute_passes_selection_and_callbacks_update_job(self):
        def start_execution(*args, **kwargs):
            kwargs["on_progress"]("step 1", 50.0)
            kwargs["on_finish"](True, {"status": "completed"})
            return {"ok": True, "job_id": kwargs["job_id"]}

        self.start_execution.side_effect = start_execution

        response = self.client.post(
            "/api/photoshop/tickets/ps-1/execute",
            json={"dry_run": True, "selected_task_indexes": [1, 3]},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertTrue(self.job_registry.finished[payload["job_id"]])
        self.assertTrue(any(update[1] == "step 1" for update in self.job_registry.updates))
        call_kwargs = self.start_execution.call_args.kwargs
        self.assertEqual(call_kwargs["selected_task_indexes"], [1, 3])
        self.assertTrue(call_kwargs["dry_run"])

    def test_execute_cancelled_callback_does_not_finish_successfully(self):
        def start_execution(*args, **kwargs):
            kwargs["on_finish"](False, {"status": "cancelled"})
            return {"ok": True, "job_id": kwargs["job_id"]}

        self.start_execution.side_effect = start_execution

        response = self.client.post("/api/photoshop/tickets/ps-1/execute", json={})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.job_registry.finished)
        self.assertTrue(any(update[3] == "error" for update in self.job_registry.updates))

    def test_execution_lookup_and_cancel_errors(self):
        self.assertEqual(self.client.get("/api/photoshop/executions/ps-1").json()["state"]["status"], "running")

        self.get_execution_state.return_value = None
        self.assertEqual(self.client.get("/api/photoshop/executions/missing").status_code, 404)

        self.assertEqual(self.client.post("/api/photoshop/executions/ps-1/cancel").status_code, 200)

        self.cancel_execution.side_effect = FileNotFoundError("missing")
        self.assertEqual(self.client.post("/api/photoshop/executions/missing/cancel").status_code, 404)


if __name__ == "__main__":
    unittest.main()
