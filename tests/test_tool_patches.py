"""Tests for declarative external-tool command patches."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import patches.tool_patches as tool_patches


class TestToolPatches(unittest.TestCase):
    def setUp(self):
        tool_patches._MANUAL_COMMAND_PATCHES.clear()
        tool_patches._FILE_COMMAND_PATCHES.clear()
        tool_patches._LOADED_PATCH_FILES.clear()
        tool_patches._LOAD_ERRORS.clear()
        tool_patches._EXTRA_PATCH_PATHS.clear()
        tool_patches._DEFAULT_LOAD_SIGNATURE = None
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        tool_patches._MANUAL_COMMAND_PATCHES.clear()
        tool_patches._FILE_COMMAND_PATCHES.clear()
        tool_patches._LOADED_PATCH_FILES.clear()
        tool_patches._LOAD_ERRORS.clear()
        tool_patches._EXTRA_PATCH_PATHS.clear()
        tool_patches._DEFAULT_LOAD_SIGNATURE = None

    def _write_json(self, name: str, payload: object) -> Path:
        path = Path(self.temp_dir) / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_normalize_helpers(self):
        self.assertEqual(tool_patches._normalize_args(None), [])
        self.assertEqual(tool_patches._normalize_args(["--a", 2, ""]), ["--a", "2"])
        self.assertEqual(tool_patches._normalize_args(" --flag "), ["--flag"])
        self.assertCountEqual(tool_patches._normalize_values({"a", "b"}), ["a", "b"])

    def test_context_matches_supported_fields(self):
        command = ["yt-dlp", "--dump-json", "https://example.com/video"]
        context = {"operation": "info", "url": "https://example.com/video"}
        self.assertTrue(tool_patches._context_matches({"command_contains": "--dump-json"}, command, context))
        self.assertTrue(tool_patches._context_matches({"url_contains": ["nope", "example.com"]}, command, context))
        self.assertTrue(tool_patches._context_matches({"operation": ["download", "info"]}, command, context))
        self.assertFalse(tool_patches._context_matches({"command_contains": ["--missing"]}, command, context))
        self.assertFalse(tool_patches._context_matches({"url_contains": "youtube.com"}, command, context))
        self.assertFalse(tool_patches._context_matches({"operation": "download"}, command, context))

    def test_insert_args(self):
        self.assertEqual(
            tool_patches._insert_args(["bin", "-i", "in.mp4"], "-i", ["-safe", "0"], after=False),
            ["bin", "-safe", "0", "-i", "in.mp4"],
        )
        self.assertEqual(
            tool_patches._insert_args(["bin", "-i", "in.mp4"], "-i", ["file"], after=True),
            ["bin", "-i", "file", "in.mp4"],
        )
        self.assertEqual(tool_patches._insert_args(["bin", "x"], "--missing", ["--a"], after=True), ["bin", "--a", "x"])
        self.assertEqual(tool_patches._insert_args([], "--missing", ["--a"], after=True), ["--a"])

    def test_patch_spec_applies_all_operations(self):
        patch_fn = tool_patches._patch_from_spec(
            {
                "match": {"operation": "download"},
                "replace_binary": "patched-bin",
                "remove_args": ["--old"],
                "prepend_args": ["--pre"],
                "insert_before": {"arg": "-i", "args": ["--before"]},
                "insert_after": {"arg": "-i", "args": ["--after"]},
                "append_args": ["--tail"],
            }
        )
        result = patch_fn(["bin", "--old", "-i", "input"], {"operation": "download"})
        self.assertEqual(result, ["patched-bin", "--pre", "--before", "-i", "--after", "input", "--tail"])
        self.assertEqual(patch_fn(["bin"], {"operation": "info"}), ["bin"])
        self.assertEqual(tool_patches._patch_from_spec({"enabled": False})(["bin"], {}), ["bin"])

    def test_manual_and_file_patches_apply_in_order(self):
        tool_patches.register_command_patch_spec("ffmpeg", {"append_args": ["file"]}, source="file")
        tool_patches.register_command_patch("ffmpeg", lambda command, context: [*command, "manual"])
        with patch.object(tool_patches, "ensure_default_patch_configs_loaded", return_value=None):
            result = tool_patches.apply_command_patches("ffmpeg", ["ffmpeg"], {"operation": "x"})
            count = tool_patches.list_command_patches("ffmpeg")
        self.assertEqual(result, ["ffmpeg", "file", "manual"])
        self.assertEqual(count, {"ffmpeg": 2})

    def test_load_patch_specs_accepts_object_or_list(self):
        path = self._write_json(
            "patches.json",
            {"tools": {"yt": {"append_args": "--a"}, "ff": [{"append_args": "--b"}]}},
        )
        specs = tool_patches._load_patch_specs(path)
        self.assertEqual(len(specs["yt"]), 1)
        self.assertEqual(len(specs["ff"]), 1)

    def test_load_patch_specs_rejects_bad_shapes(self):
        with self.assertRaises(ValueError):
            tool_patches._load_patch_specs(self._write_json("bad-root.json", []))
        with self.assertRaises(ValueError):
            tool_patches._load_patch_specs(self._write_json("bad-tools.json", {"tools": []}))
        with self.assertRaises(ValueError):
            tool_patches._load_patch_specs(self._write_json("bad-spec.json", {"tools": {"yt": "bad"}}))

    def test_load_file_and_diagnostics(self):
        good = self._write_json("good.json", {"tools": {"yt": [{"append_args": ["--a"]}]}})
        bad = self._write_json("bad.json", {"tools": []})
        missing = Path(self.temp_dir) / "missing.json"

        with patch.object(tool_patches, "get_default_patch_config_paths", return_value=[good, bad, missing]):
            tool_patches.ensure_default_patch_configs_loaded(force=True)
            diagnostics = tool_patches.get_patch_diagnostics()

        self.assertEqual(diagnostics["counts"], {"yt": 1})
        self.assertEqual(len(diagnostics["loaded_files"]), 1)
        self.assertIn(str(bad.resolve()), diagnostics["errors"])

    def test_load_command_patch_file_adds_extra_path(self):
        path = self._write_json("extra.json", {"tools": {"yt": [{"append_args": ["--extra"]}]}})
        tool_patches.load_command_patch_file(path)
        result = tool_patches.apply_command_patches("yt", ["yt"], {})
        self.assertEqual(result, ["yt", "--extra"])
