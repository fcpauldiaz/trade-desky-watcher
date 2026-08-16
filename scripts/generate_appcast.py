#!/usr/bin/env python3
"""Generate Sparkle appcast.xml for GitHub Release assets."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from notification_watcher.product import APP_NAME, GITHUB_REPO
from notification_watcher.updater import USER_AGENT, _MAC_DMG_RE, _MAC_DMG_LEGACY_RE, _pick_asset

SPARKLE_NS = "http://www.andymatuschak.org/xml-namespaces/sparkle"
DC_NS = "http://purl.org/dc/elements/1.1/"


def _github_latest() -> dict:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
        headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def build_appcast(
    *,
    version: str,
    dmg_url: str,
    dmg_size: int,
    published_at: str | None = None,
) -> str:
    pub_dt = (
        datetime.fromisoformat(published_at.replace("Z", "+00:00")).astimezone(timezone.utc)
        if published_at
        else datetime.now(timezone.utc)
    )
    pub_str = pub_dt.strftime("%a, %d %b %Y %H:%M:%S +0000")

    ET.register_namespace("sparkle", SPARKLE_NS)
    ET.register_namespace("dc", DC_NS)
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = APP_NAME
    ET.SubElement(channel, "link").text = f"https://github.com/{GITHUB_REPO}/releases/latest"
    ET.SubElement(channel, "description").text = f"{APP_NAME} updates"
    ET.SubElement(channel, "language").text = "en"

    item = ET.SubElement(channel, "item")
    ET.SubElement(item, "title").text = f"Version {version}"
    ET.SubElement(item, f"{{{SPARKLE_NS}}}releaseNotesLink").text = (
        f"https://github.com/{GITHUB_REPO}/releases/tag/v{version}"
    )
    ET.SubElement(item, "pubDate").text = pub_str
    ET.SubElement(
        item,
        "enclosure",
        {
            f"{{{SPARKLE_NS}}}version": version,
            f"{{{SPARKLE_NS}}}shortVersionString": version,
            "url": dmg_url,
            "length": str(dmg_size),
            "type": "application/octet-stream",
        },
    )

    return '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(rss, encoding="unicode")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", default="appcast.xml")
    parser.add_argument("--version", help="Release version (offline mode)")
    parser.add_argument("--dmg-url", help="DMG download URL (offline mode)")
    parser.add_argument("--dmg-size", type=int, default=0, help="DMG size in bytes (offline mode)")
    args = parser.parse_args()

    if args.version and args.dmg_url:
        xml = build_appcast(version=args.version, dmg_url=args.dmg_url, dmg_size=args.dmg_size)
    else:
        release = _github_latest()
        assets = release.get("assets", [])
        if not isinstance(assets, list):
            assets = []
        asset = _pick_asset(assets, _MAC_DMG_RE) or _pick_asset(assets, _MAC_DMG_LEGACY_RE)
        if asset is None:
            raise RuntimeError("Latest release has no macOS DMG asset")
        xml = build_appcast(
            version=str(release.get("tag_name", "")).lstrip("vV"),
            dmg_url=str(asset["browser_download_url"]),
            dmg_size=int(asset.get("size", 0)),
            published_at=str(release.get("published_at") or ""),
        )

    with open(args.output, "w", encoding="utf-8") as handle:
        handle.write(xml)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
