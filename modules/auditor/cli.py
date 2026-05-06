"""CLI for the MediaTools auditor module."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.services.auditor import get_auditor_config, get_auditor_status, run_auditor_scan_once


def main() -> None:
    parser = argparse.ArgumentParser(description="MediaTools auditor CLI")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("status", help="Show the staged Auditor integration status")
    subparsers.add_parser("config", help="Show the workspace Auditor config")
    subparsers.add_parser("run-once", help="Run a one-shot workspace scan using the Auditor config")

    args = parser.parse_args()
    if args.command in {None, "status"}:
        print(json.dumps(get_auditor_status(), ensure_ascii=False, indent=2))
        return
    if args.command == "config":
        print(json.dumps(get_auditor_config(), ensure_ascii=False, indent=2))
        return
    if args.command == "run-once":
        print(json.dumps(run_auditor_scan_once(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
