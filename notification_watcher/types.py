from dataclasses import dataclass, field
from typing import Callable

from notification_watcher.product import DEFAULT_INGEST_URL, DEFAULT_PLATFORM_URL

DeliveredDate = float | None
Notification = tuple[str, str, str, str, int | None, DeliveredDate]
OnNotification = Callable[[str, str, str, str, DeliveredDate], None]
OnError = Callable[[Exception], None]

DISCORD_APP_FILTER = "%discord%"


@dataclass
class AppConfig:
    poll_seconds: float = 0.5
    launch_at_login: bool = False
    check_for_updates: bool = True
    platform_url: str = DEFAULT_PLATFORM_URL
    ingest_url: str = DEFAULT_INGEST_URL
    auth_token: str | None = None
    account_email: str | None = None

    def effective_app_filter(self) -> str:
        return DISCORD_APP_FILTER

    def is_signed_in(self) -> bool:
        return bool(self.auth_token)
