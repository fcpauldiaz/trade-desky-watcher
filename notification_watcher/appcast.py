from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

from notification_watcher.product import APP_NAME, DOWNLOAD_PAGE_URL

SPARKLE_NS = "http://www.andymatuschak.org/xml-namespaces/sparkle"
DC_NS = "http://purl.org/dc/elements/1.1/"


@dataclass(frozen=True)
class AppcastEnclosure:
    os_name: str
    url: str
    length: int
    ed_signature: str | None = None


def build_appcast(
    *,
    version: str,
    enclosures: list[AppcastEnclosure],
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
    ET.SubElement(channel, "link").text = DOWNLOAD_PAGE_URL
    ET.SubElement(channel, "description").text = f"{APP_NAME} updates"
    ET.SubElement(channel, "language").text = "en"

    notes = DOWNLOAD_PAGE_URL
    for enclosure in enclosures:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = f"Version {version} ({enclosure.os_name})"
        ET.SubElement(item, f"{{{SPARKLE_NS}}}releaseNotesLink").text = notes
        ET.SubElement(item, "pubDate").text = pub_str
        attrs = {
            f"{{{SPARKLE_NS}}}version": version,
            f"{{{SPARKLE_NS}}}shortVersionString": version,
            f"{{{SPARKLE_NS}}}os": enclosure.os_name,
            "url": enclosure.url,
            "length": str(enclosure.length),
            "type": "application/octet-stream",
        }
        if enclosure.ed_signature:
            attrs[f"{{{SPARKLE_NS}}}edSignature"] = enclosure.ed_signature
        ET.SubElement(item, "enclosure", attrs)

    return '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(rss, encoding="unicode")
