import json
import logging
import os
import shutil
import sys
from pathlib import Path

from notification_watcher.product import (
    APP_NAME,
    DEFAULT_INGEST_URL,
    DEFAULT_PLATFORM_URL,
    LEGACY_APP_NAME,
    resolved_service_url,
)
from notification_watcher.session_store import (
    clear_stored_session,
    load_stored_session,
    save_stored_session,
    session_from_config,
)
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
        config = default_config()
    else:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            config = default_config()
        else:
            if not isinstance(data, dict):
                config = default_config()
            else:
                poll = data.get("poll_seconds")
                poll_seconds = float(poll) if isinstance(poll, (int, float)) and poll > 0 else 0.5
                platform_url = data.get("platform_url")
                ingest_url = data.get("ingest_url")
                auth_token = data.get("auth_token")
                account_email = data.get("account_email")
                config = AppConfig(
                    poll_seconds=poll_seconds,
                    launch_at_login=bool(data.get("launch_at_login", False)),
                    check_for_updates=bool(data.get("check_for_updates", True)),
                    platform_url=resolved_service_url(platform_url, DEFAULT_PLATFORM_URL),
                    ingest_url=resolved_service_url(ingest_url, DEFAULT_INGEST_URL),
                    auth_token=auth_token if isinstance(auth_token, str) and auth_token else None,
                    account_email=account_email if isinstance(account_email, str) and account_email else None,
                )
    session = load_stored_session()
    if session is not None:
        config.auth_token = session.auth_token
        config.account_email = session.account_email
        config.ingest_url = resolved_service_url(session.ingest_url, DEFAULT_INGEST_URL)
    return config


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def save_config(config: AppConfig) -> None:
    path = get_config_path()
    if config.auth_token:
        save_stored_session(session_from_config(config.auth_token, config.account_email, config.ingest_url))
    else:
        clear_stored_session()
    data = {
        "poll_seconds": config.poll_seconds,
        "launch_at_login": config.launch_at_login,
        "check_for_updates": config.check_for_updates,
        "platform_url": config.platform_url,
        "ingest_url": config.ingest_url,
        "auth_token": config.auth_token,
        "account_email": config.account_email,
    }
    _atomic_write_text(path, json.dumps(data, indent=2))
