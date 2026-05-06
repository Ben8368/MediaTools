"""Tests for subtitle processor"""
import shutil
import tempfile
import unittest
from pathlib import Path


class TestSubtitleProcessor(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        from modules.fetcher.subtitle import SubtitleProcessor
        self.processor = SubtitleProcessor()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_parse_srt_basic(self):
        srt_content = """1
00:00:01,000 --> 00:00:03,000
First subtitle

2
00:00:04,000 --> 00:00:06,000
Second subtitle
"""
        srt_path = Path(self.temp_dir) / "test.srt"
        srt_path.write_text(srt_content, encoding="utf-8")
        segments = self.processor.parse_srt(str(srt_path))
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0]["text"], "First subtitle")
        self.assertEqual(segments[1]["index"], 2)

    def test_parse_srt_with_bom(self):
        srt_content = """1
00:00:01,000 --> 00:00:03,000
Test
"""
        srt_path = Path(self.temp_dir) / "test.srt"
        srt_path.write_text(srt_content, encoding="utf-8-sig")
        segments = self.processor.parse_srt(str(srt_path))
        self.assertEqual(len(segments), 1)

    def test_format_for_llm(self):
        segments = [
            {"start": "00:00:01,000", "end": "00:00:03,000", "text": "Hello"},
            {"start": "00:00:04,000", "end": "00:00:06,000", "text": "World"},
        ]
        result = self.processor.format_for_llm(segments)
        self.assertIn("[00:00:01,000 --> 00:00:03,000] Hello", result)
        self.assertIn("[00:00:04,000 --> 00:00:06,000] World", result)

    def test_convert_vtt_to_text(self):
        vtt_content = """WEBVTT

00:00:01.000 --> 00:00:03.000
First line

00:00:04.000 --> 00:00:06.000
Second line
"""
        vtt_path = Path(self.temp_dir) / "test.vtt"
        vtt_path.write_text(vtt_content, encoding="utf-8")
        result = self.processor.convert_vtt_to_text(str(vtt_path))
        self.assertIn("First line", result)
        self.assertIn("Second line", result)


class TestVttParsing(unittest.TestCase):
    def test_clean_vtt_text_removes_tags(self):
        from modules.fetcher.subtitle import _clean_vtt_text
        text = "<c.yellow>Hello</c> <v Speaker>World</v>"
        result = _clean_vtt_text(text)
        self.assertEqual(result, "Hello World")

    def test_clean_vtt_text_removes_prefix(self):
        from modules.fetcher.subtitle import _clean_vtt_text
        text = ">>> Test"
        result = _clean_vtt_text(text)
        self.assertEqual(result, "Test")

    def test_timestamp_to_millis(self):
        from modules.fetcher.subtitle import _timestamp_to_millis
        self.assertEqual(_timestamp_to_millis("00:01:30.500"), 90500)
        self.assertEqual(_timestamp_to_millis("00:00:05,250"), 5250)

    def test_normalize_vtt_timestamp(self):
        from modules.fetcher.subtitle import _normalize_vtt_timestamp
        self.assertEqual(_normalize_vtt_timestamp("01:30.500"), "00:01:30,500")
        self.assertEqual(_normalize_vtt_timestamp("00:01:30.500"), "00:01:30,500")

    def test_deduplicate_vtt_segments_merges_progressive_captions(self):
        from modules.fetcher.subtitle import _deduplicate_vtt_segments

        segments = [
            {"start": "00:00:00,000", "end": "00:00:02,870", "text": "So, today we are making Angry Birds from"},
            {"start": "00:00:02,870", "end": "00:00:02,880", "text": "So, today we are making Angry Birds from"},
            {"start": "00:00:02,880", "end": "00:00:05,390", "text": "So, today we are making Angry Birds from scratch only using AI and I'm excited to"},
            {"start": "00:00:05,390", "end": "00:00:05,400", "text": "scratch only using AI and I'm excited to"},
            {"start": "00:00:05,400", "end": "00:00:07,030", "text": "scratch only using AI and I'm excited to see what we produce in this video. Now,"},
            {"start": "00:00:07,030", "end": "00:00:07,040", "text": "see what we produce in this video. Now,"},
        ]

        cleaned = _deduplicate_vtt_segments(segments)

        self.assertEqual(len(cleaned), 1)
        self.assertEqual(
            cleaned[0]["text"],
            "So, today we are making Angry Birds from scratch only using AI and I'm excited to see what we produce in this video. Now,",
        )
        self.assertEqual(cleaned[0]["start"], "00:00:00,000")
        self.assertEqual(cleaned[0]["end"], "00:00:07,040")


if __name__ == "__main__":
    unittest.main()
