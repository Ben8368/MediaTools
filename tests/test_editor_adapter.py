import unittest
from unittest.mock import Mock, patch

import requests

from modules.editor.adapter import CapcutAdapter


class TestCapcutAdapter(unittest.TestCase):
    def test_rejects_unsupported_direct_mode(self):
        with self.assertRaises(ValueError):
            CapcutAdapter(mode="direct")

    @patch("modules.editor.adapter.requests.Session")
    def test_create_draft_posts_to_capcut_service(self, mock_session_cls):
        response = Mock()
        response.json.return_value = {"draft_id": "draft-1"}
        mock_session = mock_session_cls.return_value
        mock_session.post.return_value = response

        adapter = CapcutAdapter(base_url="http://capcut.test/", timeout=5)
        result = adapter.create_draft(width=720, height=1280)

        self.assertEqual(result["draft_id"], "draft-1")
        mock_session.post.assert_called_once_with(
            "http://capcut.test/openapi/capcut-mate/v1/create_draft",
            json={"width": 720, "height": 1280},
            timeout=5,
        )
        response.raise_for_status.assert_called_once()

    @patch("modules.editor.adapter.requests.Session")
    def test_status_reports_unavailable_on_connection_error(self, mock_session_cls):
        mock_session = mock_session_cls.return_value
        mock_session.get.side_effect = requests.ConnectionError("offline")

        adapter = CapcutAdapter(base_url="http://capcut.test", timeout=5)
        result = adapter.status()

        self.assertFalse(result["available"])
        self.assertEqual(result["base_url"], "http://capcut.test")
        self.assertIn("offline", result["error"])


if __name__ == "__main__":
    unittest.main()
