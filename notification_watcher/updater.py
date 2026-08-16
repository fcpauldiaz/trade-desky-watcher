"""Check GitHub Releases and install updates for bundled macOS/Windows builds."""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from notification_watcher.config import get_app_logger, get_config_dir
from notification_watcher.product import APP_NAME, APP_NAME_COMPACT, GITHUB_REPO, LEGACY_APP_NAME, LEGACY_APP_NAME_COMPACT
from notification_watcher.version import __version__

USER_AGENT = f"{APP_NAME_COMPACT}/{__version__}"
UPDATE_CHECK_INTERVAL_SECONDS = 86_400
STARTUP_CHECK_DELAY_SECONDS = 60

_VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")
_MAC_DMG_RE = re.compile(rf"{APP_NAME_COMPACT}-[\d.]+\.dmg$", re.I)
_MAC_DMG_LEGACY_RE = re.compile(rf"{LEGACY_APP_NAME_COMPACT}-[\d.]+\.dmg$", re.I)
_WIN_ZIP_RE = re.compile(rf"{APP_NAME_COMPACT}-[\d.]+-win\.zip$", re.I)
_WIN_ZIP_LEGACY_RE = re.compile(rf"{LEGACY_APP_NAME_COMPACT}-[\d.]+-win\.zip$", re.I)

logger = get_app_logger()


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    tag: str
    download_url: str
    asset_name: str
    release_notes: str


@dataclass(frozen=True)
class UpdateCheckResult:
    current_version: str
    latest: ReleaseInfo | None
    update_available: bool
    error: str | None = None


def parse_version(value: str) -> tuple[int, int, int] | None:
    match = _VERSION_RE.search(value.lstrip("vV"))
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def is_newer_version(latest: str, current: str) -> bool:
    latest_parts = parse_version(latest)
    current_parts = parse_version(current)
    if latest_parts is None or current_parts is None:
        return False
    return latest_parts > current_parts


def is_bundled_app() -> bool:
    if getattr(sys, "frozen", False):
        return True
    exe = Path(sys.executable).resolve()
    if sys.platform == "darwin":
        return ".app" in exe.as_posix()
    return exe.suffix.lower() == ".exe"


def get_mac_app_bundle() -> Path | None:
    exe = Path(sys.executable).resolve()
    for parent in exe.parents:
        if parent.suffix == ".app":
            return parent
    return None


def get_windows_install_dir() -> Path | None:
    if not getattr(sys, "frozen", False):
        return None
    return Path(sys.executable).resolve().parent


def _state_path() -> Path:
    return get_config_dir() / "update_state.json"


def _read_last_check() -> float:
    path = _state_path()
    if not path.exists():
        return 0.0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0.0
    value = data.get("last_check_epoch")
    return float(value) if isinstance(value, (int, float)) else 0.0


def _write_last_check(epoch: float | None = None) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"last_check_epoch": epoch if epoch is not None else time.time()}, indent=2),
        encoding="utf-8",
    )


def _github_request(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _pick_asset(assets: list[dict], pattern: re.Pattern[str]) -> dict | None:
    for asset in assets:
        name = asset.get("name", "")
        url = asset.get("browser_download_url", "")
        if pattern.search(name) and url:
            return asset
    return None


def fetch_latest_release() -> ReleaseInfo:
    data = _github_request(f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest")
    tag = str(data.get("tag_name", ""))
    version = tag.lstrip("vV")
    assets = data.get("assets", [])
    if not isinstance(assets, list):
        assets = []

    if sys.platform == "darwin":
        asset = _pick_asset(assets, _MAC_DMG_RE) or _pick_asset(assets, _MAC_DMG_LEGACY_RE)
        if asset is None:
            raise RuntimeError("No macOS DMG found on latest release")
    elif sys.platform == "win32":
        asset = _pick_asset(assets, _WIN_ZIP_RE) or _pick_asset(assets, _WIN_ZIP_LEGACY_RE)
        if asset is None:
            raise RuntimeError("No Windows zip found on latest release")
    else:
        raise RuntimeError(f"Auto-update is not supported on {sys.platform}")

    notes = str(data.get("body") or "").strip()
    return ReleaseInfo(
        version=version,
        tag=tag,
        download_url=str(asset["browser_download_url"]),
        asset_name=str(asset["name"]),
        release_notes=notes,
    )


def check_for_updates(*, force: bool = False) -> UpdateCheckResult:
    if not force:
        last = _read_last_check()
        if time.time() - last < UPDATE_CHECK_INTERVAL_SECONDS:
            return UpdateCheckResult(
                current_version=__version__,
                latest=None,
                update_available=False,
            )

    try:
        latest = fetch_latest_release()
        _write_last_check()
        return UpdateCheckResult(
            current_version=__version__,
            latest=latest,
            update_available=is_newer_version(latest.version, __version__),
        )
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, RuntimeError, json.JSONDecodeError) as exc:
        logger.warning("Update check failed: %s", exc)
        return UpdateCheckResult(
            current_version=__version__,
            latest=None,
            update_available=False,
            error=str(exc),
        )


def _download_file(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def _find_app_in_dir(root: Path) -> Path | None:
    for candidate in root.rglob("*.app"):
        if candidate.is_dir():
            return candidate
    return None


def install_macos_update(dmg_path: Path) -> str:
    app_bundle = get_mac_app_bundle()
    if app_bundle is None:
        raise RuntimeError("Could not locate the running app bundle")

    mount_point = Path(tempfile.mkdtemp(prefix="nw-update-mount-"))
    try:
        subprocess.run(
            ["hdiutil", "attach", str(dmg_path), "-nobrowse", "-quiet", "-mountpoint", str(mount_point)],
            check=True,
            timeout=120,
        )
        source_app = _find_app_in_dir(mount_point)
        if source_app is None:
            raise RuntimeError(f"DMG does not contain {APP_NAME}.app")

        target = Path("/Applications") / source_app.name
        if target.exists():
            backup = target.with_name(f"{target.name}.backup")
            if backup.exists():
                shutil.rmtree(backup)
            shutil.move(str(target), str(backup))
        shutil.copytree(source_app, target)
        leftover = Path("/Applications") / f"{LEGACY_APP_NAME}.app"
        if leftover.exists() and leftover != target:
            shutil.rmtree(leftover, ignore_errors=True)
        return str(target)
    finally:
        subprocess.run(["hdiutil", "detach", str(mount_point), "-quiet"], check=False, timeout=60)
        shutil.rmtree(mount_point, ignore_errors=True)


def _write_windows_updater_script(
    source_dir: Path,
    install_dir: Path,
    exe_name: str,
) -> Path:
    script_dir = get_config_dir() / "pending_update"
    if script_dir.exists():
        shutil.rmtree(script_dir, ignore_errors=True)
    script_dir.mkdir(parents=True, exist_ok=True)

    staged_dir = script_dir / "payload"
    if staged_dir.exists():
        shutil.rmtree(staged_dir)
    shutil.copytree(source_dir, staged_dir)

    script_path = script_dir / "apply_update.bat"
    script_path.write_text(
        "\r\n".join(
            [
                "@echo off",
                "setlocal",
                f'set "TARGET={install_dir}"',
                f'set "SOURCE={staged_dir}"',
                f'set "EXE={exe_name}"',
                ":wait",
                'tasklist /FI "IMAGENAME eq %EXE%" 2>nul | find /I "%EXE%" >nul',
                "if not errorlevel 1 (",
                "  timeout /t 1 /nobreak >nul",
                "  goto wait",
                ")",
                'xcopy "%SOURCE%\\*" "%TARGET%\\" /E /Y /Q >nul',
                'start "" "%TARGET%\\%EXE%"',
                f'rmdir /S /Q "{script_dir}"',
                "endlocal",
            ]
        ),
        encoding="utf-8",
    )
    return script_path


def install_windows_update(zip_path: Path) -> Path:
    install_dir = get_windows_install_dir()
    if install_dir is None:
        raise RuntimeError("Could not locate the Windows install directory")

    extract_dir = Path(tempfile.mkdtemp(prefix="nw-update-"))
    try:
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(extract_dir)
        payload_dir = extract_dir / APP_NAME_COMPACT
        if not payload_dir.is_dir():
            payload_dir = extract_dir / LEGACY_APP_NAME_COMPACT
        if not payload_dir.is_dir():
            children = [p for p in extract_dir.iterdir() if p.is_dir()]
            if len(children) == 1:
                payload_dir = children[0]
            else:
                raise RuntimeError("Windows update zip has unexpected layout")
        return _write_windows_updater_script(payload_dir, install_dir, Path(sys.executable).name)
    finally:
        shutil.rmtree(extract_dir, ignore_errors=True)


def download_and_install(release: ReleaseInfo) -> str:
    suffix = ".dmg" if sys.platform == "darwin" else ".zip"
    with tempfile.TemporaryDirectory(prefix="nw-update-") as tmp:
        archive = Path(tmp) / f"update{suffix}"
        _download_file(release.download_url, archive)
        if sys.platform == "darwin":
            return install_macos_update(archive)
        script = install_windows_update(archive)
        return str(script)


def release_page_url() -> str:
    return f"https://github.com/{GITHUB_REPO}/releases/latest"


def schedule_background_checks(
    on_update_available: Callable[[UpdateCheckResult], None],
    *,
    enabled: bool = True,
) -> None:
    if not enabled:
        return

    def worker() -> None:
        time.sleep(STARTUP_CHECK_DELAY_SECONDS)
        result = check_for_updates()
        if result.update_available and result.latest is not None:
            on_update_available(result)

        while True:
            time.sleep(UPDATE_CHECK_INTERVAL_SECONDS)
            result = check_for_updates(force=True)
            if result.update_available and result.latest is not None:
                on_update_available(result)

    threading.Thread(target=worker, daemon=True, name="update-checker").start()
