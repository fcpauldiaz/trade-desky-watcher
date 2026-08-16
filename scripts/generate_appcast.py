#!/usr/bin/env python3
"""Generate a Sparkle/WinSparkle appcast.xml for GitHub Release assets."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from notification_watcher.appcast import AppcastEnclosure, build_appcast


def _enclosure_from_file(*, os_name: str, url: str, path: Path, sign: bool) -> AppcastEnclosure:
    signature = None
    if sign:
        from notification_watcher.sparkle_sign import sign_file

        signature = sign_file(path)
    return AppcastEnclosure(
        os_name=os_name,
        url=url,
        length=path.stat().st_size,
        ed_signature=signature,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", default="appcast.xml")
    parser.add_argument("--version", required=True)
    parser.add_argument("--dmg", type=Path)
    parser.add_argument("--dmg-url")
    parser.add_argument("--win-setup", type=Path)
    parser.add_argument("--win-setup-url")
    parser.add_argument("--sign", action="store_true")
    args = parser.parse_args()

    enclosures: list[AppcastEnclosure] = []
    if args.dmg:
        if not args.dmg_url:
            parser.error("--dmg-url is required with --dmg")
        enclosures.append(
            _enclosure_from_file(os_name="macos", url=args.dmg_url, path=args.dmg, sign=args.sign)
        )
    if args.win_setup:
        if not args.win_setup_url:
            parser.error("--win-setup-url is required with --win-setup")
        enclosures.append(
            _enclosure_from_file(
                os_name="windows",
                url=args.win_setup_url,
                path=args.win_setup,
                sign=args.sign,
            )
        )
    if not enclosures:
        parser.error("Pass --dmg and/or --win-setup")

    xml = build_appcast(version=args.version, enclosures=enclosures)
    Path(args.output).write_text(xml, encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
