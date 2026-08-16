#!/usr/bin/env bash
# Import a Developer ID .p12 into a temporary keychain for GitHub Actions.
set -euo pipefail

: "${MACOS_CERTIFICATE_P12_BASE64:?MACOS_CERTIFICATE_P12_BASE64 is required}"
: "${MACOS_CERTIFICATE_PASSWORD:?MACOS_CERTIFICATE_PASSWORD is required}"

TMP="${RUNNER_TEMP:-${TMPDIR:-/tmp}}"
CERT_PATH="${TMP}/developer_id.p12"
KEYCHAIN="${TMP}/trade-desky-signing.keychain-db"
KEYCHAIN_PASSWORD="$(openssl rand -base64 32)"

CERT_PATH="${CERT_PATH}" python3 - <<'PY'
import base64, os, pathlib
raw = os.environ["MACOS_CERTIFICATE_P12_BASE64"].strip()
pathlib.Path(os.environ["CERT_PATH"]).write_bytes(base64.b64decode(raw))
PY

security delete-keychain "${KEYCHAIN}" >/dev/null 2>&1 || true
security create-keychain -p "${KEYCHAIN_PASSWORD}" "${KEYCHAIN}"
security set-keychain-settings -lut 21600 "${KEYCHAIN}"
security unlock-keychain -p "${KEYCHAIN_PASSWORD}" "${KEYCHAIN}"

security import "${CERT_PATH}" \
  -k "${KEYCHAIN}" \
  -P "${MACOS_CERTIFICATE_PASSWORD}" \
  -T /usr/bin/codesign \
  -T /usr/bin/security \
  -T /usr/bin/productbuild

EXISTING="$(security list-keychains -d user | sed 's/"//g')"
# shellcheck disable=SC2086
security list-keychains -d user -s "${KEYCHAIN}" ${EXISTING}

security set-key-partition-list \
  -S apple-tool:,apple:,codesign: \
  -s \
  -k "${KEYCHAIN_PASSWORD}" \
  "${KEYCHAIN}" >/dev/null

CA="${TMP}/DeveloperIDG2CA.cer"
curl -fsSL -o "${CA}" "https://www.apple.com/certificateauthority/DeveloperIDG2CA.cer"
security import "${CA}" -k "${KEYCHAIN}" -T /usr/bin/codesign || true

echo "Codesigning identities:"
security find-identity -v -p codesigning

rm -f "${CERT_PATH}"
