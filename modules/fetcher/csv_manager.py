"""CSV storage for downloaded media records."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from backend.config import BASE_DIR, CSV_FIELDS


def _safe_int(value, default=0):
    try:
        return int(value or default)
    except (ValueError, TypeError):
        return default


class CSVManager:
    def __init__(self, csv_path: str | None = None):
        default_csv_path = BASE_DIR / "runtime" / "youtube_videos.csv"
        self.csv_path = Path(csv_path) if csv_path else default_csv_path
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate_legacy_csv()

    def _migrate_legacy_csv(self) -> None:
        legacy_csv = BASE_DIR / "youtube_videos.csv"
        if self.csv_path == legacy_csv or self.csv_path.exists() or not legacy_csv.exists():
            return
        try:
            legacy_csv.replace(self.csv_path)
        except OSError:
            return

    def add_video(self, info: dict, highlights: list | None = None) -> None:
        row = dict.fromkeys(CSV_FIELDS, "")
        row.update({key: value for key, value in info.items() if key in CSV_FIELDS})

        if info.get("has_manual_subs"):
            row["original_subs"] = "downloaded"
        elif info.get("has_auto_subs"):
            row["original_subs"] = "auto_generated"
        else:
            row["original_subs"] = "none"

        row["chinese_subs"] = info.get("chinese_subs_status", "pending")
        row["subtitle_path"] = info.get("subtitle_path", "")
        row["download_time"] = datetime.now().isoformat()

        if highlights is not None:
            row["highlights_count"] = len(highlights)

        file_exists = self.csv_path.exists()
        with self.csv_path.open("a", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)

    def read_all(self) -> list[dict]:
        if not self.csv_path.exists():
            return []
        with self.csv_path.open("r", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))

    def get_stats(self) -> dict:
        videos = self.read_all()
        if not videos:
            return {"total": 0}
        return {
            "total": len(videos),
            "total_duration": sum(_safe_int(item.get("duration")) for item in videos),
            "total_views": sum(_safe_int(item.get("view_count")) for item in videos),
            "with_highlights": sum(1 for item in videos if _safe_int(item.get("highlights_count")) > 0),
        }
