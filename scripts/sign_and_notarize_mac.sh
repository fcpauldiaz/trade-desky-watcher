#!/usr/bin/env bash
# Sign and notarize the macOS app locally. Requires Apple Developer credentials.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "${SCRIPT_DIR}"
APP_NAME="$(python3 -c "from notification_watcher.product import APP_NAME; print(APP_NAME)")"
APP_PATH="${SCRIPT_DIR}/dist/${APP_NAME}.app"
SIGN_IDENTITY="${SIGN_IDENTITY:-Developer ID Application}"
NOTARY_PROFILE="${NOTARY_PROFILE:-AC_NOTARY}"

if [[ ! -d "${APP_PATH}" ]]; then
  echo "Build first: python3 setup.py py2app"
  exit 1
fi

if [[ -z "${SIGN_IDENTITY}" ]]; then
  echo "Set SIGN_IDENTITY to your Developer ID Application certificate name."
  exit 1
fi

echo "Signing ${APP_PATH}..."
codesign --force --deep --options runtime --sign "${SIGN_IDENTITY}" "${APP_PATH}"
codesign --verify --verbose "${APP_PATH}"

echo "Creating zip for notarization..."
ZIP_PATH="${SCRIPT_DIR}/dist/${APP_NAME}.zip"
ditto -c -k --keepParent "${APP_PATH}" "${ZIP_PATH}"

echo "Submitting for notarization (profile: ${NOTARY_PROFILE})..."
xcrun notarytool submit "${ZIP_PATH}" --keychain-profile "${NOTARY_PROFILE}" --wait

echo "Stapling ticket..."
xcrun stapler staple "${APP_PATH}"

echo "Rebuilding DMG..."
chmod +x "${SCRIPT_DIR}/create_dmg.sh"
"${SCRIPT_DIR}/create_dmg.sh"

echo "Done. Signed and notarized app ready in dist/"
