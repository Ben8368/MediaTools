"""CLI for the MediaTools generator module."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.generator.screenshot import ScreenshotGenerator
from modules.generator.wechat_moments import WechatMomentsGenerator


def main() -> None:
    parser = argparse.ArgumentParser(description="MediaTools generator CLI")
    subparsers = parser.add_subparsers(dest="command")

    screenshot_parser = subparsers.add_parser("screenshot", help="Extract screenshot from video")
    screenshot_parser.add_argument("video_path", help="Video file path")
    screenshot_parser.add_argument("timestamp", help="Timestamp (HH:MM:SS or seconds)")
    screenshot_parser.add_argument("-o", "--output", required=True, help="Output image path")
    screenshot_parser.add_argument("-q", "--quality", type=int, default=2, help="Image quality (1-31, lower is better)")

    batch_parser = subparsers.add_parser("batch-screenshot", help="Extract multiple screenshots")
    batch_parser.add_argument("video_path", help="Video file path")
    batch_parser.add_argument("timestamps", nargs="+", help="List of timestamps")
    batch_parser.add_argument("-o", "--output-dir", required=True, help="Output directory")
    batch_parser.add_argument("-t", "--template", default="frame_{index:04d}.jpg", help="Filename template")
    batch_parser.add_argument("-q", "--quality", type=int, default=2, help="Image quality")

    # 朋友圈图片生成
    moments_parser = subparsers.add_parser("wechat-moments", help="Generate WeChat moments image")
    moments_subparsers = moments_parser.add_subparsers(dest="moments_command")

    moments_subparsers.add_parser("status", help="Show WeChat moments generator status")
    moments_subparsers.add_parser("draft", help="Show current draft")

    export_parser = moments_subparsers.add_parser("export", help="Export moments image")
    export_parser.add_argument("-o", "--output", help="Output image path")

    args = parser.parse_args()

    if args.command == "screenshot":
        generator = ScreenshotGenerator()
        result = generator.extract_frame(
            args.video_path,
            args.timestamp,
            args.output,
            args.quality,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result["success"] else 1)

    elif args.command == "batch-screenshot":
        generator = ScreenshotGenerator()
        result = generator.extract_multiple_frames(
            args.video_path,
            args.timestamps,
            args.output_dir,
            args.template,
            args.quality,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result["success"] else 1)

    elif args.command == "wechat-moments":
        generator = WechatMomentsGenerator()

        if args.moments_command == "status":
            result = generator.get_status()
            print(json.dumps(result, ensure_ascii=False, indent=2))

        elif args.moments_command == "draft":
            result = generator.get_draft()
            print(json.dumps(result, ensure_ascii=False, indent=2))

        elif args.moments_command == "export":
            result = generator.export_image(output_path=args.output)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            sys.exit(0 if result["success"] else 1)

        else:
            moments_parser.print_help()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
