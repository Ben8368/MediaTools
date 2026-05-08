"""HTTP routes for /api/model-config."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.api_test_helpers import make_client


class TestModelConfigRoutes(unittest.TestCase):
    def test_post_and_put_save_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "model_config.json"

            with patch("backend.services.model_config._get_config_file", return_value=cfg_path):
                client = make_client()
                body = {"baseUrl": "https://example.com/v1", "model": "gpt-test", "apiKey": "sk-local"}

                r_post = client.post("/api/model-config", json=body)
                self.assertEqual(r_post.status_code, 200, r_post.text)
                self.assertEqual(r_post.json()["model"], "gpt-test")

                r_put = client.put(
                    "/api/model-config",
                    json={"baseUrl": "", "model": "other", "apiKey": ""},
                )
                self.assertEqual(r_put.status_code, 200, r_put.text)
                stored = json.loads(cfg_path.read_text(encoding="utf-8"))
                self.assertEqual(stored["model"], "other")

                r_get = client.get("/api/model-config")
                self.assertEqual(r_get.status_code, 200)
                self.assertEqual(r_get.json()["model"], "other")

                r_del = client.delete("/api/model-config")
                self.assertEqual(r_del.status_code, 200)
                self.assertFalse(cfg_path.exists())


if __name__ == "__main__":
    unittest.main()
