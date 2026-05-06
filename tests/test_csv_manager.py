import tempfile
import unittest
from pathlib import Path

from modules.fetcher.csv_manager import CSVManager, _safe_int


class TestCSVManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.csv_path = Path(self.temp_dir.name) / "records.csv"
        self.manager = CSVManager(str(self.csv_path))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_safe_int(self):
        self.assertEqual(_safe_int("12"), 12)
        self.assertEqual(_safe_int(""), 0)
        self.assertEqual(_safe_int("bad", default=7), 7)

    def test_read_all_missing_file(self):
        self.assertEqual(self.manager.read_all(), [])

    def test_add_video_writes_readable_subtitle_statuses(self):
        self.manager.add_video(
            {
                "video_id": "v1",
                "title": "Video",
                "duration": "10",
                "view_count": "100",
                "has_auto_subs": True,
                "chinese_subs_status": "downloaded",
                "ignored": "not written",
            },
            highlights=[{"start": 1}],
        )

        rows = self.manager.read_all()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["original_subs"], "auto_generated")
        self.assertEqual(rows[0]["chinese_subs"], "downloaded")
        self.assertEqual(rows[0]["highlights_count"], "1")
        self.assertNotIn("ignored", rows[0])

    def test_get_stats(self):
        self.manager.add_video({"duration": "10", "view_count": "100"}, highlights=[])
        self.manager.add_video({"duration": "bad", "view_count": "25"}, highlights=[{}])

        stats = self.manager.get_stats()

        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["total_duration"], 10)
        self.assertEqual(stats["total_views"], 125)
        self.assertEqual(stats["with_highlights"], 1)


if __name__ == "__main__":
    unittest.main()
