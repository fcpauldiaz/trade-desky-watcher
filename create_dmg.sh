#!/usr/bin/env bash
# Create a DMG for distributing Trade Desky Watcher. Run after: python3 setup.py py2app
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DIST_DIR="${SCRIPT_DIR}/dist"
APP_NAME="$(python3 -c "from notification_watcher.product import APP_NAME; print(APP_NAME)")"
APP_NAME_COMPACT="$(python3 -c "from notification_watcher.product import APP_NAME_COMPACT; print(APP_NAME_COMPACT)")"
VERSION="$(python3 -c "from notification_watcher.version import __version__; print(__version__)")"
DMG_NAME="${APP_NAME_COMPACT}-${VERSION}"
STAGING="${DIST_DIR}/dmg-staging"
DMG_PATH="${DIST_DIR}/${DMG_NAME}.dmg"

if [[ ! -d "${DIST_DIR}/${APP_NAME}.app" ]]; then
  echo "Run first: python3 setup.py py2app"
  exit 1
fi

rm -rf "${STAGING}"
mkdir -p "${STAGING}"
cp -R "${DIST_DIR}/${APP_NAME}.app" "${STAGING}/"
ln -s /Applications "${STAGING}/Applications"
rm -f "${DMG_PATH}"
hdiutil create -volname "${APP_NAME}" -srcfolder "${STAGING}" -ov -format UDZO "${DMG_PATH}"
rm -rf "${STAGING}"
echo "Created ${DMG_PATH}"
