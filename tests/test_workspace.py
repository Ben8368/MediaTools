"""Tests for workspace service"""
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class TestWorkspaceFunctions(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _make_workspace(self, root: str) -> dict:
        from services.workspace import _workspace_payload
        return _workspace_payload(Path(root))

    def test_workspace_payload_keys(self):
        ws = self._make_workspace(self.temp_dir)
        expected_keys = [
            "project_root", "inputs_dir", "downloads_dir", "decrypted_dir",
            "transcoded_dir", "clips_dir", "subtitles_dir", "analysis_dir",
            "assets_dir", "imports_dir", "exports_dir", "cache_dir",
            "logs_dir", "manifests_dir",
        ]
        for key in expected_keys:
            self.assertIn(key, ws)

    def test_workspace_payload_creates_dirs(self):
        ws = self._make_workspace(self.temp_dir)
        self.assertTrue(Path(ws["project_root"]).exists())
        self.assertTrue(Path(ws["downloads_dir"]).exists())
        self.assertTrue(Path(ws["clips_dir"]).exists())

    def test_workspace_payload_paths_under_root(self):
        ws = self._make_workspace(self.temp_dir)
        root = Path(ws["project_root"])
        self.assertTrue(Path(ws["downloads_dir"]).is_relative_to(root))
        self.assertTrue(Path(ws["clips_dir"]).is_relative_to(root))

    def test_set_and_get_current_workspace(self):
        from services.workspace import get_current_workspace, set_current_workspace
        ws = set_current_workspace(self.temp_dir)
        self.assertEqual(Path(ws["project_root"]).resolve(), Path(self.temp_dir).resolve())
        loaded = get_current_workspace()
        self.assertEqual(loaded["project_root"], ws["project_root"])

    def test_set_current_workspace_enforces_allowed_root(self):
        from services.workspace import set_current_workspace
        with patch("services.workspace.WORKSPACE_ALLOWED_ROOTS", [Path(self.temp_dir) / "allowed"]):
            with self.assertRaises(ValueError):
                set_current_workspace(self.temp_dir, enforce_allowed_root=True)

    def test_get_workspace_dir_known_key(self):
        from services.workspace import get_workspace_dir, set_current_workspace
        set_current_workspace(self.temp_dir)
        d = get_workspace_dir("clips")
        self.assertIsInstance(d, Path)
        self.assertTrue(str(d).endswith("clips"))

    def test_get_workspace_dir_with_suffix(self):
        from services.workspace import get_workspace_dir, set_current_workspace
        set_current_workspace(self.temp_dir)
        d = get_workspace_dir("clips_dir")
        self.assertIsInstance(d, Path)

    def test_get_workspace_dir_unknown_raises(self):
        from services.workspace import get_workspace_dir, set_current_workspace
        set_current_workspace(self.temp_dir)
        with self.assertRaises(KeyError):
            get_workspace_dir("nonexistent_thing")

    def test_workspace_path_returns_path(self):
        from services.workspace import set_current_workspace, workspace_path
        set_current_workspace(self.temp_dir)
        p = workspace_path("clips", "myclip.mp4")
        self.assertIsInstance(p, Path)
        self.assertTrue(p.name == "myclip.mp4")

    def test_workspace_path_ensure_parent(self):
        from services.workspace import set_current_workspace, workspace_path
        set_current_workspace(self.temp_dir)
        p = workspace_path("clips", "sub", "myclip.mp4", ensure_parent=True)
        self.assertTrue(p.parent.exists())

    def test_derive_output_path(self):
        from services.workspace import derive_output_path, set_current_workspace
        set_current_workspace(self.temp_dir)
        p = derive_output_path("clips", "/some/video.mp4", suffix="_out")
        self.assertEqual(p.name, "video_out.mp4")

    def test_derive_output_path_custom_extension(self):
        from services.workspace import derive_output_path, set_current_workspace
        set_current_workspace(self.temp_dir)
        p = derive_output_path("clips", "/some/video.mp4", extension=".mkv")
        self.assertEqual(p.suffix, ".mkv")

    def test_format_workspace_text(self):
        from services.workspace import format_workspace_text, set_current_workspace
        set_current_workspace(self.temp_dir)
        text = format_workspace_text()
        self.assertIn("项目根目录", text)
        self.assertIn("下载目录", text)
        self.assertIn("切片目录", text)

    def test_get_current_workspace_fallback_on_bad_json(self):
        from services.workspace import RUNTIME_DIR, WORKSPACE_FILE, get_current_workspace
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        WORKSPACE_FILE.write_text("not valid json", encoding="utf-8")
        with self.assertLogs("services.workspace", level="WARNING") as logs:
            ws = get_current_workspace()
        self.assertIn("project_root", ws)
        self.assertTrue(any("Invalid workspace config" in item for item in logs.output))


if __name__ == "__main__":
    unittest.main()
