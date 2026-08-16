#!/usr/bin/env python3
"""Download Sparkle.framework and WinSparkle.dll into vendor/ for app builds."""

from __future__ import annotations

import argparse
import shutil
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from notification_watcher.product import SPARKLE_VERSION, WINSPARKLE_VERSION

VENDOR = ROOT / "vendor"
USER_AGENT = "TradeDeskyWatcher-build/1.0"


def _download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def fetch_sparkle() -> Path:
    url = (
        "https://github.com/sparkle-project/Sparkle/releases/download/"
        f"{SPARKLE_VERSION}/Sparkle-{SPARKLE_VERSION}.tar.xz"
    )
    archive = VENDOR / f"Sparkle-{SPARKLE_VERSION}.tar.xz"
    _download(url, archive)
    extract = VENDOR / "sparkle-extract"
    if extract.exists():
        shutil.rmtree(extract)
    extract.mkdir(parents=True)
    with tarfile.open(archive) as tar:
        try:
            tar.extractall(extract, filter="data")
        except TypeError:
            tar.extractall(extract)
    framework = next(extract.rglob("Sparkle.framework"))
    target = VENDOR / "Sparkle.framework"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(framework, target, symlinks=True)
    print(f"Sparkle.framework -> {target}")
    return target


def fetch_winsparkle() -> Path:
    url = (
        "https://github.com/vslavik/winsparkle/releases/download/"
        f"v{WINSPARKLE_VERSION}/WinSparkle-{WINSPARKLE_VERSION}.zip"
    )
    archive = VENDOR / f"WinSparkle-{WINSPARKLE_VERSION}.zip"
    _download(url, archive)
    extract = VENDOR / "winsparkle-extract"
    if extract.exists():
        shutil.rmtree(extract)
    with zipfile.ZipFile(archive) as zipped:
        zipped.extractall(extract)
    dlls = sorted(extract.rglob("WinSparkle.dll"))
    preferred = [path for path in dlls if "x64" in path.as_posix().lower() or "x86_64" in path.as_posix().lower()]
    dll = (preferred or dlls)[0]
    target = VENDOR / "WinSparkle.dll"
    shutil.copy2(dll, target)
    print(f"WinSparkle.dll ({dll}) -> {target}")
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sparkle", action="store_true")
    parser.add_argument("--winsparkle", action="store_true")
    args = parser.parse_args()
    VENDOR.mkdir(parents=True, exist_ok=True)
    if not args.sparkle and not args.winsparkle:
        args.sparkle = sys.platform == "darwin"
        args.winsparkle = sys.platform == "win32"
    if args.sparkle:
        fetch_sparkle()
    if args.winsparkle:
        fetch_winsparkle()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
