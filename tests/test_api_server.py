"""Tests for api_server helpers and JobRegistry"""
import asyncio
import unittest
from unittest.mock import Mock, patch


class TestJobRegistry(unittest.TestCase):
    def _make_registry(self):
        from services.api_server import JobRegistry
        return JobRegistry()

    def test_register_job(self):
        registry = self._make_registry()
        job_id = registry.register("job1", "transcode", "Transcode Video")
        self.assertEqual(job_id, "job1")
        snapshot = registry.snapshot()
        jobs = snapshot["jobs"]
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["id"], "job1")
        self.assertEqual(jobs[0]["status"], "pending")

    def test_update_job(self):
        registry = self._make_registry()
        registry.register("job1", "transcode", "Transcode Video")
        registry.update("job1", "processing", 50.0)
        snapshot = registry.snapshot()
        job = snapshot["jobs"][0]
        self.assertEqual(job["stage"], "processing")
        self.assertEqual(job["percent"], 50.0)
        self.assertEqual(job["status"], "running")

    def test_finish_job_success(self):
        registry = self._make_registry()
        registry.register("job1", "transcode", "Transcode Video")
        registry.finish("job1", success=True)
        snapshot = registry.snapshot()
        job = snapshot["jobs"][0]
        self.assertEqual(job["status"], "done")
        self.assertEqual(job["percent"], 100.0)

    def test_finish_job_failure(self):
        registry = self._make_registry()
        registry.register("job1", "transcode", "Transcode Video")
        registry.finish("job1", success=False)
        snapshot = registry.snapshot()
        job = snapshot["jobs"][0]
        self.assertEqual(job["status"], "error")

    def test_update_nonexistent_job(self):
        registry = self._make_registry()
        registry.update("nonexistent", "stage", 50.0)
        snapshot = registry.snapshot()
        self.assertEqual(len(snapshot["jobs"]), 0)

    def test_add_remove_ws(self):
        registry = self._make_registry()
        mock_ws = Mock()
        registry.add_ws(mock_ws)
        self.assertIn(mock_ws, registry._ws_clients)
        registry.remove_ws(mock_ws)
        self.assertNotIn(mock_ws, registry._ws_clients)

    def test_snapshot_has_system(self):
        registry = self._make_registry()
        snapshot = registry.snapshot()
        self.assertIn("jobs", snapshot)
        self.assertIn("system", snapshot)


class TestResultSuccess(unittest.TestCase):
    def test_result_success_with_ok_true(self):
        from services.api_server import _result_success
        self.assertTrue(_result_success({"ok": True}))

    def test_result_success_with_ok_false(self):
        from services.api_server import _result_success
        self.assertFalse(_result_success({"ok": False}))

    def test_result_success_with_output_path(self):
        from services.api_server import _result_success
        self.assertTrue(_result_success({"output_path": "/some/path.mp4"}))

    def test_result_success_with_output_paths(self):
        from services.api_server import _result_success
        self.assertTrue(_result_success({"output_paths": ["/path1.mp4"]}))

    def test_result_success_with_summary_rows(self):
        from services.api_server import _result_success
        self.assertTrue(_result_success({"summary_rows": [["状态", "成功"]]}))
        self.assertFalse(_result_success({"summary_rows": [["状态", "失败"]]}))

    def test_result_success_non_dict(self):
        from services.api_server import _result_success
        self.assertTrue(_result_success(True))
        self.assertFalse(_result_success(False))
        self.assertFalse(_result_success(None))


class TestLoopExceptionHandler(unittest.TestCase):
    def test_suppresses_windows_proactor_connection_reset_noise(self):
        from services.api_server import _handle_loop_exception

        loop = Mock()
        exc = ConnectionResetError(10054, "connection reset")
        exc.winerror = 10054
        _handle_loop_exception(
            loop,
            {
                "exception": exc,
                "handle": "<Handle _ProactorBasePipeTransport._call_connection_lost()>",
            },
        )

        loop.default_exception_handler.assert_not_called()

    def test_delegates_other_loop_exceptions(self):
        from services.api_server import _handle_loop_exception

        loop = Mock()
        context = {"exception": RuntimeError("boom"), "handle": "<Handle something_else>"}
        _handle_loop_exception(loop, context)

        loop.default_exception_handler.assert_called_once_with(context)


class TestFrontendDevProxy(unittest.TestCase):
    def test_proxy_frontend_dev_request_forwards_path_and_query(self):
        from services import api_server

        request = Mock()
        request.method = "GET"
        request.url.query = "foo=bar"
        request.headers.items.return_value = [("accept", "text/html"), ("host", "127.0.0.1:7860")]

        upstream = Mock()
        upstream.status_code = 200
        upstream.content = b"<html>ok</html>"
        upstream.headers.items.return_value = [("content-type", "text/html; charset=utf-8")]

        with patch.object(api_server, "FRONTEND_DEV_SERVER", "http://127.0.0.1:5173"), patch(
            "services.api_server.requests.request", return_value=upstream
        ) as request_mock:
            response = asyncio.run(api_server._proxy_frontend_dev_request(request, "dashboard"))

        request_mock.assert_called_once_with(
            "GET",
            "http://127.0.0.1:5173/dashboard?foo=bar",
            headers={"accept": "text/html"},
            timeout=10,
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.body, b"<html>ok</html>")
        self.assertEqual(response.headers["content-type"], "text/html; charset=utf-8")

    def test_proxy_frontend_dev_request_returns_502_when_vite_is_down(self):
        from services import api_server

        request = Mock()
        request.method = "GET"
        request.url.query = ""
        request.headers.items.return_value = []

        with patch.object(api_server, "FRONTEND_DEV_SERVER", "http://127.0.0.1:5173"), patch(
            "services.api_server.requests.request", side_effect=api_server.requests.RequestException("boom")
        ):
            response = asyncio.run(api_server._proxy_frontend_dev_request(request, ""))

        self.assertEqual(response.status_code, 502)
        self.assertIn(b"frontend dev server unavailable", response.body)


if __name__ == "__main__":
    unittest.main()
