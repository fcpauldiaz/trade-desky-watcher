# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

block_cipher = None
root = Path(SPECPATH)
winsparkle = root / "vendor" / "WinSparkle.dll"
binaries = [(str(winsparkle), ".")] if winsparkle.is_file() else []

a = Analysis(
    ["windows_app.py"],
    pathex=[str(root)],
    binaries=binaries,
    datas=[(str(root / "assets" / "icon.ico"), "assets")],
    hiddenimports=[
        "pystray",
        "PIL",
        "PIL.Image",
        "PIL.ImageDraw",
        "notification_watcher.updater",
        "notification_watcher.native_update",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TradeDeskyWatcher",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(root / "assets" / "icon.ico"),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="TradeDeskyWatcher",
)
