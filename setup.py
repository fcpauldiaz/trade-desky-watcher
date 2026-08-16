from setuptools import setup

from notification_watcher.product import APP_NAME, APPCAST_URL, BUNDLE_ID
from notification_watcher.version import __version__

APP = ["notification_app.py"]
DATA_FILES = [("assets", ["assets/icon.icns", "assets/icon.png"])]
OPTIONS = {
    "argv_emulation": False,
    "iconfile": "assets/icon.icns",
    "includes": ["notification_watcher", "ingest_sender"],
    "packages": ["rumps", "objc", "Foundation", "AppKit"],
    "plist": {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleIdentifier": BUNDLE_ID,
        "CFBundleVersion": __version__,
        "CFBundleShortVersionString": __version__,
        "LSUIElement": True,
        "NSHighResolutionCapable": True,
        "SUFeedURL": APPCAST_URL,
    },
}

setup(
    name=APP_NAME,
    version=__version__,
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
