import base64
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat

from notification_watcher.appcast import SPARKLE_NS, AppcastEnclosure, build_appcast
from notification_watcher.native_update import NativeUpdater
from notification_watcher.product import SPARKLE_ED_PUBLIC_KEY
from notification_watcher.sparkle_sign import sign_file, verify_file


def test_build_appcast_includes_macos_and_windows_enclosures():
    xml = build_appcast(
        version="1.4.0",
        enclosures=[
            AppcastEnclosure(
                os_name="macos",
                url="https://example.com/app.dmg",
                length=123,
                ed_signature="sig-mac",
            ),
            AppcastEnclosure(
                os_name="windows",
                url="https://example.com/app-setup.exe",
                length=456,
                ed_signature="sig-win",
            ),
        ],
        published_at="2026-08-15T12:00:00Z",
    )
    root = ET.fromstring(xml)
    items = root.findall("./channel/item")
    assert len(items) == 2
    os_values = [item.find("enclosure").attrib[f"{{{SPARKLE_NS}}}os"] for item in items]
    assert os_values == ["macos", "windows"]
    signatures = [item.find("enclosure").attrib[f"{{{SPARKLE_NS}}}edSignature"] for item in items]
    assert signatures == ["sig-mac", "sig-win"]
    assert "sparkle:os" in xml
    assert "sparkle:edSignature" in xml


def test_unsigned_enclosure_omits_ed_signature():
    xml = build_appcast(
        version="1.4.0",
        enclosures=[
            AppcastEnclosure(os_name="macos", url="https://example.com/app.dmg", length=1),
        ],
    )
    root = ET.fromstring(xml)
    attrib = root.find("./channel/item/enclosure").attrib
    assert f"{{{SPARKLE_NS}}}edSignature" not in attrib


def test_sign_and_verify_file(tmp_path: Path, monkeypatch):
    key = Ed25519PrivateKey.generate()
    seed = key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    public_b64 = base64.b64encode(
        key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    ).decode("ascii")
    payload = tmp_path / "update.bin"
    payload.write_bytes(b"trade-desky-watcher-update")
    monkeypatch.setenv("SPARKLE_ED_PRIVATE_KEY", base64.b64encode(seed).decode("ascii"))
    signature = sign_file(payload)
    verify_file(payload, signature, public_b64)


def test_sign_file_requires_private_key(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("SPARKLE_ED_PRIVATE_KEY", raising=False)
    payload = tmp_path / "update.bin"
    payload.write_bytes(b"x")
    with pytest.raises(RuntimeError, match="SPARKLE_ED_PRIVATE_KEY"):
        sign_file(payload)


def test_sparkle_public_key_is_32_bytes():
    assert len(base64.b64decode(SPARKLE_ED_PUBLIC_KEY)) == 32


def test_native_updater_unavailable_without_framework():
    updater = NativeUpdater()
    if updater.available:
        pytest.skip("Native updater library is present")
    assert updater.start(automatic=True) is False
    assert updater.check_now() is False
