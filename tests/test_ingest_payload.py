import ingest_sender


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
