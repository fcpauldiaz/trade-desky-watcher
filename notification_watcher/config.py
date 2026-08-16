import json
import logging
import os
import shutil
import sys
from pathlib import Path

from notification_watcher.product import APP_NAME, DEFAULT_INGEST_URL, DEFAULT_PLATFORM_URL, LEGACY_APP_NAME
from notification_watcher.types import AppConfig

CONFIG_FILENAME = "config.json"
LOG_FILENAME = "notification_watcher.log"

_APP_LOGGER: logging.Logger | None = None


def get_config_dir() -> Path:
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("APPDATA", Path.home()))
    current = base / APP_NAME
    legacy = base / LEGACY_APP_NAME
    if not current.exists() and legacy.exists():
        try:
            shutil.move(str(legacy), str(current))
        except OSError:
            return legacy
    return current


def get_config_path() -> Path:
    return get_config_dir() / CONFIG_FILENAME


def get_log_path() -> Path:
    return get_config_dir() / LOG_FILENAME


def get_app_logger() -> logging.Logger:
    global _APP_LOGGER
    if _APP_LOGGER is not None:
        return _APP_LOGGER
    log_path = get_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("notification_watcher")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(fh)
    _APP_LOGGER = logger
    return logger


def default_config() -> AppConfig:
    return AppConfig()


def load_config() -> AppConfig:
    path = get_config_path()
    if not path.exists():
        return default_config()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_config()
    if not isinstance(data, dict):
        return default_config()
    poll = data.get("poll_seconds")
    poll_seconds = float(poll) if isinstance(poll, (int, float)) and poll > 0 else 0.5
    app_filter = data.get("app_filter")
    platform_url = data.get("platform_url")
    ingest_url = data.get("ingest_url")
    auth_token = data.get("auth_token")
    account_email = data.get("account_email")
    return AppConfig(
        poll_seconds=poll_seconds,
        discord_only=bool(data.get("discord_only", False)),
        app_filter=app_filter if isinstance(app_filter, str) and app_filter else None,
        launch_at_login=bool(data.get("launch_at_login", False)),
        check_for_updates=bool(data.get("check_for_updates", True)),
        platform_url=platform_url if isinstance(platform_url, str) and platform_url else DEFAULT_PLATFORM_URL,
        ingest_url=ingest_url if isinstance(ingest_url, str) and ingest_url else DEFAULT_INGEST_URL,
        auth_token=auth_token if isinstance(auth_token, str) and auth_token else None,
        account_email=account_email if isinstance(account_email, str) and account_email else None,
    )


def save_config(config: AppConfig) -> None:
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "poll_seconds": config.poll_seconds,
        "discord_only": config.discord_only,
        "app_filter": config.app_filter,
        "launch_at_login": config.launch_at_login,
        "check_for_updates": config.check_for_updates,
        "platform_url": config.platform_url,
        "ingest_url": config.ingest_url,
        "auth_token": config.auth_token,
        "account_email": config.account_email,
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
