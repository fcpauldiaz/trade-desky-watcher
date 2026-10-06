from pathlib import Path

from notification_watcher.product import (
    APP_NAME,
    COMPANY_NAME,
    COPYRIGHT,
    macos_bundle_plist,
    windows_file_version_tuple,
    windows_version_info_text,
)
from scripts.generate_icons import SOURCE_NAME, load_source, write_icons


def test_macos_bundle_plist_includes_copyright():
    plist = macos_bundle_plist("1.4.1")
    assert plist["NSHumanReadableCopyright"] == COPYRIGHT
    assert COMPANY_NAME in COPYRIGHT
    assert "not specified" not in str(plist["NSHumanReadableCopyright"]).lower()
    assert plist["CFBundleName"] == APP_NAME
    assert "1.4.1" in str(plist["CFBundleGetInfoString"])


def test_windows_version_info_includes_copyright():
    assert windows_file_version_tuple("1.4.1") == (1, 4, 1, 0)
    text = windows_version_info_text("1.4.1")
    assert COMPANY_NAME in text
    assert COPYRIGHT in text
    assert APP_NAME in text


def test_write_icons_from_trade_desky_mark(tmp_path: Path):
    png_path, ico_path = write_icons(tmp_path)
    assert png_path.is_file()
    assert ico_path.is_file()
    image = load_source(tmp_path)
    assert image.size == (1024, 1024)
    ink = image.getpixel((120, 120))
    assert ink[:3] == (17, 17, 17)
    lime = image.getpixel((512, 420))
    assert lime[1] > 150 and lime[0] < 80
