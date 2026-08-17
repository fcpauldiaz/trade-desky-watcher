import ingest_sender
from notification_watcher.types import AppConfig


class _ImmediateThread:
    def __init__(self, target, daemon: bool = True) -> None:
        self._target = target

    def start(self) -> None:
        self._target()


def test_only_discord_notifications_are_forwarded():
    assert ingest_sender._should_forward("com.hnc.Discord") is True
    assert ingest_sender._should_forward("com.apple.MobileSMS") is False


def test_build_generic_payload():
    payload = ingest_sender.build_generic_payload(
        "com.app", "Title", "Sub", "Body", None
    )
    assert payload["app_id"] == "com.app"
    assert payload["title"] == "Title"
    assert "platform" in payload


def test_unsigned_discord_notifications_flush_after_sign_in(monkeypatch) -> None:
    ingest_sender.clear_pending()
    sent: list[str] = []

    def capture(
        url: str, payload_bytes: bytes, payload_json: str, auth_token: str
    ) -> bool:
        sent.append(auth_token)
        return True

    monkeypatch.setattr(ingest_sender.threading, "Thread", _ImmediateThread)
    monkeypatch.setattr(ingest_sender, "_post_one", capture)

    unsigned = AppConfig(auth_token=None)
    ingest_sender.send_notification(
        "com.hnc.Discord", "Alerts", "", "BTO SPY", 1.0, unsigned
    )
    ingest_sender.send_notification(
        "com.apple.mail", "Hi", "", "not a trade", 2.0, unsigned
    )
    assert ingest_sender.pending_count() == 1
    assert sent == []

    signed = AppConfig(
        auth_token="device-token",
        ingest_url="https://trade-receiver.chapilabs.com/v1/ingest",
    )
    flushed = ingest_sender.flush_pending(signed)
    assert flushed == 1
    assert ingest_sender.pending_count() == 0
    assert sent == ["device-token"]
    ingest_sender.clear_pending()
