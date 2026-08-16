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
python3 setup.py py2app
./create_dmg.sh
```

Output: `dist/Trade Desky Watcher.app`, `dist/TradeDeskyWatcher-1.3.0.dmg`

### Windows .exe

```bash
pip install -r requirements-windows.txt
python scripts/generate_icons.py
pyinstaller notification_watcher.spec
```

Output: `dist/TradeDeskyWatcher/TradeDeskyWatcher.exe`

## CI artifacts

See [INSTALL.md](INSTALL.md) for end-user setup (macOS FDA, Windows, sign-in).

GitHub Actions runs tests on every push/PR. On pushes to `main`, it also builds macOS and Windows artifacts, creates a **`v{version}` tag** from [`notification_watcher/version.py`](notification_watcher/version.py), and publishes a [GitHub Release](https://github.com/fcpauldiaz/trade-desky-watcher/releases) with download links for:

- `TradeDeskyWatcher-{version}.dmg` (macOS)
- `TradeDeskyWatcher-{version}-win.zip` (Windows)

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
2. Delete the install folder.
3. Remove `%APPDATA%\Trade Desky Watcher\`.
4. Remove the `TradeDeskyWatcher` entry from Registry → `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` if present.

## Privacy

See [PRIVACY.md](PRIVACY.md). No telemetry.

## Auto-update

Bundled macOS and Windows builds check [GitHub Releases](https://github.com/fcpauldiaz/trade-desky-watcher/releases) for updates:

- **On startup** (after 60 seconds) and **once per day**
- **Manual check**: menu bar / tray → **Updates → Check for updates...**
- **macOS**: downloads the DMG, installs to `/Applications`, offers restart
- **Windows**: downloads the zip, applies on quit via a small updater script, then relaunches
- **Running from source**: opens the release download page instead of installing in place

Disable automatic checks in `config.json`:

```json
{ "check_for_updates": false }
```

CI also publishes `appcast.xml` on each release for optional future [Sparkle](https://sparkle-project.org/) integration (`SUFeedURL` is set in the macOS app plist).

## License

MIT — see [LICENSE](LICENSE).
