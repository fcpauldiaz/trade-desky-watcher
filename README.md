# Trade Desky Watcher

Cross-platform utility that watches OS notifications and forwards them to Trade Desky when signed in.

| Platform | Supported versions | Data source |
|----------|-------------------|-------------|
| macOS | 13+ (Sequoia/Tahoe may need FDA) | Notification Center SQLite |
| Windows | 10, 11 | `%LOCALAPPDATA%\Microsoft\Windows\Notifications\wpndatabase.db` |

## Features

- Menu bar (macOS) or system tray (Windows) UI
- Recent notifications list with detail view
- Configurable poll interval: 10 ms, 50 ms, 100 ms, 500 ms, 1 s
- App filter (SQL LIKE) and Discord-only shortcut
- Account sign-in to Trade Desky (no manual URLs to configure)
- Forwards alerts to the platform ingest endpoint automatically
- Persistent settings, launch at login, local logs
- CLI (`scraper.py`) for scripting

## Quick start

### macOS (from source)

```bash
pip install -r requirements-app.txt
python3 scripts/generate_icons.py
python3 notification_app.py
```

Grant **Full Disk Access** to Terminal or Trade Desky Watcher in System Settings → Privacy & Security.

### Windows (from source)

```bash
pip install -r requirements-windows.txt
python scripts/generate_icons.py
python windows_app.py
```

### CLI (either platform)

```bash
python3 scraper.py                  # watch + forward to ingest
python3 scraper.py --once           # dump once
python3 scraper.py --discord-only
python3 scraper.py --poll 0.5
python3 scraper.py --no-ingest
```

Config file location:

- macOS: `~/Library/Application Support/Trade Desky Watcher/config.json`
- Windows: `%APPDATA%\Trade Desky Watcher\config.json`

Settings from the previous **Notification Watcher** folder are moved automatically on first launch.

## Build distributables

### macOS .app and DMG

```bash
pip install -r requirements-app.txt
python3 scripts/generate_icons.py
python3 scripts/fetch_update_frameworks.py --sparkle
python3 setup.py py2app
./create_dmg.sh
```

Output: `dist/Trade Desky Watcher.app`, `dist/TradeDeskyWatcher-1.4.0.dmg`

### Windows installer and portable zip

```bash
pip install -r requirements-windows.txt
python scripts/generate_icons.py
python scripts/fetch_update_frameworks.py --winsparkle
pyinstaller notification_watcher.spec
python scripts/build_windows_installer.py
```

Output:

- `dist/TradeDeskyWatcher/TradeDeskyWatcher.exe` (portable folder)
- `dist/TradeDeskyWatcher-1.4.0-setup.exe` (per-user NSIS installer used by auto-update)

`build_windows_installer.py` requires [NSIS](https://nsis.sourceforge.io/) (`choco install nsis`).

## CI artifacts

See [INSTALL.md](INSTALL.md) for end-user setup (macOS FDA, Windows, sign-in).

GitHub Actions runs tests on every push/PR. On pushes to `main`, it builds macOS and Windows artifacts, then publishes **public downloads** to [tradedesky.chapilabs.com/download](https://tradedesky.chapilabs.com/download) (Coolify-hosted, not GitHub Releases):

- `TradeDeskyWatcher.dmg` / versioned DMG (macOS)
- `TradeDeskyWatcher-setup.exe` / versioned setup (Windows)
- `appcast.xml` (Sparkle / WinSparkle feed, Ed25519-signed)

Bump `__version__` in `notification_watcher/version.py` before merging to `main` to publish a new release tag.

## Signing (CI)

macOS GitHub Actions builds **must** Developer ID-sign and notarize the app. The `build-mac` job fails if these secrets are missing:

| Secret | Purpose |
|--------|---------|
| `MACOS_CERTIFICATE_P12_BASE64` | Developer ID Application certificate as a base64-encoded `.p12` |
| `MACOS_CERTIFICATE_PASSWORD` | Password for that `.p12` |
| `MACOS_SIGN_IDENTITY` | Identity string, e.g. `Developer ID Application: Name (TEAMID)` |
| `APPLE_API_KEY` | App Store Connect API `.p8` private key contents |
| `APPLE_API_KEY_ID` | Key ID |
| `APPLE_API_ISSUER` | Issuer UUID |

Windows CI builds **must** Authenticode-sign with [Azure Artifact Signing](https://learn.microsoft.com/en-us/azure/artifact-signing/quickstart) (Trusted Signing) over GitHub OIDC. The `build-win` job fails if these secrets are missing:

| Secret | Purpose |
|--------|---------|
| `AZURE_CLIENT_ID` | App registration (application) ID |
| `AZURE_TENANT_ID` | Microsoft Entra tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID |
| `AZURE_TRUSTED_SIGNING_ENDPOINT` | Regional endpoint, e.g. `https://eus.codesigning.azure.net/` |
| `AZURE_TRUSTED_SIGNING_ACCOUNT` | Artifact Signing account name |
| `AZURE_CERT_PROFILE_NAME` | Certificate profile name (Public Trust) |

Azure portal setup (once):

1. Register the **Microsoft.CodeSigning** resource provider on the subscription.
2. Create an **Artifact Signing** account in a supported region (East US is `https://eus.codesigning.azure.net/`).
3. Assign yourself **Artifact Signing Identity Verifier** and create a **Public Trust** identity validation for Chapi Labs. This can take 1–20 business days.
4. After the identity is **Completed**, create a **Public Trust** certificate profile.
5. Create an App registration. Under **Certificates & secrets** → **Federated credentials**, add GitHub: org `fcpauldiaz`, repo `trade-desky-watcher`, entity **Branch**, branch `main`.
6. On the Artifact Signing account, grant that app **Artifact Signing Certificate Profile Signer**.

Local PFX signing is still `scripts/sign_windows.ps1` for machines that have a `.pfx`.

Local macOS signing (same script CI uses):

```bash
# macOS — Developer ID in the login keychain + notarytool profile, or APPLE_API_KEY*
SIGN_IDENTITY="Developer ID Application: Your Name (TEAMID)" ./scripts/sign_and_notarize_mac.sh
```

## Filtering

The watcher only captures **Discord** notifications.

## Troubleshooting

### macOS: no notifications

1. Confirm Full Disk Access is enabled for the app.
2. Check status in the menu: should say **Watching**.
3. Open logs via Account → View logs.

### Windows: no notifications

1. Confirm `wpndatabase.db` exists under `%LOCALAPPDATA%\Microsoft\Windows\Notifications\`.
2. Send a test toast; WAL mode may add slight delay.
3. Check `%APPDATA%\Trade Desky Watcher\notification_watcher.log`.

### Connection test fails

- Sign in via **Account → Sign in…** with your Trade Desky credentials.
- Confirm an active Pro subscription on the platform.
- Use **Account → Test connection** to verify.

## Uninstall

### macOS

1. Quit the app.
2. Delete `Trade Desky Watcher.app` from Applications.
3. Remove `~/Library/Application Support/Trade Desky Watcher/`.
4. Remove `~/Library/LaunchAgents/com.chapilabs.tradedesky.watcher.plist` if present.

### Windows

1. Quit the tray app.
2. Delete `%LOCALAPPDATA%\Programs\TradeDeskyWatcher` (or your portable folder).
3. Remove `%APPDATA%\Trade Desky Watcher\`.
4. Remove the `TradeDeskyWatcher` entry from Registry → `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` if present.

## Privacy

See [PRIVACY.md](PRIVACY.md). No telemetry.

## Auto-update

Bundled macOS and Windows builds use **Sparkle 2** and **WinSparkle** with a signed `appcast.xml` on this site (`https://tradedesky.chapilabs.com/desktop/appcast.xml`):

- **On startup** and **once per day** (native updater)
- **Manual check**: menu bar / tray → **Updates → Check for updates...**
- **macOS**: Sparkle downloads the DMG from the Trade Desky site and replaces the app
- **Windows**: WinSparkle downloads `TradeDeskyWatcher-*-setup.exe` from the site and runs the silent per-user installer
- **Running from source** (or if Sparkle/WinSparkle is not bundled): opens [the download page](https://tradedesky.chapilabs.com/download)

Disable automatic checks in `config.json`:

```json
{ "check_for_updates": false }
```

Release signing uses the `SPARKLE_ED_PRIVATE_KEY` GitHub Actions secret (32-byte Ed25519 seed, base64). The matching public key is `SUPublicEDKey` in the macOS plist and `win_sparkle_set_eddsa_public_key` on Windows.

After each release upload, CI purges Cloudflare for the stable `/desktop/*` aliases. Set `CLOUDFLARE_ZONE_ID` and `CLOUDFLARE_API_TOKEN` (permission: Zone.Cache Purge) on the GitHub repo.

## License

MIT — see [LICENSE](LICENSE).
