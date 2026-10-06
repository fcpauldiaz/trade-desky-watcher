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
from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox

import pystray
from PIL import Image, ImageDraw

import ingest_sender
from notification_watcher.account_status import format_status_line
from notification_watcher.auth import AuthError, sign_in
from notification_watcher.config import get_app_logger, get_log_path, load_config, save_config
from notification_watcher.login import is_launch_at_login_enabled, set_launch_at_login
from notification_watcher.platform import get_backend
from notification_watcher.types import DISCORD_APP_FILTER
from notification_watcher.native_update import start_native_or_github
from notification_watcher.product import APP_NAME, APP_NAME_COMPACT, DOWNLOAD_PAGE_URL
from notification_watcher.version import __version__
from notification_watcher.watcher import watch
from notification_watcher.win_sign_in import show_sign_in_dialog
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
    for name in ("icon.ico", "icon.png"):
        path = ASSETS_DIR / name
        if path.exists():
            return Image.open(path).convert("RGBA")
    img = Image.new("RGBA", (64, 64), (17, 17, 17, 255))
    draw = ImageDraw.Draw(img)
    draw.line([(16, 38), (32, 18), (48, 38)], fill=(34, 197, 94, 255), width=4)
    draw.line([(32, 22), (32, 46)], fill=(34, 197, 94, 255), width=4)
    return img


class WindowsNotificationApp:
    def __init__(self) -> None:
        self._config = load_config()
        self._db_path = get_notification_db_path()
        self._poll_seconds = self._config.poll_seconds
        self._notif_queue: queue.Queue = queue.Queue()
        self._stop_thread = threading.Event()
        self._watcher_thread: threading.Thread | None = None
        self._recent: list[tuple[str, str, str, str, float | None]] = []
        self._status = "Starting..."
        self._icon: pystray.Icon | None = None
        self._tk_root = tk.Tk()
        self._tk_root.withdraw()
        self._tk_root.protocol("WM_DELETE_WINDOW", lambda: None)
        self._ui_queue: queue.Queue[Callable[[], None]] = queue.Queue()
        self._ui_running = False
        self._tray_thread: threading.Thread | None = None

        if self._db_path is None or not self._db_path.exists():
            self._run_on_ui(self._show_db_missing_notice)

        self._quitting_for_update = False
        self._start_background_tasks()
        self._build_tray()
        self._native_updater = start_native_or_github(
            automatic=self._config.check_for_updates,
            on_shutdown=self._sparkle_shutdown,
        )
        if self._config.is_signed_in():
            get_app_logger().info(
                "Restored session for %s",
                self._config.account_email or "signed-in user",
            )

    def _save_config(self) -> None:
        self._config.poll_seconds = self._poll_seconds
        save_config(self._config)

    def _refresh_tray_menu(self) -> None:
        if self._icon:
            self._icon.menu = self._build_menu()

    def _run_on_ui(self, fn: Callable[[], None]) -> None:
        self._ui_queue.put(fn)

    def _pump_ui_queue(self) -> None:
        while True:
            try:
                fn = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            fn()
        if self._ui_running:
            self._tk_root.after(50, self._pump_ui_queue)

    def _show_db_missing_notice(self) -> None:
        messagebox.showinfo(
            APP_NAME,
            "Notification database not found yet.\n\n"
            "The app will watch:\n"
            "%LOCALAPPDATA%\\Microsoft\\Windows\\Notifications\\wpndatabase.db\n\n"
            "Send a test notification if watching does not start.",
            parent=self._tk_root,
        )

    def _set_status(self, status: str) -> None:
        self._status = status
        self._refresh_tray_menu()

    def _status_label(self) -> str:
        return format_status_line(self._status, self._config)

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
            DISCORD_APP_FILTER,
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
                self._refresh_tray_menu()
            time.sleep(QUEUE_DRAIN_INTERVAL)

    def _build_tray(self) -> None:
        self._icon = pystray.Icon(
            APP_NAME_COMPACT,
            _load_icon(),
            APP_NAME,
            menu=self._build_menu(),
        )

    def _build_menu(self) -> pystray.Menu:
        items: list[pystray.MenuItem | pystray.Menu] = [
            pystray.MenuItem(lambda _: self._status_label(), None, enabled=False),
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
            self._run_on_ui(lambda: self._show_recent_at(index))

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
            parent=self._tk_root,
        )

    def _toggle_launch_at_login(self, _icon, _item) -> None:
        enabled = not is_launch_at_login_enabled()
        set_launch_at_login(enabled, Path(sys.executable))
        self._config.launch_at_login = is_launch_at_login_enabled()
        save_config(self._config)

    def _sign_in(self, _icon, _item) -> None:
        self._run_on_ui(self._sign_in_ui)

    def _sign_in_ui(self) -> None:
        def authenticate(email: str, password: str) -> tuple[bool, str]:
            try:
                result = sign_in(email, password, self._config.platform_url)
            except AuthError as exc:
                return False, str(exc)
            self._config.auth_token = result["auth_token"]
            self._config.ingest_url = result["ingest_url"]
            self._config.account_email = result["account_email"]
            save_config(self._config)
            ingest_sender.flush_pending(self._config)
            return True, ""

        signed_email = show_sign_in_dialog(
            self._tk_root,
            initial_email=self._config.account_email or "",
            on_submit=authenticate,
        )
        if signed_email:
            self._set_status(self._status)
            messagebox.showinfo(
                "Signed in",
                f"You are signed in as {signed_email}.",
                parent=self._tk_root,
            )

    def _sign_out(self, _icon, _item) -> None:
        self._run_on_ui(self._sign_out_ui)

    def _sign_out_ui(self) -> None:
        if not self._config.is_signed_in():
            messagebox.showinfo("Account", "Not signed in.", parent=self._tk_root)
            return
        self._config.auth_token = None
        self._config.account_email = None
        save_config(self._config)
        messagebox.showinfo("Account", "Signed out.", parent=self._tk_root)

    def _test_connection(self, _icon, _item) -> None:
        self._run_on_ui(self._test_connection_ui)

    def _test_connection_ui(self) -> None:
        ok, message = ingest_sender.send_test_connection()
        if ok:
            messagebox.showinfo("Connection test", message, parent=self._tk_root)
        else:
            messagebox.showerror("Connection test failed", message, parent=self._tk_root)

    def _view_logs(self, _icon, _item) -> None:
        path = get_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("", encoding="utf-8")
        subprocess.run(["notepad.exe", str(path)], check=False)

    def _sparkle_shutdown(self) -> None:
        self._quitting_for_update = True
        self._run_on_ui(self._quit_ui)

    def _check_for_updates(self, _icon, _item) -> None:
        self._run_on_ui(self._check_for_updates_ui)

    def _check_for_updates_ui(self) -> None:
        if self._native_updater.check_now():
            return
        if messagebox.askyesno(
            "Updates",
            f"Download the latest {APP_NAME} from the Trade Desky website.\n\nOpen download page?",
            parent=self._tk_root,
        ):
            subprocess.run(["cmd", "/c", "start", "", DOWNLOAD_PAGE_URL], check=False)

    def _quit(self, _icon, _item) -> None:
        self._run_on_ui(self._quit_ui)

    def _quit_ui(self) -> None:
        self._stop_thread.set()
        self._ui_running = False
        if not self._quitting_for_update:
            self._native_updater.cleanup()
        if self._icon:
            self._icon.stop()
        self._tk_root.destroy()

    def run(self) -> None:
        if not self._icon:
            return
        self._ui_running = True
        self._tk_root.after(50, self._pump_ui_queue)
        self._tray_thread = threading.Thread(target=self._icon.run, daemon=True)
        self._tray_thread.start()
        self._tk_root.mainloop()


def main() -> None:
    app = WindowsNotificationApp()
    app.run()


if __name__ == "__main__":
    main()
