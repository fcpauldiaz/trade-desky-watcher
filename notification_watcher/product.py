import os
import sys
from pathlib import Path

from notification_watcher.version import __version__

APP_NAME = "Trade Desky Watcher"
APP_NAME_COMPACT = "TradeDeskyWatcher"
COMPANY_NAME = "Chapi Labs"
COPYRIGHT = "Copyright © 2026 Chapi Labs"
LEGACY_APP_NAME = "Notification Watcher"
LEGACY_APP_NAME_COMPACT = "NotificationWatcher"
HTTP_USER_AGENT = f"{APP_NAME_COMPACT}/{__version__}"

DOWNLOAD_BASE_URL = os.environ.get("TRADE_DOWNLOAD_BASE_URL", "https://tradedesky.chapilabs.com").rstrip("/")
DOWNLOAD_PAGE_URL = f"{DOWNLOAD_BASE_URL}/download"
DESKTOP_ASSETS_URL = f"{DOWNLOAD_BASE_URL}/desktop"
APPCAST_URL = f"{DESKTOP_ASSETS_URL}/appcast.xml"
GITHUB_REPO = "fcpauldiaz/trade-desky-watcher"
DESKTOP_CACHE_PURGE_PATHS = (
    "/desktop/TradeDeskyWatcher.dmg",
    "/desktop/TradeDeskyWatcher-setup.exe",
    "/desktop/TradeDeskyWatcher-win.zip",
    "/desktop/appcast.xml",
)

PRODUCTION_PLATFORM_URL = "https://tradedesky.chapilabs.com"
PRODUCTION_INGEST_URL = "https://trade-receiver.chapilabs.com/v1/ingest"
DEFAULT_PLATFORM_URL = os.environ.get("TRADE_PLATFORM_URL", PRODUCTION_PLATFORM_URL).rstrip("/")
DEFAULT_INGEST_URL = os.environ.get("TRADE_INGEST_URL", PRODUCTION_INGEST_URL).rstrip("/")

BUNDLE_ID = "com.chapilabs.tradedesky.watcher"
LEGACY_BUNDLE_ID = "com.notificationwatcher.app"

# Ed25519 public key for Sparkle 2 and WinSparkle (base64, 32 bytes).
SPARKLE_ED_PUBLIC_KEY = "p0zov5LiRiWRrOgkdUkVuPhw6w+RwC415epJzD3hzRc="

SPARKLE_VERSION = "2.9.5"
WINSPARKLE_VERSION = "0.9.4"


def is_loopback_url(url: str) -> bool:
    lowered = url.lower()
    return "localhost" in lowered or "127.0.0.1" in lowered


def resolved_service_url(saved: object, default: str) -> str:
    if isinstance(saved, str) and saved.strip():
        candidate = saved.strip().rstrip("/")
        if is_loopback_url(candidate) and not is_loopback_url(default):
            return default
        return candidate
    return default.rstrip("/")


def desktop_cache_purge_urls(base: str | None = None) -> list[str]:
    root = (base or DOWNLOAD_BASE_URL).rstrip("/")
    return [f"{root}{path}" for path in DESKTOP_CACHE_PURGE_PATHS]


def macos_bundle_plist(version: str) -> dict[str, object]:
    return {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleIdentifier": BUNDLE_ID,
        "CFBundleVersion": version,
        "CFBundleShortVersionString": version,
        "LSUIElement": True,
        "NSHighResolutionCapable": True,
        "NSHumanReadableCopyright": COPYRIGHT,
        "CFBundleGetInfoString": f"{APP_NAME} {version}, {COPYRIGHT}",
    }


def windows_file_version_tuple(version: str) -> tuple[int, int, int, int]:
    nums = [int(part) for part in version.split(".")]
    while len(nums) < 4:
        nums.append(0)
    return (nums[0], nums[1], nums[2], nums[3])


def windows_version_info_text(version: str) -> str:
    tup = windows_file_version_tuple(version)
    return f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={tup},
    prodvers={tup},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'{COMPANY_NAME}'),
        StringStruct(u'FileDescription', u'{APP_NAME}'),
        StringStruct(u'FileVersion', u'{version}'),
        StringStruct(u'InternalName', u'{APP_NAME_COMPACT}'),
        StringStruct(u'LegalCopyright', u'{COPYRIGHT}'),
        StringStruct(u'OriginalFilename', u'{APP_NAME_COMPACT}.exe'),
        StringStruct(u'ProductName', u'{APP_NAME}'),
        StringStruct(u'ProductVersion', u'{version}')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""


def apply_macos_app_identity(icon_path: Path | None, version: str) -> None:
    if sys.platform != "darwin":
        return
    try:
        from AppKit import NSApplication, NSImage
        from Foundation import NSBundle
    except ImportError:
        return
    info = NSBundle.mainBundle().infoDictionary()
    if info is not None:
        info.update(macos_bundle_plist(version))
    if icon_path is None or not icon_path.exists():
        return
    image = NSImage.alloc().initByReferencingFile_(str(icon_path))
    if image is not None and image.size().width > 0:
        NSApplication.sharedApplication().setApplicationIconImage_(image)
