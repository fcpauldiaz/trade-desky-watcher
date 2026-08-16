import os

APP_NAME = "Trade Desky Watcher"
APP_NAME_COMPACT = "TradeDeskyWatcher"
LEGACY_APP_NAME = "Notification Watcher"
LEGACY_APP_NAME_COMPACT = "NotificationWatcher"

GITHUB_REPO = "fcpauldiaz/trade-desky-watcher"
RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases"
APPCAST_URL = f"{RELEASES_URL}/latest/download/appcast.xml"

BUNDLE_ID = "com.chapilabs.tradedesky.watcher"
LEGACY_BUNDLE_ID = "com.notificationwatcher.app"

DEFAULT_PLATFORM_URL = os.environ.get("TRADE_PLATFORM_URL", "http://localhost:3000")
DEFAULT_INGEST_URL = os.environ.get("TRADE_INGEST_URL", "http://localhost:8000/v1/ingest")
