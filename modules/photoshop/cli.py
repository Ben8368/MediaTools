"""CLI for the MediaTools Photoshop module."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.services.photoshop import (
    cancel_execution,
    get_execution_state,
    get_photoshop_status,
    get_photoshop_ticket,
    list_photoshop_tickets,
    scan_photoshop_document,
    start_ticket_execution,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="MediaTools Photoshop automation CLI")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("status", help="Show Photoshop runtime status")
    subparsers.add_parser("tickets", help="List saved Photoshop tickets in the current workspace")

    scan_parser = subparsers.add_parser("scan", help="Scan an open PSD or a provided PSD path")
    scan_parser.add_argument("--psd-path", default="", help="Optional PSD path")
    scan_parser.add_argument("--languages", nargs="*", default=[], help="Optional language codes")
    scan_parser.add_argument("--timeout-sec", type=int, default=180, help="Scan timeout in seconds")

    show_parser = subparsers.add_parser("show", help="Show a saved ticket")
    show_parser.add_argument("ticket_id", help="Ticket id")

    exec_parser = subparsers.add_parser("execute", help="Execute a saved ticket")
    exec_parser.add_argument("ticket_id", help="Ticket id")
    exec_parser.add_argument("--dry-run", action="store_true", help="Use the currently opened PSD without copying")
    exec_parser.add_argument("--wait", action="store_true", help="Poll until execution reaches a terminal state")
    exec_parser.add_argument("--poll-interval", type=float, default=2.0, help="Polling interval in seconds")

    state_parser = subparsers.add_parser("execution", help="Show execution state for a ticket")
    state_parser.add_argument("ticket_id", help="Ticket id")

    cancel_parser = subparsers.add_parser("cancel", help="Cancel a running ticket execution")
    cancel_parser.add_argument("ticket_id", help="Ticket id")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    if args.command == "status":
        print(json.dumps(get_photoshop_status(), ensure_ascii=False, indent=2))
        return

    if args.command == "tickets":
        print(json.dumps(list_photoshop_tickets(), ensure_ascii=False, indent=2))
        return

    if args.command == "scan":
        result = scan_photoshop_document(
            psd_path=args.psd_path,
            languages=args.languages,
            timeout_sec=args.timeout_sec,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not result.get("ok"):
            raise SystemExit(1)
        return

    if args.command == "show":
        print(json.dumps(get_photoshop_ticket(args.ticket_id), ensure_ascii=False, indent=2))
        return

    if args.command == "execute":
        result = start_ticket_execution(
            args.ticket_id,
            dry_run=args.dry_run,
            job_id=f"cli_{args.ticket_id}",
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not result.get("ok"):
            raise SystemExit(1)
        if not args.wait:
            return
        while True:
            state = get_execution_state(args.ticket_id)
            print(json.dumps({"ok": True, "state": state}, ensure_ascii=False, indent=2))
            if not state or state.get("status") in {"done", "error", "cancelled"}:
                if state and state.get("status") != "done":
                    raise SystemExit(1)
                return
            time.sleep(max(args.poll_interval, 0.5))

    if args.command == "execution":
        state = get_execution_state(args.ticket_id)
        if not state:
            print(
                json.dumps(
                    {"ok": False, "error": f"Execution not found for ticket {args.ticket_id}"},
                    ensure_ascii=False,
                    indent=2,
                )
            )
            raise SystemExit(1)
        print(json.dumps({"ok": True, "state": state}, ensure_ascii=False, indent=2))
        return

    if args.command == "cancel":
        print(json.dumps({"ok": True, "state": cancel_execution(args.ticket_id)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
