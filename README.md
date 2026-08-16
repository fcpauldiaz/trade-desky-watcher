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

GitHub Actions runs tests on every push/PR. On pushes to `main`, it also builds macOS and Windows artifacts, creates a **`v{version}` tag** from [`notification_watcher/version.py`](notification_watcher/version.py), and publishes a [GitHub Release](https://github.com/fcpauldiaz/trade-desky-watcher/releases) with download links for:

- `TradeDeskyWatcher-{version}.dmg` (macOS)
- `TradeDeskyWatcher-{version}-setup.exe` (Windows installer; auto-update)
- `TradeDeskyWatcher-{version}-win.zip` (Windows portable)
- `appcast.xml` (Sparkle / WinSparkle feed, Ed25519-signed)

Bump `__version__` in `notification_watcher/version.py` before merging to `main` to publish a new release tag.

## Signing (local)

Unsigned CI builds are fine for personal use. For distribution:

```bash
# macOS — set SIGN_IDENTITY and NOTARY_PROFILE (notarytool keychain profile)
SIGN_IDENTITY="Developer ID Application: Your Name" ./scripts/sign_and_notarize_mac.sh

# Windows — set WINDOWS_CERT_PATH and optional WINDOWS_CERT_PASSWORD
./scripts/sign_windows.ps1
```

## Filtering

- Set `"discord_only": true` in config to forward only Discord app notifications.
- Set `"app_filter": "%slack%"` (SQL LIKE) to limit by app bundle id.

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

Bundled macOS and Windows builds use **Sparkle 2** and **WinSparkle** with a signed `appcast.xml` on GitHub Releases:

- **On startup** and **once per day** (native updater)
- **Manual check**: menu bar / tray → **Updates → Check for updates...**
- **macOS**: Sparkle downloads the DMG and replaces the app
- **Windows**: WinSparkle downloads `TradeDeskyWatcher-*-setup.exe` and runs the silent per-user installer (`%LOCALAPPDATA%\Programs\TradeDeskyWatcher`)
- **Running from source** (or if Sparkle/WinSparkle is not bundled): falls back to the GitHub Releases updater, which opens the download page instead of installing in place

Disable automatic checks in `config.json`:

```json
{ "check_for_updates": false }
```

Release signing uses the `SPARKLE_ED_PRIVATE_KEY` GitHub Actions secret (32-byte Ed25519 seed, base64). The matching public key is `SUPublicEDKey` in the macOS plist and `win_sparkle_set_eddsa_public_key` on Windows.

## License

MIT — see [LICENSE](LICENSE).
