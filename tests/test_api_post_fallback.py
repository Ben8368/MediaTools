"""POST /api/* 回退路由：未知路径返回 404 JSON，避免 SPA GET 回退导致 405。"""

import unittest

from fastapi.testclient import TestClient

from backend.api.server import app


class TestApiPostFallback(unittest.TestCase):
    def test_unknown_post_under_api_returns_404_json(self):
        client = TestClient(app)
        response = client.post("/api/__mediatools_unknown_route__/segment", json={})

        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data["ok"])
        self.assertIn("未知接口", data["error"])
