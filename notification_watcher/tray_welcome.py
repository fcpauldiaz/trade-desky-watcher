"""Copy and helpers for first-run system tray guidance on Windows."""

from notification_watcher.product import APP_NAME, BRAND_NAME

TRAY_WELCOME_TITLE = f"{BRAND_NAME} — {APP_NAME}"

TRAY_WELCOME_DIALOG = (
    f"{APP_NAME} is part of {BRAND_NAME} and runs in the background.\n\n"
    f"Look for the {BRAND_NAME} icon in the notification area "
    "(bottom-right of the taskbar): ink tile with a lime green arrow. "
    "If you do not see it, click the ^ chevron to show hidden icons.\n\n"
    f"Right-click the icon → Account → Sign in… with your {BRAND_NAME} "
    "email and password."
)

TRAY_WELCOME_BALLOON = (
    f"{BRAND_NAME}: look for the lime arrow icon in the notification area. "
    "Right-click → Account → Sign in…"
)
