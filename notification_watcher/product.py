import os

APP_NAME = "Trade Desky Watcher"
APP_NAME_COMPACT = "TradeDeskyWatcher"
COMPANY_NAME = "Chapi Labs"
LEGACY_APP_NAME = "Notification Watcher"
LEGACY_APP_NAME_COMPACT = "NotificationWatcher"

GITHUB_REPO = "fcpauldiaz/trade-desky-watcher"
RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases"
APPCAST_URL = f"{RELEASES_URL}/latest/download/appcast.xml"

BUNDLE_ID = "com.chapilabs.tradedesky.watcher"
LEGACY_BUNDLE_ID = "com.notificationwatcher.app"

# Ed25519 public key for Sparkle 2 and WinSparkle (base64, 32 bytes).
SPARKLE_ED_PUBLIC_KEY = "p0zov5LiRiWRrOgkdUkVuPhw6w+RwC415epJzD3hzRc="

SPARKLE_VERSION = "2.9.5"
WINSPARKLE_VERSION = "0.9.4"

DEFAULT_PLATFORM_URL = os.environ.get("TRADE_PLATFORM_URL", "http://localhost:3000")
DEFAULT_INGEST_URL = os.environ.get("TRADE_INGEST_URL", "http://localhost:8000/v1/ingest")
