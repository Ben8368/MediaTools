import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.api_adobe_routes import create_router


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


class TestApiAdobeRoutes(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = {"project_root": str(Path(self.temp_dir.name))}
        self.job_registry = FakeJobRegistry()
        self.get_photoshop_status = MagicMock(return_value={"ok": True, "tool": "photoshop"})
        app = FastAPI()
        app.include_router(create_router(self.job_registry, lambda: self.workspace, self.get_photoshop_status))
        self.client = TestClient(app)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_status_routes(self):
        self.assertEqual(self.client.get("/api/adobe/photoshop/status").json()["tool"], "photoshop")

        with patch("modules.adobe.after_effects.get_ae_status", return_value={"ok": True, "tool": "ae"}) as get_ae_status:
            response = self.client.get("/api/adobe/after_effects/status")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["tool"], "ae")
        get_ae_status.assert_called_once_with(self.workspace)

        self.assertEqual(self.client.get("/api/adobe/unknown/status").status_code, 400)

    def test_ae_scan_success_and_error(self):
        with patch("modules.adobe.after_effects.scan_ae_project", return_value={"ok": True, "ticket_id": "ae-1"}) as scan:
            response = self.client.post("/api/adobe/after_effects/scan", json={"file_path": "project.aep"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertTrue(self.job_registry.finished[payload["job_id"]])
        scan.assert_called_once_with(project_path="project.aep", workspace=self.workspace)

        with patch("modules.adobe.after_effects.scan_ae_project", side_effect=RuntimeError("AE offline")):
            response = self.client.post("/api/adobe/after_effects/scan", json={"file_path": "project.aep"})

        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.job_registry.finished[response.json()["job_id"]])

    def test_ae_ticket_routes_and_errors(self):
        with patch("modules.adobe.after_effects.list_ae_tickets", return_value=[{"id": "ae-1"}]):
            self.assertEqual(self.client.get("/api/adobe/after_effects/tickets").json()["items"], [{"id": "ae-1"}])

        with patch("modules.adobe.after_effects.get_ae_ticket", return_value={"ticket": {"id": "ae-1"}}):
            self.assertEqual(self.client.get("/api/adobe/after_effects/tickets/ae-1").json()["ticket"]["id"], "ae-1")

        with patch("modules.adobe.after_effects.get_ae_ticket", side_effect=FileNotFoundError("missing")):
            self.assertEqual(self.client.get("/api/adobe/after_effects/tickets/missing").status_code, 404)

        with patch("modules.adobe.after_effects.get_ae_ticket", side_effect=ValueError("bad id")):
            self.assertEqual(self.client.get("/api/adobe/after_effects/tickets/bad").status_code, 400)

        with patch("modules.adobe.after_effects.save_ae_ticket", return_value={"ticket": {"id": "ae-1"}}):
            self.assertEqual(
                self.client.put("/api/adobe/after_effects/tickets/ae-1", json={"ticket": {"id": "ae-1"}}).status_code,
                200,
            )

        with patch("modules.adobe.after_effects.save_ae_ticket", side_effect=RuntimeError("cannot save")):
            self.assertEqual(
                self.client.put("/api/adobe/after_effects/tickets/ae-1", json={"ticket": {"id": "ae-1"}}).status_code,
                400,
            )

    def test_ae_execute_success_cancelled_and_error(self):
        def start_success(*args, **kwargs):
            kwargs["on_progress"]("render", 35.0)
            kwargs["on_finish"](True, {"status": "completed"})
            return {"ok": True, "job_id": kwargs["job_id"]}

        with patch("modules.adobe.after_effects.start_ae_ticket_execution", side_effect=start_success) as start:
            response = self.client.post(
                "/api/adobe/after_effects/tickets/ae-1/execute",
                json={"dry_run": True, "selected_task_indexes": [2]},
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.job_registry.finished[response.json()["job_id"]])
        self.assertEqual(start.call_args.kwargs["selected_task_indexes"], [2])
        self.assertTrue(any(update[1] == "render" for update in self.job_registry.updates))

        self.job_registry.finished.clear()
        self.job_registry.updates.clear()

        def start_cancelled(*args, **kwargs):
            kwargs["on_finish"](False, {"status": "cancelled"})
            return {"ok": True, "job_id": kwargs["job_id"]}

        with patch("modules.adobe.after_effects.start_ae_ticket_execution", side_effect=start_cancelled):
            self.assertEqual(
                self.client.post("/api/adobe/after_effects/tickets/ae-1/execute", json={}).status_code,
                200,
            )
        self.assertFalse(self.job_registry.finished)
        self.assertTrue(any(update[3] == "error" for update in self.job_registry.updates))

        with patch("modules.adobe.after_effects.start_ae_ticket_execution", side_effect=RuntimeError("cannot execute")):
            response = self.client.post("/api/adobe/after_effects/tickets/ae-1/execute", json={})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.job_registry.finished[response.json()["job_id"]])

    def test_ae_execution_and_cancel_routes(self):
        with patch("modules.adobe.common.execution.get_execution_state", return_value={"status": "running"}):
            self.assertEqual(
                self.client.get("/api/adobe/after_effects/executions/ae-1").json()["state"]["status"],
                "running",
            )

        with patch("modules.adobe.common.execution.get_execution_state", return_value=None):
            self.assertEqual(self.client.get("/api/adobe/after_effects/executions/missing").status_code, 404)

        with patch("modules.adobe.common.execution.cancel_execution", return_value={"status": "cancelled"}):
            self.assertEqual(self.client.post("/api/adobe/after_effects/executions/ae-1/cancel").status_code, 200)

        with patch("modules.adobe.common.execution.cancel_execution", side_effect=FileNotFoundError("missing")):
            self.assertEqual(self.client.post("/api/adobe/after_effects/executions/missing/cancel").status_code, 404)

        with patch("modules.adobe.common.execution.cancel_execution", side_effect=RuntimeError("busy")):
            self.assertEqual(self.client.post("/api/adobe/after_effects/executions/busy/cancel").status_code, 400)

    def test_ae_auxiliary_routes_delegate_to_after_effects_service(self):
        with patch("modules.adobe.after_effects.list_ae_fonts", return_value={"ok": True, "items": ["Arial"]}) as call:
            self.assertEqual(self.client.get("/api/adobe/after_effects/fonts", params={"query": "Ar", "limit": 5}).status_code, 200)
        call.assert_called_once_with(query="Ar", limit=5, workspace=self.workspace)

        routes = [
            (
                "modules.adobe.after_effects.create_ae_checkpoint",
                "post",
                "/api/adobe/after_effects/checkpoints/create",
                {"file_path": "project.aep", "label": "v1", "step_index": 2, "notes": "ok"},
            ),
            (
                "modules.adobe.after_effects.revert_ae_checkpoint",
                "post",
                "/api/adobe/after_effects/checkpoints/revert",
                {"file_path": "checkpoint.json", "create_branch": True},
            ),
            (
                "modules.adobe.after_effects.add_ae_to_render_queue",
                "post",
                "/api/adobe/after_effects/render/add",
                {"file_path": "project.aep", "comp_index": 3, "output_path": "out.mov"},
            ),
            (
                "modules.adobe.after_effects.start_ae_render",
                "post",
                "/api/adobe/after_effects/render/start",
                {"file_path": "project.aep"},
            ),
        ]
        for target, method, url, body in routes:
            with self.subTest(url=url), patch(target, return_value={"ok": True}) as call:
                response = getattr(self.client, method)(url, json=body)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.json()["ok"])
                self.assertEqual(call.call_args.kwargs["workspace"], self.workspace)

        with patch("modules.adobe.after_effects.list_ae_checkpoints", return_value={"ok": True, "items": []}) as call:
            response = self.client.get("/api/adobe/after_effects/checkpoints", params={"project_path": "project.aep"})
        self.assertEqual(response.status_code, 200)
        call.assert_called_once_with(project_path="project.aep", workspace=self.workspace)

        with patch("modules.adobe.after_effects.get_ae_render_queue_status", return_value={"ok": True}) as call:
            response = self.client.get("/api/adobe/after_effects/render/status", params={"project_path": "project.aep"})
        self.assertEqual(response.status_code, 200)
        call.assert_called_once_with(project_path="project.aep", workspace=self.workspace)


if __name__ == "__main__":
    unittest.main()
