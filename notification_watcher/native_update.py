"""Sparkle (macOS) and WinSparkle (Windows) wrappers for bundled builds."""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

from notification_watcher.config import get_app_logger
from notification_watcher.product import (
    APP_NAME,
    APPCAST_URL,
    COMPANY_NAME,
    SPARKLE_ED_PUBLIC_KEY,
)
from notification_watcher.version import __version__

logger = get_app_logger()
UPDATE_CHECK_INTERVAL_SECONDS = 86_400


class NativeUpdater:
    def __init__(self) -> None:
        self._impl: _MacSparkle | _WinSparkle | None = None
        if sys.platform == "darwin":
            impl = _MacSparkle()
            self._impl = impl if impl.available else None
        elif sys.platform == "win32":
            impl = _WinSparkle()
            self._impl = impl if impl.available else None

    @property
    def available(self) -> bool:
        return self._impl is not None

    def start(self, *, automatic: bool, on_shutdown: Callable[[], None] | None = None) -> bool:
        if self._impl is None:
            return False
        return self._impl.start(automatic=automatic, on_shutdown=on_shutdown)

    def check_now(self) -> bool:
        if self._impl is None:
            return False
        return self._impl.check_now()

    def cleanup(self) -> None:
        if self._impl is not None:
            self._impl.cleanup()


def start_native_or_github(
    *,
    automatic: bool,
    on_shutdown: Callable[[], None] | None = None,
) -> NativeUpdater:
    native = NativeUpdater()
    if native.start(automatic=automatic, on_shutdown=on_shutdown):
        logger.info("Native updater started")
    return native


class _MacSparkle:
    def __init__(self) -> None:
        self.available = False
        self._controller = None
        self._controller_cls = None
        framework = _sparkle_framework_path()
        if framework is None:
            return
        try:
            import objc

            objc.loadBundle("Sparkle", module_globals=globals(), bundle_path=str(framework))
            self._controller_cls = objc.lookUpClass("SPUStandardUpdaterController")
            self.available = self._controller_cls is not None
        except Exception as exc:
            logger.warning("Could not load Sparkle.framework: %s", exc)

    def start(self, *, automatic: bool, on_shutdown: Callable[[], None] | None = None) -> bool:
        if not self.available or self._controller_cls is None:
            return False
        try:
            self._controller = self._controller_cls.alloc().initWithStartingUpdater_updaterDelegate_userDriverDelegate_(
                True, None, None
            )
            updater = self._controller.updater()
            updater.setAutomaticallyChecksForUpdates_(automatic)
            updater.setUpdateCheckInterval_(UPDATE_CHECK_INTERVAL_SECONDS)
            try:
                from Foundation import NSURL

                feed = NSURL.URLWithString_(APPCAST_URL)
                if feed is not None:
                    updater.setFeedURL_(feed)
            except Exception:
                pass
            return True
        except Exception as exc:
            logger.warning("Could not start Sparkle: %s", exc)
            self._controller = None
            return False

    def check_now(self) -> bool:
        if self._controller is None:
            return False
        self._controller.checkForUpdates_(None)
        return True

    def cleanup(self) -> None:
        self._controller = None


class _WinSparkle:
    def __init__(self) -> None:
        self.available = False
        self._dll = None
        self._callbacks: list[object] = []
        path = _winsparkle_dll_path()
        if path is None:
            return
        try:
            import ctypes

            self._dll = ctypes.WinDLL(str(path))
            self._configure_prototypes()
            self.available = True
        except Exception as exc:
            logger.warning("Could not load WinSparkle.dll: %s", exc)

    def _configure_prototypes(self) -> None:
        import ctypes

        dll = self._dll
        dll.win_sparkle_set_appcast_url.argtypes = [ctypes.c_char_p]
        dll.win_sparkle_set_eddsa_public_key.argtypes = [ctypes.c_char_p]
        dll.win_sparkle_set_eddsa_public_key.restype = ctypes.c_int
        dll.win_sparkle_set_app_details.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_wchar_p,
            ctypes.c_wchar_p,
        ]
        dll.win_sparkle_set_automatic_check_for_updates.argtypes = [ctypes.c_int]
        dll.win_sparkle_set_update_check_interval.argtypes = [ctypes.c_int]
        can_shutdown_fn = ctypes.CFUNCTYPE(ctypes.c_int)
        shutdown_fn = ctypes.CFUNCTYPE(None)
        dll.win_sparkle_set_can_shutdown_callback.argtypes = [can_shutdown_fn]
        dll.win_sparkle_set_shutdown_request_callback.argtypes = [shutdown_fn]
        self._can_shutdown_fn = can_shutdown_fn
        self._shutdown_fn = shutdown_fn

    def start(self, *, automatic: bool, on_shutdown: Callable[[], None] | None = None) -> bool:
        if self._dll is None:
            return False
        dll = self._dll
        dll.win_sparkle_set_appcast_url(APPCAST_URL.encode("utf-8"))
        if dll.win_sparkle_set_eddsa_public_key(SPARKLE_ED_PUBLIC_KEY.encode("utf-8")) != 1:
            logger.warning("WinSparkle rejected EdDSA public key")
            return False
        dll.win_sparkle_set_app_details(COMPANY_NAME, APP_NAME, __version__)
        dll.win_sparkle_set_automatic_check_for_updates(1 if automatic else 0)
        dll.win_sparkle_set_update_check_interval(UPDATE_CHECK_INTERVAL_SECONDS)

        can_shutdown = self._can_shutdown_fn(lambda: 1)
        self._callbacks.append(can_shutdown)
        dll.win_sparkle_set_can_shutdown_callback(can_shutdown)

        if on_shutdown is not None:
            shutdown = self._shutdown_fn(on_shutdown)
            self._callbacks.append(shutdown)
            dll.win_sparkle_set_shutdown_request_callback(shutdown)

        dll.win_sparkle_init()
        return True

    def check_now(self) -> bool:
        if self._dll is None:
            return False
        self._dll.win_sparkle_check_update_with_ui()
        return True

    def cleanup(self) -> None:
        if self._dll is not None:
            self._dll.win_sparkle_cleanup()
            self._dll = None
        self._callbacks.clear()


def _sparkle_framework_path() -> Path | None:
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        bundled = exe.parent.parent / "Frameworks" / "Sparkle.framework"
        if bundled.exists():
            return bundled
    vendor = Path(__file__).resolve().parents[1] / "vendor" / "Sparkle.framework"
    return vendor if vendor.exists() else None


def _winsparkle_dll_path() -> Path | None:
    name = "WinSparkle.dll"
    if getattr(sys, "frozen", False):
        bundled = Path(sys.executable).resolve().parent / name
        if bundled.exists():
            return bundled
    vendor = Path(__file__).resolve().parents[1] / "vendor" / name
    return vendor if vendor.exists() else None
