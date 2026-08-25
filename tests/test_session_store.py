import json
from pathlib import Path

from notification_watcher.config import load_config, save_config
from notification_watcher.session_store import (
    SESSION_FILENAME,
    clear_stored_session,
    load_stored_session,
    save_stored_session,
    session_from_config,
    session_path,
)
from notification_watcher.types import AppConfig


def test_session_round_trip(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("notification_watcher.config.get_config_dir", lambda: tmp_path)

    save_stored_session(
        session_from_config(
            "device-token",
            "user@example.com",
            "https://trade-receiver.chapilabs.com/v1/ingest",
        )
    )

    loaded = load_stored_session()
    assert loaded is not None
    assert loaded.auth_token == "device-token"
    assert loaded.account_email == "user@example.com"
    assert loaded.ingest_url == "https://trade-receiver.chapilabs.com/v1/ingest"


def test_load_config_prefers_session_file(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("notification_watcher.config.get_config_dir", lambda: tmp_path)

    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "poll_seconds": 0.5,
                "auth_token": "old-config-token",
                "account_email": "old@example.com",
            }
        ),
        encoding="utf-8",
    )
    save_stored_session(
        session_from_config(
            "session-token",
            "new@example.com",
            "https://trade-receiver.chapilabs.com/v1/ingest",
        )
    )

    loaded = load_config()
    assert loaded.auth_token == "session-token"
    assert loaded.account_email == "new@example.com"


def test_migrate_legacy_auth_from_config_json(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("notification_watcher.config.get_config_dir", lambda: tmp_path)

    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "auth_token": "legacy-token",
                "account_email": "legacy@example.com",
                "ingest_url": "https://trade-receiver.chapilabs.com/v1/ingest",
            }
        ),
        encoding="utf-8",
    )

    migrated = load_stored_session()
    assert migrated is not None
    assert migrated.auth_token == "legacy-token"
    assert (tmp_path / SESSION_FILENAME).exists()


def test_save_config_writes_session_and_clears_on_sign_out(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("notification_watcher.config.get_config_dir", lambda: tmp_path)

    cfg = AppConfig(
        auth_token="device-token",
        account_email="user@example.com",
    )
    save_config(cfg)
    assert session_path().exists()

    cfg.auth_token = None
    cfg.account_email = None
    save_config(cfg)
    assert not session_path().exists()


def test_clear_stored_session(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("notification_watcher.config.get_config_dir", lambda: tmp_path)
    save_stored_session(session_from_config("token", "user@example.com", "https://example.com/v1/ingest"))
    clear_stored_session()
    assert not session_path().exists()
