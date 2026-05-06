import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.api_files_routes import create_router


class TestApiFilesRoutes(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.file_manager = MagicMock()
        self.preview_generator = MagicMock()
        self.workspace = {"cache_dir": str(self.root / "cache")}
        self.extract_icon = MagicMock(return_value={"ok": True, "output_png": "icon.png"})
        app = FastAPI()
        app.include_router(
            create_router(
                lambda: self.file_manager,
                lambda: self.workspace,
                lambda: self.preview_generator,
                lambda: 1024,
                self.extract_icon,
            )
        )
        self.client = TestClient(app)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_basic_file_operations_delegate_to_file_manager(self):
        self.file_manager.list_directory.return_value = {"files": [], "directories": []}
        self.file_manager.create_directory.return_value = {"path": "new"}
        self.file_manager.delete.return_value = {"path": "old.txt"}
        self.file_manager.rename.return_value = {"path": "new.txt"}
        self.file_manager.copy.return_value = {"path": "copy.txt"}
        self.file_manager.move.return_value = {"path": "moved.txt"}
        self.file_manager.get_file_info.return_value = {"name": "file.txt"}

        self.assertEqual(self.client.get("/api/files/list", params={"directory": "."}).status_code, 200)
        self.assertEqual(self.client.post("/api/files/mkdir", json={"path": "new"}).status_code, 200)
        self.assertEqual(self.client.request("DELETE", "/api/files/delete", json={"path": "old.txt"}).status_code, 200)
        self.assertEqual(self.client.post("/api/files/rename", json={"old_path": "old.txt", "new_name": "new.txt"}).status_code, 200)
        self.assertEqual(self.client.post("/api/files/copy", json={"source_path": "a.txt", "dest_path": "b.txt"}).status_code, 200)
        self.assertEqual(self.client.post("/api/files/move", json={"source_path": "a.txt", "dest_path": "c.txt"}).status_code, 200)
        self.assertEqual(self.client.get("/api/files/info", params={"path": "file.txt"}).json()["name"], "file.txt")

    def test_file_manager_error_returns_400(self):
        self.file_manager.list_directory.side_effect = ValueError("bad path")

        response = self.client.get("/api/files/list", params={"directory": ".."})

        self.assertEqual(response.status_code, 400)
        self.assertIn("bad path", response.json()["error"])

    def test_preview_rejects_non_file_large_and_unsupported_files(self):
        missing = self.root / "folder"
        missing.mkdir()
        self.file_manager._validate_path.return_value = missing
        response = self.client.get("/api/files/preview", params={"path": "folder"})
        self.assertEqual(response.status_code, 400)

        large = self.root / "large.jpg"
        large.write_bytes(b"x" * 2048)
        self.file_manager._validate_path.return_value = large
        response = self.client.get("/api/files/preview", params={"path": "large.jpg"})
        self.assertEqual(response.status_code, 413)

        small = self.root / "small.bin"
        small.write_bytes(b"x")
        self.file_manager._validate_path.return_value = small
        self.preview_generator.can_preview.return_value = {"can_preview": False}
        response = self.client.get("/api/files/preview", params={"path": "small.bin"})
        self.assertEqual(response.status_code, 400)

    def test_preview_image_audio_and_video_use_preview_generator(self):
        sample = self.root / "sample.media"
        sample.write_bytes(b"x")
        self.file_manager._validate_path.return_value = sample

        self.preview_generator.can_preview.return_value = {"can_preview": True, "preview_type": "image"}
        self.preview_generator.generate_image_preview.return_value = {"preview_type": "image"}
        response = self.client.get("/api/files/preview", params={"path": "sample.media"})
        self.assertEqual(response.json()["preview_type"], "image")

        self.preview_generator.can_preview.return_value = {"can_preview": True, "preview_type": "audio"}
        self.preview_generator.generate_audio_waveform.return_value = {"preview_type": "audio"}
        response = self.client.get("/api/files/preview", params={"path": "sample.media"})
        self.assertEqual(response.json()["preview_type"], "audio")

        self.preview_generator.can_preview.return_value = {"can_preview": True, "preview_type": "video"}
        self.preview_generator.generate_video_thumbnail.return_value = {"preview_type": "video"}
        response = self.client.get("/api/files/preview", params={"path": "sample.media", "timestamp": "00:00:02"})
        self.assertEqual(response.json()["preview_type"], "video")
        self.assertTrue((self.root / "cache" / "previews").exists())

    def test_extract_icon_delegates(self):
        response = self.client.post("/api/files/extract-icon", json={"exe_path": "app.exe", "output_png": "icon.png"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.extract_icon.assert_called_once_with("app.exe", "icon.png")


if __name__ == "__main__":
    unittest.main()
