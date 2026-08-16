#!/usr/bin/env python3
"""Build a per-user NSIS installer around the PyInstaller onedir output."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from notification_watcher.version import __version__


def _makensis() -> str:
    found = shutil.which("makensis")
    if found:
        return found
    for candidate in (
        Path(r"C:\Program Files (x86)\NSIS\makensis.exe"),
        Path(r"C:\Program Files\NSIS\makensis.exe"),
    ):
        if candidate.is_file():
            return str(candidate)
    raise RuntimeError("makensis not found. Install NSIS (choco install nsis).")


def main() -> int:
    dist_dir = ROOT / "dist" / "TradeDeskyWatcher"
    if not dist_dir.is_dir():
        raise SystemExit("Build first: pyinstaller notification_watcher.spec")
    nsis = _makensis()
    script = ROOT / "installer" / "windows.nsi"
    (ROOT / "dist").mkdir(parents=True, exist_ok=True)
    subprocess.run([nsis, f"/DVERSION={__version__}", str(script)], check=True, cwd=ROOT)
    print(f"Created dist/TradeDeskyWatcher-{__version__}-setup.exe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
