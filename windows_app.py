#!/usr/bin/env python3
"""
Windows system tray app for watching Action Center notifications.
"""
from __future__ import annotations

import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog

import pystray
from PIL import Image, ImageDraw

import ingest_sender
from notification_watcher.auth import AuthError, sign_in
from notification_watcher.config import get_app_logger, get_log_path, load_config, save_config
from notification_watcher.login import is_launch_at_login_enabled, set_launch_at_login
from notification_watcher.platform import get_backend
from notification_watcher.types import AppConfig
from notification_watcher.native_update import start_native_or_github
from notification_watcher.product import APP_NAME, APP_NAME_COMPACT
from notification_watcher.updater import (
    check_for_updates,
    download_and_install,
    is_bundled_app,
    release_page_url,
)
from notification_watcher.version import __version__
from notification_watcher.watcher import watch
from notification_watcher.windows import format_delivered_date, get_notification_db_path

RECENT_MAX = 10
QUEUE_DRAIN_INTERVAL = 0.5
POLL_LABELS = {
    0.01: "10 ms",
    0.05: "50 ms",
    0.1: "100 ms",
    0.5: "500 ms",
    1.0: "1 s",
}
ASSETS_DIR = Path(__file__).resolve().parent / "assets"


def _load_icon() -> Image.Image:
    ico = ASSETS_DIR / "icon.ico"
    if ico.exists():
        return Image.open(ico)
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((8, 8, 56, 56), fill=(66, 133, 244, 255))
    draw.rectangle((30, 18, 34, 40), fill="white")
    draw.ellipse((26, 40, 38, 50), fill="white")
    return img


class WindowsNotificationApp:
    def __init__(self) -> None:
        self._config = load_config()
        self._db_path = get_notification_db_path()
        self._poll_seconds = self._config.poll_seconds
        self._app_filter = self._config.effective_app_filter()
        self._discord_only = self._config.discord_only
        self._notif_queue: queue.Queue = queue.Queue()
        self._stop_thread = threading.Event()
        self._watcher_thread: threading.Thread | None = None
        self._recent: list[tuple[str, str, str, str, float | None]] = []
        self._status = "Starting..."
        self._icon: pystray.Icon | None = None
        self._tk_root = tk.Tk()
        self._tk_root.withdraw()

        if self._db_path is None or not self._db_path.exists():
            messagebox.showinfo(
                APP_NAME,
                "Notification database not found yet.\n\n"
                "The app will watch:\n"
                "%LOCALAPPDATA%\\Microsoft\\Windows\\Notifications\\wpndatabase.db\n\n"
                "Send a test notification if watching does not start.",
            )

        self._quitting_for_update = False
        self._start_background_tasks()
        self._build_tray()
        self._native_updater = start_native_or_github(
            automatic=self._config.check_for_updates,
            on_github_update=self._notify_update_available,
            on_shutdown=self._sparkle_shutdown,
        )

    def _save_config(self) -> None:
        self._config.poll_seconds = self._poll_seconds
        self._config.discord_only = self._discord_only
        self._app_filter = self._config.effective_app_filter()
        save_config(self._config)

    def _set_status(self, status: str) -> None:
        self._status = status
        if self._icon:
            self._icon.update_menu()

    def _start_background_tasks(self) -> None:
        threading.Thread(target=self._drain_loop, daemon=True).start()
        threading.Thread(target=self._permission_loop, daemon=True).start()
        self._update_watcher()
        get_app_logger().info("Windows app started (db=%s)", self._db_path)

    def _permission_loop(self) -> None:
        import time

        while not self._stop_thread.is_set():
            path = get_notification_db_path()
            exists = path is not None and path.exists()
            if exists and self._status.startswith(("Waiting", "Starting")):
                self._db_path = path
                self._set_status("Watching")
                self._update_watcher()
            elif not exists and self._status == "Watching":
                self._set_status("Waiting for notification database")
                self._stop_thread.set()
                self._stop_thread = threading.Event()
            time.sleep(5.0)

    def _update_watcher(self) -> None:
        if self._db_path is None or not self._db_path.exists():
            self._set_status("Waiting for notification database")
            return
        self._set_status("Watching")
        self._stop_thread.set()
        self._stop_thread = threading.Event()
        self._watcher_thread = threading.Thread(target=self._watcher_loop, daemon=True)
        self._watcher_thread.start()

    def _on_notification(
        self, app_id: str, title: str, subtitle: str, body: str, delivered_date: float | None
    ) -> None:
        self._notif_queue.put((app_id, title, subtitle, body, delivered_date))

    def _on_error(self, exc: Exception) -> None:
        self._set_status(f"Error: {exc}")

    def _watcher_loop(self) -> None:
        if not self._db_path:
            return
        backend = get_backend()

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

    def _drain_loop(self) -> None:
        import time

        while True:
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
                if self._icon:
                    self._icon.update_menu()
            time.sleep(QUEUE_DRAIN_INTERVAL)

    def _build_tray(self) -> None:
        self._icon = pystray.Icon(
            APP_NAME_COMPACT,
            _load_icon(),
            APP_NAME,
            menu=self._build_menu,
        )

    def _build_menu(self) -> pystray.Menu:
        items: list[pystray.MenuItem | pystray.Menu] = [
            pystray.MenuItem(f"Status: {self._status}", None, enabled=False),
            pystray.Menu.SEPARATOR,
        ]
        recent_items: list[pystray.MenuItem] = []
        if not self._recent:
            recent_items.append(pystray.MenuItem("(none)", None, enabled=False))
        else:
            recent_items = [
                pystray.MenuItem(
                    self._recent_label(i, item),
                    self._make_recent_handler(i),
                )
                for i, item in enumerate(self._recent)
            ]
        items.append(pystray.MenuItem("Recent", pystray.Menu(*recent_items)))
        items.append(pystray.Menu.SEPARATOR)
        items.append(
            pystray.MenuItem(
                "Discord only",
                self._toggle_discord,
                checked=lambda _: self._discord_only,
            )
        )
        items.append(pystray.MenuItem("Filter by app...", self._set_app_filter))
        poll_submenu = pystray.Menu(
            *[
                pystray.MenuItem(
                    label,
                    self._make_poll_handler(seconds),
                    checked=lambda _, s=seconds: self._poll_seconds == s,
                    radio=True,
                )
                for seconds, label in POLL_LABELS.items()
            ]
        )
        items.append(pystray.MenuItem("Poll interval", poll_submenu))
        items.append(pystray.Menu.SEPARATOR)
        items.append(
            pystray.MenuItem(
                "Launch at login",
                self._toggle_launch_at_login,
                checked=lambda _: is_launch_at_login_enabled(),
            )
        )
        items.append(pystray.Menu.SEPARATOR)
        items.append(
            pystray.MenuItem(
                "Account",
                pystray.Menu(
                    pystray.MenuItem("Sign in...", self._sign_in),
                    pystray.MenuItem("Sign out", self._sign_out),
                    pystray.MenuItem("Test connection", self._test_connection),
                    pystray.MenuItem("View logs", self._view_logs),
                ),
            )
        )
        items.append(pystray.Menu.SEPARATOR)
        items.append(
            pystray.MenuItem(
                "Updates",
                pystray.Menu(
                    pystray.MenuItem(f"Version {__version__}", None, enabled=False),
                    pystray.MenuItem("Check for updates...", self._check_for_updates),
                ),
            )
        )
        items.append(pystray.Menu.SEPARATOR)
        items.append(pystray.MenuItem("Quit", self._quit))
        return pystray.Menu(*items)

    def _recent_label(self, index: int, item: tuple[str, str, str, str, float | None]) -> str:
        app_id, title, _, _, _ = item
        label = f"{title or '(no title)'} — {app_id}" if app_id else (title or "(no title)")
        if len(label) > 55:
            label = label[:52] + "..."
        return f"{index + 1}. {label}"

    def _make_recent_handler(self, index: int):
        def handler(_icon, _item) -> None:
            self._show_recent_at(index)

        return handler

    def _make_poll_handler(self, seconds: float):
        def handler(_icon, _item) -> None:
            self._poll_seconds = seconds
            self._save_config()
            self._update_watcher()

        return handler

    def _show_recent_at(self, index: int) -> None:
        if index < 0 or index >= len(self._recent):
            return
        app_id, title, subtitle, body, delivered_date = self._recent[index]
        messagebox.showinfo(
            title or "Notification",
            f"App: {app_id}\n"
            f"Time: {format_delivered_date(delivered_date)}\n"
            f"Title: {title}\n"
            f"Subtitle: {subtitle}\n"
            f"Body: {body}",
        )

    def _toggle_discord(self, _icon, _item) -> None:
        self._discord_only = not self._discord_only
        self._config.discord_only = self._discord_only
        self._app_filter = self._config.effective_app_filter()
        self._save_config()
        self._update_watcher()

    def _set_app_filter(self, _icon, _item) -> None:
        value = simpledialog.askstring(
            "Filter by app",
            "App identifier filter (SQL LIKE, e.g. %discord%):",
            initialvalue=self._config.app_filter or "",
            parent=self._tk_root,
        )
        if value is None:
            return
        self._config.app_filter = value.strip() or None
        if self._config.app_filter:
            self._discord_only = False
            self._config.discord_only = False
        self._app_filter = self._config.effective_app_filter()
        self._save_config()
        self._update_watcher()

    def _toggle_launch_at_login(self, _icon, _item) -> None:
        enabled = not is_launch_at_login_enabled()
        set_launch_at_login(enabled, Path(sys.executable))
        self._config.launch_at_login = is_launch_at_login_enabled()
        save_config(self._config)

    def _sign_in(self, _icon, _item) -> None:
        email = simpledialog.askstring(
            "Sign in",
            "Trade Platform email:",
            initialvalue=self._config.account_email or "",
            parent=self._tk_root,
        )
        if not email:
            return
        password = simpledialog.askstring(
            "Sign in",
            "Password:",
            show="*",
            parent=self._tk_root,
        )
        if password is None:
            return
        try:
            result = sign_in(email.strip(), password, self._config.platform_url)
        except AuthError as exc:
            messagebox.showerror("Sign in failed", str(exc))
            return
        self._config.auth_token = result["auth_token"]
        self._config.ingest_url = result["ingest_url"]
        self._config.account_email = result["account_email"]
        save_config(self._config)
        messagebox.showinfo("Signed in", result["account_email"])

    def _sign_out(self, _icon, _item) -> None:
        if not self._config.is_signed_in():
            messagebox.showinfo("Account", "Not signed in.")
            return
        self._config.auth_token = None
        self._config.account_email = None
        save_config(self._config)
        messagebox.showinfo("Account", "Signed out.")

    def _test_connection(self, _icon, _item) -> None:
        ok, message = ingest_sender.send_test_connection()
        if ok:
            messagebox.showinfo("Connection test", message)
        else:
            messagebox.showerror("Connection test failed", message)

    def _view_logs(self, _icon, _item) -> None:
        path = get_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("", encoding="utf-8")
        subprocess.run(["notepad.exe", str(path)], check=False)

    def _notify_update_available(self, result) -> None:
        latest = result.latest
        if latest is None:
            return
        self._tk_root.after(
            0,
            lambda: messagebox.showinfo(
                "Update available",
                f"{APP_NAME} {latest.version} is available.\n\n"
                "Open the tray menu → Updates → Check for updates...",
            ),
        )

    def _sparkle_shutdown(self) -> None:
        self._quitting_for_update = True
        self._tk_root.after(0, lambda: self._quit(self._icon, None))

    def _check_for_updates(self, _icon, _item) -> None:
        if self._native_updater.check_now():
            return
        result = check_for_updates(force=True)
        if result.error:
            messagebox.showerror("Updates", f"Could not check for updates:\n\n{result.error}")
            return
        latest = result.latest
        if latest is None:
            messagebox.showinfo("Updates", "No release information found.")
            return
        if not result.update_available:
            messagebox.showinfo("Updates", f"You are on the latest version ({__version__}).")
            return

        notes = latest.release_notes
        if len(notes) > 400:
            notes = notes[:397] + "..."
        message = f"Version {latest.version} is available.\n\nYou are on {__version__}."
        if notes:
            message += f"\n\n{notes}"

        if not is_bundled_app():
            if messagebox.askyesno("Update available", message + "\n\nOpen download page?"):
                subprocess.run(["cmd", "/c", "start", "", release_page_url()], check=False)
            return

        if not messagebox.askyesno("Update available", message + "\n\nDownload and install now?"):
            return

        try:
            script_or_target = download_and_install(latest)
        except Exception as exc:
            messagebox.showerror("Updates", f"Update failed:\n\n{exc}")
            return

        if sys.platform == "win32" and str(script_or_target).endswith(".bat"):
            subprocess.Popen(
                ["cmd", "/c", "start", "", "/min", str(script_or_target)],
                creationflags=subprocess.DETACHED_PROCESS if hasattr(subprocess, "DETACHED_PROCESS") else 0,
            )
            self._quit(_icon, _item)
            return

        messagebox.showinfo("Updates", f"Installed to:\n{script_or_target}")

    def _quit(self, _icon, _item) -> None:
        self._stop_thread.set()
        if not self._quitting_for_update:
            self._native_updater.cleanup()
        if self._icon:
            self._icon.stop()
        self._tk_root.destroy()

    def run(self) -> None:
        if self._icon:
            self._icon.run()


def main() -> None:
    app = WindowsNotificationApp()
    app.run()


if __name__ == "__main__":
    main()
