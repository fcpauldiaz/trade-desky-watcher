#!/usr/bin/env python3
"""
Menu bar app for watching macOS Notification Center. Requires Full Disk Access.
"""
import queue
import subprocess
import threading
from pathlib import Path

import rumps

import ingest_sender
from notification_watcher.auth import AuthError, sign_in
from notification_watcher.config import get_app_logger, get_log_path, load_config, save_config
from notification_watcher.login import is_launch_at_login_enabled, open_full_disk_access_settings, set_launch_at_login
from notification_watcher.macos import format_delivered_date, get_notification_db_path
from notification_watcher.platform import get_backend
from notification_watcher.product import APP_NAME
from notification_watcher.updater import (
    check_for_updates,
    download_and_install,
    is_bundled_app,
    release_page_url,
    schedule_background_checks,
)
from notification_watcher.version import __version__
from notification_watcher.watcher import watch

RECENT_MAX = 10
QUEUE_DRAIN_INTERVAL = 0.5
FDA_RECHECK_INTERVAL = 5.0
POLL_LABELS = {
    0.01: "10 ms",
    0.05: "50 ms",
    0.1: "100 ms",
    0.5: "500 ms",
    1.0: "1 s",
}
ASSETS_DIR = Path(__file__).resolve().parent / "assets"


class NotificationWatcherApp(rumps.App):
    def __init__(self) -> None:
        icon = ASSETS_DIR / "icon.icns"
        super().__init__(
            APP_NAME,
            icon=str(icon) if icon.exists() else None,
            title=None if icon.exists() else "NC",
            quit_button=None,
        )
        self._config = load_config()
        self._db_path: Path | None = get_notification_db_path()
        self._poll_seconds = self._config.poll_seconds
        self._app_filter = self._config.effective_app_filter()
        self._discord_only = self._config.discord_only
        self._notif_queue: queue.Queue = queue.Queue()
        self._stop_thread = threading.Event()
        self._watcher_thread: threading.Thread | None = None
        self._recent: list[tuple[str, str, str, str, float | None]] = []
        self._status = "Starting..."

        self.menu = [
            rumps.MenuItem("Status: Starting...", callback=None),
            None,
            ["Recent", [rumps.MenuItem("(none)", callback=self._show_recent_detail)]],
            None,
            rumps.MenuItem("Discord only", callback=self._toggle_discord),
            rumps.MenuItem("Filter by app...", callback=self._set_app_filter),
            [
                "Poll interval",
                [
                    rumps.MenuItem("10 ms", callback=self._set_poll),
                    rumps.MenuItem("50 ms", callback=self._set_poll),
                    rumps.MenuItem("100 ms", callback=self._set_poll),
                    rumps.MenuItem("500 ms", callback=self._set_poll),
                    rumps.MenuItem("1 s", callback=self._set_poll),
                ],
            ],
            None,
            rumps.MenuItem("Launch at login", callback=self._toggle_launch_at_login),
            None,
            [
                "Account",
                [
                    rumps.MenuItem("Sign in...", callback=self._sign_in),
                    rumps.MenuItem("Sign out", callback=self._sign_out),
                    rumps.MenuItem("Test connection", callback=self._test_connection),
                    rumps.MenuItem("View logs", callback=self._view_logs),
                ],
            ],
            None,
            [
                "Updates",
                [
                    rumps.MenuItem(f"Version {__version__}", callback=None),
                    rumps.MenuItem("Check for updates...", callback=self._check_for_updates),
                ],
            ],
            None,
            "Quit",
        ]
        self._status_item = self.menu[0]
        self._poll_menu = self.menu["Poll interval"]
        self._recent_menu = self.menu["Recent"]
        self._launch_item = self.menu["Launch at login"]
        self._discord_item = self.menu["Discord only"]
        self._refresh_account_status()

        self._apply_poll_menu_state()
        self._discord_item.state = self._discord_only
        self._launch_item.state = is_launch_at_login_enabled()
        if self._config.launch_at_login != self._launch_item.state:
            self._config.launch_at_login = self._launch_item.state
            save_config(self._config)

        rumps.Timer(self._drain_queue, QUEUE_DRAIN_INTERVAL).start()
        rumps.Timer(self._recheck_permissions, FDA_RECHECK_INTERVAL).start()
        self._update_status_from_db()
        if self._config.check_for_updates:
            schedule_background_checks(self._notify_update_available, enabled=True)
        get_app_logger().info("App started (db=%s)", self._db_path)

    def _save_config(self) -> None:
        self._config.poll_seconds = self._poll_seconds
        self._config.discord_only = self._discord_only
        self._app_filter = self._config.effective_app_filter()
        save_config(self._config)

    def _set_status(self, status: str) -> None:
        self._status = status
        self._status_item.title = f"Status: {status}"

    def _update_status_from_db(self) -> None:
        self._db_path = get_notification_db_path()
        if self._db_path is None or not self._db_path.exists():
            self._set_status("Waiting for Full Disk Access")
            if self._watcher_thread and self._watcher_thread.is_alive():
                self._stop_thread.set()
            return
        self._set_status("Watching")
        if self._watcher_thread is None or not self._watcher_thread.is_alive():
            self._stop_thread.clear()
            self._start_watcher_thread()

    def _recheck_permissions(self, _: rumps.Timer) -> None:
        path = get_notification_db_path()
        exists = path is not None and path.exists()
        if exists and self._status.startswith("Waiting"):
            self._db_path = path
            self._update_status_from_db()
            rumps.notification(
                APP_NAME,
                "Full Disk Access granted",
                "Now watching notifications.",
            )
        elif not exists and self._status == "Watching":
            self._set_status("Waiting for Full Disk Access")
            self._stop_thread.set()
            open_full_disk_access_settings()

    def _apply_poll_menu_state(self) -> None:
        label = POLL_LABELS.get(self._poll_seconds, "500 ms")
        for item in self._poll_menu.values():
            if isinstance(item, rumps.MenuItem):
                item.state = item.title == label

    def _toggle_discord(self, sender: rumps.MenuItem) -> None:
        self._discord_only = not sender.state
        sender.state = self._discord_only
        self._config.discord_only = self._discord_only
        self._app_filter = self._config.effective_app_filter()
        self._save_config()

    def _set_app_filter(self, _: rumps.MenuItem) -> None:
        window = rumps.Window(
            message="App identifier filter (SQL LIKE, e.g. %discord%):",
            title="Filter by app",
            default_text=self._config.app_filter or "",
            ok="Apply",
            cancel="Cancel",
        )
        response = window.run()
        if response.clicked != 1:
            return
        value = (response.text or "").strip()
        self._config.app_filter = value or None
        if value:
            self._discord_only = False
            self._config.discord_only = False
            self._discord_item.state = False
        self._app_filter = self._config.effective_app_filter()
        self._save_config()

    def _set_poll(self, sender: rumps.MenuItem) -> None:
        for item in self._poll_menu.values():
            if isinstance(item, rumps.MenuItem):
                item.state = item == sender
        for seconds, label in POLL_LABELS.items():
            if sender.title == label:
                self._poll_seconds = seconds
                break
        self._save_config()

    def _toggle_launch_at_login(self, sender: rumps.MenuItem) -> None:
        enabled = not sender.state
        set_launch_at_login(enabled)
        sender.state = is_launch_at_login_enabled()
        self._config.launch_at_login = sender.state
        save_config(self._config)

    def _on_notification(
        self, app_id: str, title: str, subtitle: str, body: str, delivered_date: float | None
    ) -> None:
        self._notif_queue.put((app_id, title, subtitle, body, delivered_date))

    def _on_error(self, exc: Exception) -> None:
        self._set_status(f"Error: {exc}")

    def _watcher_loop(self) -> None:
        backend = get_backend()
        if not self._db_path:
            return

        def stop_flag() -> bool:
            return self._stop_thread.is_set()

        watch(
            backend,
            self._db_path,
            lambda: self._poll_seconds,
            lambda: self._app_filter,
            self._on_notification,
            stop_flag=stop_flag,
            on_error=self._on_error,
        )

    def _start_watcher_thread(self) -> None:
        self._watcher_thread = threading.Thread(target=self._watcher_loop, daemon=True)
        self._watcher_thread.start()

    def _refresh_account_status(self) -> None:
        if self._config.is_signed_in():
            email = self._config.account_email or "signed in"
            self._set_status(f"Signed in as {email}")
        elif self._status == "Watching":
            self._set_status("Watching (not signed in)")

    def _sign_in(self, _: rumps.MenuItem) -> None:
        email_window = rumps.Window(
            message="Trade Platform email:",
            title="Sign in",
            default_text=self._config.account_email or "",
            ok="Next",
            cancel="Cancel",
        )
        email_response = email_window.run()
        if email_response.clicked != 1:
            return
        email = (email_response.text or "").strip()
        if not email:
            rumps.alert("Email is required.", "Sign in")
            return
        password_window = rumps.Window(
            message="Password:",
            title="Sign in",
            default_text="",
            ok="Sign in",
            cancel="Cancel",
        )
        password_response = password_window.run()
        if password_response.clicked != 1:
            return
        password = password_response.text or ""
        try:
            result = sign_in(email, password, self._config.platform_url)
        except AuthError as exc:
            rumps.alert(str(exc), "Sign in failed")
            return
        self._config.auth_token = result["auth_token"]
        self._config.ingest_url = result["ingest_url"]
        self._config.account_email = result["account_email"]
        save_config(self._config)
        self._refresh_account_status()
        rumps.notification(APP_NAME, "Signed in", result["account_email"])

    def _sign_out(self, _: rumps.MenuItem) -> None:
        if not self._config.is_signed_in():
            rumps.alert("Not signed in.", "Account")
            return
        self._config.auth_token = None
        self._config.account_email = None
        save_config(self._config)
        self._update_status_from_db()
        rumps.notification(APP_NAME, "Signed out", "")

    def _test_connection(self, _: rumps.MenuItem) -> None:
        ok, message = ingest_sender.send_test_connection()
        title = "Connection test" if ok else "Connection test failed"
        rumps.alert(message, title)

    def _view_logs(self, _: rumps.MenuItem) -> None:
        path = get_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("", encoding="utf-8")
        subprocess.run(["open", "-e", str(path)], check=False, timeout=5)

    def _drain_queue(self, _: rumps.Timer) -> None:
        while True:
            try:
                item = self._notif_queue.get_nowait()
            except queue.Empty:
                break
            app_id, title, subtitle, body, delivered_date = item
            ingest_sender.send_notification(
                app_id, title, subtitle, body, delivered_date, self._config
            )
            self._recent.insert(0, item)
            self._recent = self._recent[:RECENT_MAX]
            self._rebuild_recent_menu()

    def _show_recent_detail(self, sender: rumps.MenuItem) -> None:
        title = sender.title
        if title in ("(none)",) or not title[0].isdigit():
            return
        try:
            index = int(title.split(".", 1)[0]) - 1
        except ValueError:
            return
        if index < 0 or index >= len(self._recent):
            return
        app_id, notif_title, subtitle, body, delivered_date = self._recent[index]
        message = (
            f"App: {app_id}\n"
            f"Time: {format_delivered_date(delivered_date)}\n"
            f"Title: {notif_title}\n"
            f"Subtitle: {subtitle}\n"
            f"Body: {body}"
        )
        rumps.alert(message, notif_title or "Notification")

    def _rebuild_recent_menu(self) -> None:
        self._recent_menu.clear()
        if not self._recent:
            self._recent_menu.add(rumps.MenuItem("(none)", callback=self._show_recent_detail))
            return
        items = []
        for i, (app_id, title, _subtitle, _body, _delivered_date) in enumerate(self._recent):
            label = f"{title or '(no title)'} — {app_id}" if app_id else (title or "(no title)")
            if len(label) > 55:
                label = label[:52] + "..."
            items.append(rumps.MenuItem(f"{i + 1}. {label}", callback=self._show_recent_detail))
        self._recent_menu.update(items)

    def _notify_update_available(self, result) -> None:
        latest = result.latest
        if latest is None:
            return
        rumps.notification(
            "Update available",
            f"{APP_NAME} {latest.version}",
            "Open the menu → Updates → Check for updates...",
        )

    def _check_for_updates(self, _: rumps.MenuItem) -> None:
        result = check_for_updates(force=True)
        if result.error:
            rumps.alert(f"Could not check for updates:\n\n{result.error}", "Updates")
            return
        latest = result.latest
        if latest is None:
            rumps.alert("No release information found.", "Updates")
            return
        if not result.update_available:
            rumps.alert(f"You are on the latest version ({__version__}).", "Updates")
            return

        notes = latest.release_notes
        if len(notes) > 400:
            notes = notes[:397] + "..."
        message = f"Version {latest.version} is available.\n\nYou are on {__version__}."
        if notes:
            message += f"\n\n{notes}"

        if not is_bundled_app():
            if rumps.alert(message, "Update available", ok="Open download page", cancel="Later") == 1:
                subprocess.run(["open", release_page_url()], check=False, timeout=5)
            return

        if rumps.alert(message, "Update available", ok="Download and install", cancel="Later") != 1:
            return

        try:
            target = download_and_install(latest)
        except Exception as exc:
            rumps.alert(f"Update failed:\n\n{exc}", "Updates")
            return

        if rumps.alert(
            f"Installed to:\n{target}\n\nRestart {APP_NAME} now?",
            "Update installed",
            ok="Restart",
            cancel="Later",
        ) == 1:
            subprocess.Popen(["open", "-n", target], start_new_session=True)
            self._stop_thread.set()
            rumps.quit_application()

    @rumps.clicked("Quit")
    def quit_app(self, _: rumps.MenuItem) -> None:
        self._stop_thread.set()
        rumps.quit_application()


def main() -> None:
    path = get_notification_db_path()
    if path is None or not path.exists():
        rumps.alert(
            "Full Disk Access required",
            f"{APP_NAME} needs Full Disk Access to read notifications.\n\n"
            "System Settings will open. Add this app (or Terminal) to Full Disk Access.",
        )
        open_full_disk_access_settings()
    app = NotificationWatcherApp()
    app.run()


if __name__ == "__main__":
    main()
