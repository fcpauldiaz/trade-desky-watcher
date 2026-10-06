import inspect
import sys
import types
from unittest.mock import MagicMock

from notification_watcher.config import default_config


def _fake_pystray_module() -> types.ModuleType:
    mod = types.ModuleType("pystray")

    class Menu:
        def __init__(self, *items: object) -> None:
            self.items = items

    mod.Menu = Menu
    mod.MenuItem = MagicMock()
    mod.Menu.SEPARATOR = object()
    mod.Icon = MagicMock()
    return mod


def test_build_menu_returns_pystray_menu() -> None:
    sys.modules["pystray"] = _fake_pystray_module()
    from windows_app import WindowsNotificationApp

    app = WindowsNotificationApp.__new__(WindowsNotificationApp)
    app._config = default_config()
    app._status = "Watching"
    app._recent = []
    app._poll_seconds = 0.5
    menu = app._build_menu()
    assert type(menu).__name__ == "Menu"
    assert hasattr(menu, "items")
    assert not callable(menu)

    tray_src = inspect.getsource(WindowsNotificationApp._build_tray)
    assert "menu=self._build_menu()" in tray_src
