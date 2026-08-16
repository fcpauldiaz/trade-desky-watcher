#!/usr/bin/env bash
# Sign and notarize the macOS app locally. Requires Apple Developer credentials.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "${SCRIPT_DIR}"
APP_NAME="$(python3 -c "from notification_watcher.product import APP_NAME; print(APP_NAME)")"
APP_PATH="${SCRIPT_DIR}/dist/${APP_NAME}.app"
SIGN_IDENTITY="${SIGN_IDENTITY:-Developer ID Application: Pablo Diaz (GGGP7AV2E7)}"
NOTARY_PROFILE="${NOTARY_PROFILE:-AC_NOTARY}"
REQUIRE_SIGNING="${REQUIRE_SIGNING:-0}"

if [[ ! -d "${APP_PATH}" ]]; then
  echo "Build first: python3 setup.py py2app"
  exit 1
fi

if [[ "${REQUIRE_SIGNING}" == "1" ]]; then
  if ! security find-identity -v -p codesigning | grep -F "${SIGN_IDENTITY}" >/dev/null; then
    echo "Required signing identity not found: ${SIGN_IDENTITY}"
    security find-identity -v -p codesigning || true
    exit 1
  fi
fi

sign() {
  codesign --force --options runtime --timestamp --sign "${SIGN_IDENTITY}" "$@"
}

notary_submit() {
  local artifact="$1"
  if [[ -n "${APPLE_API_KEY_FILE:-}" ]]; then
    : "${APPLE_API_KEY_ID:?APPLE_API_KEY_ID is required}"
    : "${APPLE_API_ISSUER:?APPLE_API_ISSUER is required}"
    xcrun notarytool submit "${artifact}" --key "${APPLE_API_KEY_FILE}" --key-id "${APPLE_API_KEY_ID}" --issuer "${APPLE_API_ISSUER}" --wait
  elif [[ -n "${APPLE_API_KEY:-}" ]]; then
    : "${APPLE_API_KEY_ID:?APPLE_API_KEY_ID is required}"
    : "${APPLE_API_ISSUER:?APPLE_API_ISSUER is required}"
    local key_file
    key_file="$(mktemp)"
    printf '%s\n' "${APPLE_API_KEY}" > "${key_file}"
    chmod 600 "${key_file}"
    xcrun notarytool submit "${artifact}" --key "${key_file}" --key-id "${APPLE_API_KEY_ID}" --issuer "${APPLE_API_ISSUER}" --wait
    rm -f "${key_file}"
  else
    xcrun notarytool submit "${artifact}" --keychain-profile "${NOTARY_PROFILE}" --wait
  fi
}

echo "Signing nested binaries in ${APP_PATH}..."

SPARKLE="${APP_PATH}/Contents/Frameworks/Sparkle.framework"
if [[ -d "${SPARKLE}/Versions/B" ]]; then
  python3 - "${SPARKLE}" <<'PY'
from pathlib import Path
import shutil
import sys

root = Path(sys.argv[1])
version_b = root / "Versions" / "B"
current = root / "Versions" / "Current"
if version_b.is_dir() and current.exists() and not current.is_symlink():
    shutil.rmtree(current)
    current.symlink_to("B")
for name in (
    "Sparkle",
    "Resources",
    "Headers",
    "Modules",
    "PrivateHeaders",
    "Updater.app",
    "XPCServices",
    "Autoupdate",
):
    dest = root / name
    source = version_b / name
    if not source.exists():
        continue
    if dest.is_symlink():
        continue
    if dest.exists():
        if dest.is_dir() and not dest.is_symlink():
            shutil.rmtree(dest)
        else:
            dest.unlink()
    dest.symlink_to(Path("Versions/Current") / name)
PY

  shopt -s nullglob
  for xpc in "${SPARKLE}/Versions/B/XPCServices/"*.xpc; do
    sign "${xpc}"
  done
  sign "${SPARKLE}/Versions/B/Autoupdate"
  sign "${SPARKLE}/Versions/B/Updater.app"
  sign "${SPARKLE}"
  shopt -u nullglob
fi

PYTHON_FW="${APP_PATH}/Contents/Frameworks/Python.framework"
if [[ -d "${PYTHON_FW}" ]]; then
  find "${PYTHON_FW}" \( -name '*.dylib' -o -name '*.so' -o -perm -111 -type f \) ! -name '*.pyc' -print0 |
    while IFS= read -r -d '' bin; do
      if file "${bin}" | grep -q 'Mach-O'; then
        sign "${bin}" || true
      fi
    done
  sign "${PYTHON_FW}"
fi

find "${APP_PATH}/Contents/Frameworks" -name '*.dylib' -type f -print0 |
  while IFS= read -r -d '' dylib; do
    sign "${dylib}"
  done

find "${APP_PATH}/Contents" \( -name '*.so' -o -name '*.dylib' \) -type f -print0 |
  while IFS= read -r -d '' bin; do
    sign "${bin}" || true
  done

if [[ -f "${APP_PATH}/Contents/MacOS/python" ]]; then
  sign "${APP_PATH}/Contents/MacOS/python"
fi
sign "${APP_PATH}"

codesign --verify --verbose=2 "${APP_PATH}"
SIGN_INFO="$(codesign --display --verbose=2 "${APP_PATH}" 2>&1)"
echo "${SIGN_INFO}"
if ! echo "${SIGN_INFO}" | grep -q "Developer ID Application"; then
  echo "App is not signed with Developer ID Application"
  exit 1
fi

echo "Creating zip for notarization..."
ZIP_PATH="${SCRIPT_DIR}/dist/${APP_NAME}.zip"
rm -f "${ZIP_PATH}"
ditto -c -k --keepParent "${APP_PATH}" "${ZIP_PATH}"

echo "Submitting app zip for notarization..."
notary_submit "${ZIP_PATH}"

echo "Stapling ticket..."
xcrun stapler staple "${APP_PATH}"

echo "Rebuilding DMG..."
chmod +x "${SCRIPT_DIR}/create_dmg.sh"
"${SCRIPT_DIR}/create_dmg.sh"

APP_NAME_COMPACT="$(python3 -c "from notification_watcher.product import APP_NAME_COMPACT; print(APP_NAME_COMPACT)")"
VERSION="$(python3 -c "from notification_watcher.version import __version__; print(__version__)")"
DMG_PATH="${SCRIPT_DIR}/dist/${APP_NAME_COMPACT}-${VERSION}.dmg"
if [[ -f "${DMG_PATH}" ]]; then
  echo "Notarizing DMG..."
  notary_submit "${DMG_PATH}"
  xcrun stapler staple "${DMG_PATH}"
  xcrun stapler validate "${DMG_PATH}"
fi

echo "Done. Signed and notarized app ready in dist/"
