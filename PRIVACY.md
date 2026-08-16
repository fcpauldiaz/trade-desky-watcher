# Privacy Policy

Trade Desky Watcher is a local utility. It does not operate a cloud service or collect analytics.

## What the app reads

- **macOS**: Notification content from the local Notification Center SQLite database (app identifier, title, subtitle, body, delivery time). Requires Full Disk Access.
- **Windows**: Notification content from the local `wpndatabase.db` file (app identifier, toast text, arrival time).

## What leaves your device

- When signed in to Trade Desky, matching notification data is sent via HTTPS POST to the platform ingest endpoint.
- No data is sent if you are not signed in.

## What is stored locally

- Settings: `config.json` in the app support directory.
- Logs: `notification_watcher.log` in the same directory (ingest attempts, errors).

## Third parties

When signed in, notifications are sent to your Trade Desky ingest endpoint. The platform privacy policy applies to that data.

## Telemetry

This app checks GitHub Releases for newer versions when `check_for_updates` is enabled (default). No other telemetry, crash reporting, or third-party analytics.

## Contact

For privacy questions, open an issue in the project repository.
