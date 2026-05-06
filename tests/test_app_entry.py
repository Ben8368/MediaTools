import unittest
from unittest.mock import patch

import app


class TestAppEntry(unittest.TestCase):
    def test_loopback_host_detection(self):
        self.assertTrue(app._is_loopback_host("127.0.0.1"))
        self.assertTrue(app._is_loopback_host("localhost"))
        self.assertTrue(app._is_loopback_host("::1"))
        self.assertFalse(app._is_loopback_host("0.0.0.0"))
        self.assertFalse(app._is_loopback_host("192.168.1.10"))

    @patch("app.configure_windows_event_loop")
    @patch("app.uvicorn.run")
    @patch("app.API_SECRET_KEY", "")
    def test_main_rejects_non_loopback_without_api_key(self, mock_run, _mock_loop):
        with patch("sys.argv", ["app.py", "--host", "0.0.0.0"]):
            with self.assertRaises(SystemExit) as ctx:
                app.main()

        self.assertEqual(ctx.exception.code, 2)
        mock_run.assert_not_called()

    @patch("app.configure_windows_event_loop")
    @patch("app.uvicorn.run")
    @patch("app.API_SECRET_KEY", "secret")
    def test_main_allows_non_loopback_with_api_key(self, mock_run, _mock_loop):
        with patch("sys.argv", ["app.py", "--host", "0.0.0.0", "--port", "9999"]):
            app.main()

        mock_run.assert_called_once()
        self.assertEqual(mock_run.call_args.kwargs["host"], "0.0.0.0")
        self.assertEqual(mock_run.call_args.kwargs["port"], 9999)


if __name__ == "__main__":
    unittest.main()
