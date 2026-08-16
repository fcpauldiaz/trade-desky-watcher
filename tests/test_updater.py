from notification_watcher.updater import (
    ReleaseInfo,
    _MAC_DMG_LEGACY_RE,
    _MAC_DMG_RE,
    is_newer_version,
    parse_version,
    _pick_asset,
)


def test_parse_version():
    assert parse_version("1.2.3") == (1, 2, 3)
    assert parse_version("v2.0.1") == (2, 0, 1)
    assert parse_version("bad") is None


def test_is_newer_version():
    assert is_newer_version("1.2.0", "1.1.0") is True
    assert is_newer_version("1.1.0", "1.1.0") is False
    assert is_newer_version("1.0.9", "1.1.0") is False
    assert is_newer_version("2.0.0", "1.9.9") is True


def test_release_info_frozen():
    info = ReleaseInfo(
        version="1.2.0",
        tag="v1.2.0",
        download_url="https://example.com/app.dmg",
        asset_name="TradeDeskyWatcher-1.3.0.dmg",
        release_notes="Fixes",
    )
    assert info.version == "1.2.0"


def test_pick_asset_prefers_new_brand_name():
    assets = [
        {"name": "NotificationWatcher-1.2.0.dmg", "browser_download_url": "https://example.com/legacy.dmg"},
        {"name": "TradeDeskyWatcher-1.3.0.dmg", "browser_download_url": "https://example.com/new.dmg"},
    ]
    assert _pick_asset(assets, _MAC_DMG_RE)["name"] == "TradeDeskyWatcher-1.3.0.dmg"
    assert _pick_asset(assets, _MAC_DMG_LEGACY_RE)["name"] == "NotificationWatcher-1.2.0.dmg"
