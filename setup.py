from pathlib import Path

from setuptools import setup

from notification_watcher.product import APP_NAME, APPCAST_URL, BUNDLE_ID, SPARKLE_ED_PUBLIC_KEY
from notification_watcher.version import __version__

APP = ["notification_app.py"]
DATA_FILES = [("assets", ["assets/icon.icns", "assets/icon.png"])]
OPTIONS = {
    "argv_emulation": False,
    "iconfile": "assets/icon.icns",
    "includes": ["notification_watcher", "ingest_sender", "notification_watcher.native_update"],
    "packages": ["rumps", "objc", "Foundation", "AppKit"],
    "strip": False,
    "plist": {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleIdentifier": BUNDLE_ID,
        "CFBundleVersion": __version__,
        "CFBundleShortVersionString": __version__,
        "LSUIElement": True,
        "NSHighResolutionCapable": True,
        "SUFeedURL": APPCAST_URL,
        "SUPublicEDKey": SPARKLE_ED_PUBLIC_KEY,
        "SUEnableAutomaticChecks": True,
        "SUScheduledCheckInterval": 86400,
    },
}

sparkle = Path("vendor/Sparkle.framework")
if sparkle.is_dir():
    OPTIONS["frameworks"] = [str(sparkle)]

setup(
    name=APP_NAME,
    version=__version__,
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
