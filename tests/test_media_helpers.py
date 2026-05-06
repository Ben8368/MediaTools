"""Tests for media service helper functions"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path


class TestMediaHelpers(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_ensure_explicit_output_path(self):
        from backend.services.media import _ensure_explicit_output_path
        result = _ensure_explicit_output_path(None)
        self.assertIsNone(result)

        path = str(Path(self.temp_dir) / "subdir" / "output.mp4")
        result = _ensure_explicit_output_path(path)
        self.assertEqual(result, path)
        self.assertTrue(Path(path).parent.exists())

    def test_move_file_to_workspace_dir_not_exists(self):
        from backend.services.media import _move_file_to_workspace_dir
        result = _move_file_to_workspace_dir("/nonexistent.mp4", Path(self.temp_dir))
        self.assertEqual(result, "/nonexistent.mp4")

    def test_move_file_to_workspace_dir_same_location(self):
        from backend.services.media import _move_file_to_workspace_dir
        source = Path(self.temp_dir) / "video.mp4"
        source.write_bytes(b"\x00" * 10)
        result = _move_file_to_workspace_dir(str(source), Path(self.temp_dir))
        self.assertEqual(Path(result).resolve(), source.resolve())

    def test_move_file_to_workspace_dir_moves_file(self):
        from backend.services.media import _move_file_to_workspace_dir
        source_dir = Path(self.temp_dir) / "source"
        source_dir.mkdir()
        source = source_dir / "video.mp4"
        source.write_bytes(b"\x00" * 10)

        target_dir = Path(self.temp_dir) / "target"
        result = _move_file_to_workspace_dir(str(source), target_dir)

        self.assertFalse(source.exists())
        self.assertTrue(Path(result).exists())
        self.assertTrue(Path(result).parent == target_dir)

    def test_move_file_to_workspace_dir_collision(self):
        from backend.services.media import _move_file_to_workspace_dir
        source_dir = Path(self.temp_dir) / "source"
        source_dir.mkdir()
        source = source_dir / "video.mp4"
        source.write_bytes(b"\x00" * 10)

        target_dir = Path(self.temp_dir) / "target"
        target_dir.mkdir()
        existing = target_dir / "video.mp4"
        existing.write_bytes(b"\x00" * 5)

        result = _move_file_to_workspace_dir(str(source), target_dir)
        self.assertIn("video_1.mp4", result)

    def test_normalize_subtitle_outputs(self):
        from backend.services.media import _normalize_subtitle_outputs
        source_dir = Path(self.temp_dir) / "source"
        source_dir.mkdir()
        sub1 = source_dir / "sub.srt"
        sub1.write_text("subtitle", encoding="utf-8")

        workspace = {
            "subtitles_dir": str(Path(self.temp_dir) / "subtitles")
        }
        subtitle_result = {
            "original": {"srt": str(sub1)},
            "zh": {},
            "errors": ["warning1"]
        }

        result = _normalize_subtitle_outputs(subtitle_result, workspace)
        self.assertIn("srt", result["original"])
        self.assertEqual(len(result["errors"]), 1)

    def test_default_transcode_output_path_h265(self):
        from backend.services.media import _default_transcode_output_path
        workspace = {"transcoded_dir": self.temp_dir}
        result = _default_transcode_output_path("/input/video.mp4", "H.265 (HEVC)", workspace)
        self.assertIn("h265", result)
        self.assertTrue(result.endswith(".mp4"))

    def test_default_transcode_output_path_h264(self):
        from backend.services.media import _default_transcode_output_path
        workspace = {"transcoded_dir": self.temp_dir}
        result = _default_transcode_output_path("/input/video.mp4", "H.264 (AVC)", workspace)
        self.assertIn("h264", result)

    def test_default_transcode_output_path_audio(self):
        from backend.services.media import _default_transcode_output_path
        workspace = {"transcoded_dir": self.temp_dir}
        result = _default_transcode_output_path("/input/video.mp4", "提取音频", workspace)
        self.assertTrue(result.endswith(".mp3"))

    def test_default_slice_output_path(self):
        from backend.services.media import _default_slice_output_path
        workspace = {"clips_dir": self.temp_dir}
        result = _default_slice_output_path("/input/video.mp4", "00:01:30", "00:02:45", workspace)
        self.assertIn("000130", result)
        self.assertIn("000245", result)

    def test_write_analysis_artifact(self):
        from backend.services.media import _write_analysis_artifact
        workspace = {"analysis_dir": self.temp_dir}
        payload = {"highlights": [{"time": "00:00:10"}]}
        result = _write_analysis_artifact("test_analysis", payload, workspace)
        self.assertTrue(Path(result).exists())
        content = json.loads(Path(result).read_text(encoding="utf-8"))
        self.assertIn("highlights", content)

    def test_build_fetch_state(self):
        from backend.services.media import _build_fetch_state
        state = _build_fetch_state(["url1", "url2", "url3"])
        self.assertEqual(state["total"], 3)
        self.assertEqual(state["success_count"], 0)
        self.assertEqual(state["current_index"], 0)
        self.assertIsInstance(state["logs"], list)

    def test_compute_fetch_progress_zero_total(self):
        from backend.services.media import _compute_fetch_progress
        result = _compute_fetch_progress(0, 0, "stage", 0.5)
        self.assertEqual(result, 0.0)

    def test_compute_fetch_progress_normal(self):
        from backend.services.media import _compute_fetch_progress
        result = _compute_fetch_progress(10, 5, "stage", 0.5)
        self.assertGreater(result, 0.0)
        self.assertLessEqual(result, 100.0)


if __name__ == "__main__":
    unittest.main()
