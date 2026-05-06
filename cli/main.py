#!/usr/bin/env python3
"""Unified MediaTools CLI entrypoint."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ["PATH"] = str(PROJECT_ROOT / "bin") + os.pathsep + os.environ.get("PATH", "")

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

MODULE_ALIASES = {
    "fetch": "fetcher",
    "encode": "encoder",
    "decrypt": "decryptor",
    "edit": "editor",
}

CANONICAL_MODULES = [
    "fetcher",
    "encoder",
    "decryptor",
    "assets",
    "workbench",
    "editor",
    "photoshop",
    "auditor",
    "generator",
]


def _dispatch_module(module_name: str, extra_args: list[str]) -> None:
    if module_name == "fetcher":
        from modules.fetcher.cli import main as cli_main
    elif module_name == "encoder":
        from modules.encoder.cli import main as cli_main
    elif module_name == "decryptor":
        from modules.decryptor.cli import main as cli_main
    elif module_name == "assets":
        from modules.assets.cli import main as cli_main
    elif module_name == "workbench":
        from modules.workbench.cli import main as cli_main
    elif module_name == "editor":
        from modules.editor.cli import main as cli_main
    elif module_name == "photoshop":
        from modules.photoshop.cli import main as cli_main
    elif module_name == "auditor":
        from modules.auditor.cli import main as cli_main
    elif module_name == "generator":
        from modules.generator.cli import main as cli_main
    else:
        raise SystemExit(f"Unknown module: {module_name}")

    sys.argv = [f"{sys.argv[0]} {module_name}"] + extra_args
    cli_main()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MediaTools CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Canonical modules:
  fetcher    Media download and subtitle processing
  encoder    Video/audio transcoding and slicing
  decryptor  Music and media decryption
  assets     Workspace asset indexing
  workbench  Subtitle analysis and clip export
  editor     Experimental CapCut integration
  photoshop  Photoshop automation
  auditor    Audit pipeline staging area
  generator  Asset generation (screenshots, WeChat moments, etc.)

Legacy aliases still accepted:
  fetch   -> fetcher
  encode  -> encoder
  decrypt -> decryptor
  edit    -> editor

Examples:
  python main.py fetcher download https://youtube.com/watch?v=xxx
  python main.py fetch ytdlp status
  python main.py workbench analyze subtitle.srt --clip-count 5
  python main.py photoshop status
  python main.py generator screenshot video.mp4 00:01:30 -o frame.jpg
  python main.py generator wechat-moments status
  python main.py auditor status
        """,
    )

    parser.add_argument(
        "module",
        choices=CANONICAL_MODULES + sorted(MODULE_ALIASES),
        help="Module name",
    )
    parser.add_argument("args", nargs=argparse.REMAINDER, help="Module subcommands and arguments")

    args = parser.parse_args()
    canonical_module = MODULE_ALIASES.get(args.module, args.module)
    _dispatch_module(canonical_module, args.args)


if __name__ == "__main__":
    main()
