import os
import plistlib
import subprocess
import sys
from pathlib import Path

from notification_watcher.product import APP_NAME_COMPACT, BUNDLE_ID, LEGACY_APP_NAME_COMPACT, LEGACY_BUNDLE_ID

LAUNCH_AGENT_ID = BUNDLE_ID
REGISTRY_APP_NAME = APP_NAME_COMPACT


def _macos_app_path() -> Path | None:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent.parent
    return None


def _plist_path(label: str) -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"


def is_launch_at_login_enabled() -> bool:
    if sys.platform == "darwin":
        return _plist_path(LAUNCH_AGENT_ID).exists() or _plist_path(LEGACY_BUNDLE_ID).exists()
    if sys.platform == "win32":
        import winreg

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
            ) as key:
                try:
                    winreg.QueryValueEx(key, REGISTRY_APP_NAME)
                    return True
                except OSError:
                    winreg.QueryValueEx(key, LEGACY_APP_NAME_COMPACT)
                    return True
        except OSError:
            return False
    return False


def set_launch_at_login(enabled: bool, app_path: Path | None = None) -> None:
    if sys.platform == "darwin":
        _set_macos_launch_at_login(enabled, app_path)
    elif sys.platform == "win32":
        _set_windows_launch_at_login(enabled, app_path)


def _set_macos_launch_at_login(enabled: bool, app_path: Path | None) -> None:
    current = _plist_path(LAUNCH_AGENT_ID)
    legacy = _plist_path(LEGACY_BUNDLE_ID)
    if enabled:
        resolved = app_path or _macos_app_path()
        if resolved is None:
            return
        current.parent.mkdir(parents=True, exist_ok=True)
        plist = {
            "Label": LAUNCH_AGENT_ID,
            "ProgramArguments": ["open", "-a", str(resolved)],
            "RunAtLoad": True,
        }
        current.write_bytes(plistlib.dumps(plist))
        if legacy.exists():
            legacy.unlink()
    else:
        if current.exists():
            current.unlink()
        if legacy.exists():
            legacy.unlink()


def _set_windows_launch_at_login(enabled: bool, app_path: Path | None) -> None:
    import winreg

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE
    ) as key:
        if enabled:
            exe = app_path or Path(sys.executable)
            winreg.SetValueEx(key, REGISTRY_APP_NAME, 0, winreg.REG_SZ, str(exe))
            try:
                winreg.DeleteValue(key, LEGACY_APP_NAME_COMPACT)
            except OSError:
                pass
        else:
            for name in (REGISTRY_APP_NAME, LEGACY_APP_NAME_COMPACT):
                try:
                    winreg.DeleteValue(key, name)
                except OSError:
                    pass


def open_full_disk_access_settings() -> None:
    if sys.platform != "darwin":
        return
    subprocess.run(
        ["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles"],
        check=False,
        timeout=5,
    )
