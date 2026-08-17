# Changelog

## 1.4.6

- Send a TradeDeskyWatcher User-Agent so Cloudflare no longer blocks sign-in and ingest (error 1010)
- Purge Cloudflare cache for stable `/desktop` download URLs after each release

## 1.4.5

- Sign in against tradedesky.chapilabs.com by default; replace saved localhost platform/ingest URLs
- Override with TRADE_PLATFORM_URL and TRADE_INGEST_URL for local development

## 1.4.4

- Always capture Discord notifications only; remove Discord-only and app-filter menu options

## 1.4.3

- Prompt for Full Disk Access and open System Settings when Notification Center cannot be read
- Open the notification database read-only so a missing write grant is not reported as a generic SQLite error

## 1.4.2

- Fix the macOS menu bar app crashing on launch with py2app's generic launch error

## 1.4.1

- Use the Trade Desky app icon and Chapi Labs copyright in About / Get Info and Windows file properties

## 1.4.0

- Sparkle 2 auto-update on macOS and WinSparkle on Windows (signed appcast)
- Windows per-user setup.exe installer for in-place updates; zip remains for portable install
- Falls back to GitHub Releases updater when native libraries are not bundled

## 1.3.0

- Rebranded to **Trade Desky Watcher** (app name, installers, GitHub repo `trade-desky-watcher`)
- Existing config and launch-at-login settings migrate from Notification Watcher

## 1.2.0

- GitHub Releases auto-update for bundled macOS and Windows builds
- Manual "Check for updates..." in menu bar / tray
- Sparkle appcast.xml published on each release

## 1.1.0

- Cross-platform package refactor (`notification_watcher/`)
- Windows tray app watching Action Center via `wpndatabase.db`
- Discord-compatible webhook embeds with auto-detect; generic JSON for custom backends
- Webhook retries, HTTPS validation, SSRF guard for private URLs
- Persistent settings (poll interval, filters, launch at login)
- macOS: status line, FDA re-check, recent detail view, test webhook, view logs
- Shared watcher with bounded dedup and incremental polling
- CI: pytest on Ubuntu; macOS DMG and Windows zip artifacts on release tags
- Local signing scripts for macOS and Windows
- MIT license and privacy policy

## 1.0.0

- Initial macOS menu bar app
