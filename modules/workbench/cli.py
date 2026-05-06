"""CLI for the MediaTools workbench module."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.workbench import analyze_subtitle_for_workbench, export_clips_from_workbench, list_workspace_media


def _load_clips_json(clips_file: str | None, clips_json: str | None) -> str:
    if clips_json:
        return clips_json
    if clips_file:
        return Path(clips_file).read_text(encoding="utf-8")
    raise ValueError("Either --clips-file or --clips-json is required")


def main() -> None:
    parser = argparse.ArgumentParser(description="MediaTools workbench CLI")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("media", help="List workspace videos, subtitles, and recent exports")

    analyze_parser = subparsers.add_parser("analyze", help="Analyze subtitle highlights for workbench")
    analyze_parser.add_argument("subtitle_path", help="Path to subtitle file")
    analyze_parser.add_argument("--clip-count", type=int, default=5, help="Number of suggested clips")

    export_parser = subparsers.add_parser("export", help="Export clips from workbench JSON")
    export_parser.add_argument("video_path", help="Path to source video")
    export_parser.add_argument("--subtitle-path", default="", help="Optional subtitle path for burn-in")
    export_group = export_parser.add_mutually_exclusive_group(required=True)
    export_group.add_argument("--clips-file", help="Path to a JSON file containing clips")
    export_group.add_argument("--clips-json", help="Inline JSON string containing clips")
    export_parser.add_argument("--no-burn-subtitles", action="store_true", help="Disable subtitle burn-in")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    if args.command == "media":
        print(json.dumps(list_workspace_media(), ensure_ascii=False, indent=2))
        return

    if args.command == "analyze":
        result = analyze_subtitle_for_workbench(args.subtitle_path, args.clip_count)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not result.get("ok"):
            raise SystemExit(1)
        return

    if args.command == "export":
        clips_json = _load_clips_json(args.clips_file, args.clips_json)
        result = export_clips_from_workbench(
            args.video_path,
            args.subtitle_path,
            clips_json,
            burn_subtitles=not args.no_burn_subtitles,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not result.get("ok"):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
