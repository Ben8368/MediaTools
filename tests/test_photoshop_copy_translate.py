"""photoshop_copy_translate：换行保留与行数校验。"""

import unittest
from unittest.mock import MagicMock, patch


class TestPhotoshopCopyTranslate(unittest.TestCase):
    def test_horizontal_strip_keeps_newlines(self):
        from backend.services.photoshop_copy_translate import _horizontal_outer_strip, _normalize_newlines

        self.assertEqual(_horizontal_outer_strip("  a\nb\t  "), "a\nb")
        self.assertEqual(_normalize_newlines("a\rb\n"), "a\nb\n")

    @patch("backend.services.photoshop_copy_translate.localization_batch_translate")
    @patch("backend.services.photoshop_copy_translate.get_api_config")
    def test_rejects_line_count_mismatch(self, mock_cfg, mock_translate):
        mock_cfg.return_value = {"api_key": "k", "api_base_url": "http://x", "analysis_model": "m"}
        mock_translate.return_value = '{"items":[{"i":0,"t":"only one line"}]}'

        from backend.services.photoshop_copy_translate import translate_photoshop_copy_items

        r = translate_photoshop_copy_items([{"index": 0, "text": "line1\nline2", "locale": "en-US"}])
        self.assertFalse(r["ok"])
        self.assertIn("行数", r.get("error", ""))

    @patch("backend.services.photoshop_copy_translate.localization_batch_translate")
    @patch("backend.services.photoshop_copy_translate.get_api_config")
    def test_accepts_matching_newlines(self, mock_cfg, mock_translate):
        mock_cfg.return_value = {"api_key": "k", "api_base_url": "http://x", "analysis_model": "m"}
        mock_translate.return_value = '{"items":[{"i":0,"t":"L1\\nL2"}]}'

        from backend.services.photoshop_copy_translate import translate_photoshop_copy_items

        r = translate_photoshop_copy_items([{"index": 0, "text": "a\nb", "locale": "en-US"}])
        self.assertTrue(r["ok"])
        self.assertEqual(r["items"][0]["text"], "L1\nL2")
