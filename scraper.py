#!/usr/bin/env python3
"""
CLI for watching OS notifications. Uses notification_watcher package for core logic.
"""
import argparse
import sys
from pathlib import Path

import ingest_sender
from notification_watcher.config import load_config
from notification_watcher.platform import get_backend
from notification_watcher.watcher import watch


def print_notification(
    app_id: str,
    title: str,
    subtitle: str,
    body: str,
    delivered_date,
    backend,
) -> None:
    print("=" * 50)
    print(f"App:       {app_id}")
    print(f"Time:      {backend.format_delivered_date(delivered_date)}")
    print(f"Title:     {title}")
    print(f"Subtitle:  {subtitle}")
    print(f"Body:      {body}")
    print("=" * 50)


def run_once(db_path: Path, app_filter: str | None, backend) -> None:
    count = 0
    for app_id, title, subtitle, body, _presented, delivered_date in backend.iter_notifications(
        db_path, app_filter
    ):
        print_notification(app_id, title, subtitle, body, delivered_date, backend)
        count += 1
    if count == 0:
        print("No notifications found.")


def run_watch(
    db_path: Path,
    poll_seconds: float,
    app_filter: str | None,
    no_ingest: bool,
    backend,
) -> None:
    config = load_config()
    print("Watching for new notifications... (Ctrl+C to stop)\n")

    def on_notification(app_id: str, title: str, subtitle: str, body: str, delivered_date):
        print_notification(app_id, title, subtitle, body, delivered_date, backend)
        if not no_ingest:
            ingest_sender.send_notification(
                app_id, title, subtitle, body, delivered_date, config
            )

    try:
        watch(backend, db_path, poll_seconds, app_filter, on_notification)
    except KeyboardInterrupt:
        print("\nStopped.")


def main() -> None:
    backend = get_backend()
    config = load_config()
    parser = argparse.ArgumentParser(
        description="Watch OS notifications for new events (never-ending loop)."
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Print current notifications once and exit instead of watching.",
    )
    parser.add_argument(
        "--poll",
        type=float,
        default=None,
        metavar="SECONDS",
        help=f"Poll interval in seconds (default: {config.poll_seconds} from config).",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        metavar="PATH",
        help="Path to notification db (default: auto-detect).",
    )
    parser.add_argument(
        "--no-ingest",
        action="store_true",
        help="Do not forward notifications to the ingest endpoint.",
    )
    args = parser.parse_args()

    db_path = args.db or backend.get_notification_db_path()
    if not db_path:
        print("Could not resolve notification database path.")
        raise SystemExit(1)

    app_filter = config.effective_app_filter()

    poll_seconds = args.poll if args.poll is not None else config.poll_seconds

    try:
        if args.once:
            run_once(db_path, app_filter, backend)
        else:
            run_watch(db_path, poll_seconds, app_filter, args.no_ingest, backend)
    except FileNotFoundError as e:
        print(e)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
