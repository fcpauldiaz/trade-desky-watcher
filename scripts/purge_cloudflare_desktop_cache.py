#!/usr/bin/env python3
"""Purge Cloudflare cache for stable Trade Desky desktop download URLs."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from notification_watcher.product import (
    HTTP_USER_AGENT,
    LEGACY_DOWNLOAD_BASE_URL,
    DOWNLOAD_BASE_URL,
    desktop_cache_purge_urls,
)

API_URL = "https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache"


def purge_urls(zone_id: str, token: str, urls: list[str]) -> dict[str, object]:
    request = Request(
        API_URL.format(zone_id=zone_id),
        data=json.dumps({"files": urls}).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": HTTP_USER_AGENT,
        },
    )
    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not payload.get("success"):
        raise SystemExit(f"Cloudflare purge failed: {payload}")
    return payload


def main() -> int:
    zone_id = os.environ.get("CLOUDFLARE_ZONE_ID", "").strip()
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    if not zone_id or not token:
        raise SystemExit("CLOUDFLARE_ZONE_ID and CLOUDFLARE_API_TOKEN are required")
    purged: list[str] = []
    legacy = desktop_cache_purge_urls(LEGACY_DOWNLOAD_BASE_URL)
    purged.extend(legacy)
    result = purge_urls(zone_id, token, legacy)
    site_zone_id = os.environ.get("CLOUDFLARE_SITE_ZONE_ID", "").strip()
    site_result: dict[str, object] | None = None
    current = desktop_cache_purge_urls(DOWNLOAD_BASE_URL)
    if site_zone_id:
        site_result = purge_urls(site_zone_id, token, current)
        purged.extend(current)
    print(json.dumps({"purged": purged, "result": result.get("result"), "site": None if site_result is None else site_result.get("result")}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except HTTPError as exc:
        raise SystemExit(f"Cloudflare purge failed: {exc.code} {exc.read().decode('utf-8', errors='replace')}") from exc
    except URLError as exc:
        raise SystemExit(f"Cloudflare purge failed: {exc}") from exc
