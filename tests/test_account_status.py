import pytest

from notification_watcher.account_status import format_status_line
from notification_watcher.types import AppConfig


@pytest.mark.parametrize(
    ("base", "signed_in", "email", "expected"),
    [
        ("Watching", True, "user@example.com", "Watching · signed in as user@example.com"),
        ("Watching", False, None, "Watching (not signed in)"),
        ("Waiting for Full Disk Access", True, "user@example.com", "Waiting for Full Disk Access · signed in as user@example.com"),
    ],
)
def test_format_status_line(base, signed_in, email, expected):
    config = AppConfig(
        auth_token="token" if signed_in else None,
        account_email=email,
    )
    assert format_status_line(base, config) == expected
