"""Tests for AssetLibrary"""
import shutil
import tempfile
import unittest
from pathlib import Path


class TestAssetLibrary(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _make_library(self):
        from modules.assets.library import AssetLibrary
        return AssetLibrary(self.temp_dir)

    def test_scan_empty_dir(self):
        lib = self._make_library()
        result = lib.scan()
        self.assertEqual(result, [])

    def test_scan_nonexistent_dir(self):
        from modules.assets.library import AssetLibrary
        lib = AssetLibrary("/nonexistent/path")
        result = lib.scan()
        self.assertEqual(result, [])

    def test_scan_finds_video(self):
        (Path(self.temp_dir) / "video.mp4").write_bytes(b"\x00" * 100)
        lib = self._make_library()
        result = lib.scan()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "video")
        self.assertEqual(result[0]["name"], "video.mp4")

    def test_scan_finds_audio(self):
        (Path(self.temp_dir) / "audio.mp3").write_bytes(b"\x00" * 50)
        lib = self._make_library()
        result = lib.scan()
        self.assertEqual(result[0]["type"], "audio")

    def test_scan_finds_subtitle(self):
        (Path(self.temp_dir) / "sub.srt").write_text("1\n00:00:01,000 --> 00:00:03,000\nHello\n", encoding="utf-8")
        lib = self._make_library()
        result = lib.scan()
        self.assertEqual(result[0]["type"], "subtitle")

    def test_scan_ignores_non_media(self):
        (Path(self.temp_dir) / "readme.txt").write_text("text")
        (Path(self.temp_dir) / "script.py").write_text("code")
        lib = self._make_library()
        result = lib.scan()
        self.assertEqual(result, [])

    def test_scan_recursive(self):
        subdir = Path(self.temp_dir) / "subdir"
        subdir.mkdir()
        (subdir / "video.mp4").write_bytes(b"\x00" * 100)
        lib = self._make_library()
        result = lib.scan()
        self.assertEqual(len(result), 1)
        self.assertFalse(lib.truncated)

    def test_scan_respects_max_files(self):
        for index in range(3):
            (Path(self.temp_dir) / f"video-{index}.mp4").write_bytes(b"\x00" * 100)
        lib = self._make_library()
        result = lib.scan(max_files=2)
        self.assertEqual(len(result), 2)
        self.assertTrue(lib.truncated)

    def test_list_assets_by_type(self):
        (Path(self.temp_dir) / "video.mp4").write_bytes(b"\x00" * 100)
        (Path(self.temp_dir) / "audio.mp3").write_bytes(b"\x00" * 50)
        lib = self._make_library()
        lib.scan()
        videos = lib.list_assets("video")
        self.assertEqual(len(videos), 1)
        self.assertEqual(videos[0]["type"], "video")

    def test_list_assets_all(self):
        (Path(self.temp_dir) / "video.mp4").write_bytes(b"\x00" * 100)
        (Path(self.temp_dir) / "audio.mp3").write_bytes(b"\x00" * 50)
        lib = self._make_library()
        lib.scan()
        all_assets = lib.list_assets()
        self.assertEqual(len(all_assets), 2)

    def test_search_by_keyword(self):
        (Path(self.temp_dir) / "interview_clip.mp4").write_bytes(b"\x00" * 100)
        (Path(self.temp_dir) / "background.mp4").write_bytes(b"\x00" * 100)
        lib = self._make_library()
        lib.scan()
        results = lib.search("interview")
        self.assertEqual(len(results), 1)
        self.assertIn("interview", results[0]["name"])

    def test_get_stats(self):
        (Path(self.temp_dir) / "video.mp4").write_bytes(b"\x00" * 1024 * 1024)
        (Path(self.temp_dir) / "audio.mp3").write_bytes(b"\x00" * 512 * 1024)
        lib = self._make_library()
        lib.scan()
        stats = lib.get_stats()
        self.assertEqual(stats["total"], 2)
        self.assertIn("video", stats["by_type"])
        self.assertIn("audio", stats["by_type"])

    def test_get_file_type(self):
        from modules.assets.library import _get_file_type
        self.assertEqual(_get_file_type(".mp4"), "video")
        self.assertEqual(_get_file_type(".mp3"), "audio")
        self.assertEqual(_get_file_type(".jpg"), "image")
        self.assertEqual(_get_file_type(".srt"), "subtitle")
        self.assertEqual(_get_file_type(".xyz"), "other")


if __name__ == "__main__":
    unittest.main()
