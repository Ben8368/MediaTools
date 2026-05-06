import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.services.api_assets_routes import create_router


class FakeAssetLibrary:
    def __init__(self, root):
        self.root = root
        self.truncated = False

    def scan(self, root, max_files=0):
        self.scan_root = root
        self.max_files = max_files
        return [
            {"name": "clip.mp4", "type": "video"},
            {"name": "song.wav", "type": "audio"},
            {"name": "notes.txt", "type": "other"},
        ]

    def get_stats(self):
        return {"total": 3}


class TestApiAssetsRoutes(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.workspace = {"project_root": str(self.root)}
        self.resolve_error = None
        app = FastAPI()
        app.include_router(
            create_router(
                lambda: self.workspace,
                self.resolve_allowed_path,
                FakeAssetLibrary,
                lambda: 25,
            )
        )
        self.client = TestClient(app)

    def tearDown(self):
        self.temp_dir.cleanup()

    def resolve_allowed_path(self, path, workspace):
        if self.resolve_error:
            raise self.resolve_error
        return Path(path)

    def test_assets_list_scans_workspace_and_filters_results(self):
        response = self.client.get("/api/assets/list", params={"keyword": "clip", "asset_type": "video"})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["items"], [{"name": "clip.mp4", "type": "video"}])
        self.assertEqual(data["scan_limit"], 25)
        self.assertEqual(data["stats"], {"total": 3})

    def test_assets_list_rejects_non_directory(self):
        target = self.root / "file.txt"
        target.write_text("x", encoding="utf-8")

        response = self.client.get("/api/assets/list", params={"directory": str(target)})

        self.assertEqual(response.status_code, 400)
        self.assertIn("directory", response.json()["error"])

    def test_assets_list_reports_resolver_errors(self):
        self.resolve_error = ValueError("outside")

        response = self.client.get("/api/assets/list", params={"directory": "bad"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "outside")


if __name__ == "__main__":
    unittest.main()
