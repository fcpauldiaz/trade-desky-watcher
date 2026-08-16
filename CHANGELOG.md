# Changelog

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
