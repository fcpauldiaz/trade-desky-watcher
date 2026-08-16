# Trade Desky Watcher — Install Guide

End-user setup for macOS and Windows.

## Download

Get the latest release from [GitHub Releases](https://github.com/fcpauldiaz/trade-desky-watcher/releases):

- **macOS:** `TradeDeskyWatcher-*.dmg`
- **Windows:** `TradeDeskyWatcher-*-setup.exe` (recommended)
- **Windows (portable):** `TradeDeskyWatcher-*-win.zip`

## macOS

1. Open the DMG and drag **Trade Desky Watcher** to Applications.
2. Launch the app from Applications.
3. Grant **Full Disk Access** (System Settings → Privacy & Security → Full Disk Access → add Trade Desky Watcher).
4. Menu bar icon should show **Status: Watching** when ready.

### macOS Sequoia / Tahoe

If notifications are not detected, remove and re-add Full Disk Access, then restart the app.

## Windows

1. Run `TradeDeskyWatcher-*-setup.exe` (installs to `%LOCALAPPDATA%\Programs\TradeDeskyWatcher` and launches the app).
2. If SmartScreen warns about an unsigned app, choose **More info → Run anyway** (releases are unsigned until code signing is configured in CI).

Portable alternative: extract `TradeDeskyWatcher-*-win.zip` and run `TradeDeskyWatcher.exe`. Checking for updates still downloads the setup installer, which installs to `%LOCALAPPDATA%\Programs\TradeDeskyWatcher`.

## Connect to Trade Desky

1. Sign up at your Trade Desky URL and subscribe to Pro.
2. Connect Tradier or Schwab under **Connections**, complete onboarding.
3. In Trade Desky Watcher: **Account → Sign in…** with the same email and password.
4. Use **Account → Test connection** to verify delivery.

No URL to copy — the desktop app connects automatically after sign-in.

## Example config.json

Stored in the app support directory:

- macOS: `~/Library/Application Support/Trade Desky Watcher/config.json`
- Windows: `%APPDATA%\Trade Desky Watcher\config.json`

```json
{
  "poll_seconds": 0.5,
  "discord_only": false,
  "app_filter": "%discord%",
  "platform_url": "https://app.yourdomain.com",
  "ingest_url": "https://api.yourdomain.com/v1/ingest",
  "auth_token": null,
  "account_email": null,
  "check_for_updates": true
}
```

## Updates

Bundled apps update through Sparkle (macOS) and WinSparkle (Windows). Use **Check for updates…** in the menu to check immediately.

## Code signing (maintainers)

CI builds are unsigned by default. For production distribution, configure:

- **macOS:** Apple Developer ID + notarization in CI
- **Windows:** Authenticode certificate

See `.github/workflows/ci.yml` and signing scripts in the repo.
