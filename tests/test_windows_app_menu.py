import pystray

from notification_watcher.config import default_config
from windows_app import WindowsNotificationApp


def test_build_menu_returns_pystray_menu() -> None:
    app = WindowsNotificationApp.__new__(WindowsNotificationApp)
    app._config = default_config()
    app._status = "Watching"
    app._recent = []
    app._poll_seconds = 0.5
    menu = app._build_menu()
    assert isinstance(menu, pystray.Menu)
