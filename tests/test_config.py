import json
from pathlib import Path

import pytest

from notification_watcher.config import default_config, get_config_dir, load_config, save_config
from notification_watcher.types import AppConfig


def test_default_config():
    cfg = default_config()
    assert cfg.auth_token is None
    assert cfg.poll_seconds == 0.5
    assert cfg.is_signed_in() is False


def test_config_round_trip(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "notification_watcher.config.get_config_path",
        lambda: tmp_path / "config.json",
    )
    cfg = AppConfig(
        poll_seconds=0.1,
        discord_only=True,
        app_filter="%slack%",
        launch_at_login=True,
        auth_token="secret-token",
        account_email="user@example.com",
        ingest_url="https://api.example.com/v1/ingest",
        platform_url="https://app.example.com",
    )
    save_config(cfg)
    loaded = load_config()
    assert loaded.poll_seconds == 0.1
    assert loaded.discord_only is True
    assert loaded.app_filter == "%slack%"
    assert loaded.launch_at_login is True
    assert loaded.auth_token == "secret-token"
    assert loaded.account_email == "user@example.com"
    assert loaded.ingest_url == "https://api.example.com/v1/ingest"
    assert loaded.platform_url == "https://app.example.com"


def test_effective_app_filter():
    cfg = AppConfig(discord_only=True, app_filter="%slack%")
    assert cfg.effective_app_filter() == "%discord%"
    cfg.discord_only = False
    assert cfg.effective_app_filter() == "%slack%"


def test_load_config_invalid_json(tmp_path: Path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr("notification_watcher.config.get_config_path", lambda: path)
    assert load_config() == default_config()


def test_migrates_legacy_config_dir(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("notification_watcher.config.sys.platform", "darwin")
    monkeypatch.setattr("notification_watcher.config.Path.home", lambda: tmp_path)
    support = tmp_path / "Library" / "Application Support"
    legacy = support / "Notification Watcher"
    legacy.mkdir(parents=True)
    (legacy / "config.json").write_text("{}", encoding="utf-8")

    moved = get_config_dir()
    assert moved.name == "Trade Desky Watcher"
    assert (moved / "config.json").exists()
    assert not legacy.exists()
