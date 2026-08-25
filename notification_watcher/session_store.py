import json
from dataclasses import dataclass
from pathlib import Path

from notification_watcher.product import DEFAULT_INGEST_URL

SESSION_FILENAME = "session.json"
SESSION_VERSION = 1
CONFIG_FILENAME = "config.json"


@dataclass(frozen=True)
class StoredSession:
    auth_token: str
    account_email: str | None
    ingest_url: str


def session_path() -> Path:
    from notification_watcher.config import get_config_dir

    return get_config_dir() / SESSION_FILENAME


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def load_stored_session() -> StoredSession | None:
    path = session_path()
    if path.exists():
        session = _parse_session_file(path)
        if session is not None:
            return session
    return _migrate_legacy_session()


def save_stored_session(session: StoredSession) -> None:
    payload = {
        "version": SESSION_VERSION,
        "auth_token": session.auth_token,
        "account_email": session.account_email,
        "ingest_url": session.ingest_url.rstrip("/"),
    }
    _atomic_write_text(session_path(), json.dumps(payload, indent=2))


def clear_stored_session() -> None:
    path = session_path()
    if path.exists():
        path.unlink()


def session_from_config(auth_token: str, account_email: str | None, ingest_url: str) -> StoredSession:
    return StoredSession(
        auth_token=auth_token,
        account_email=account_email,
        ingest_url=ingest_url.rstrip("/") or DEFAULT_INGEST_URL,
    )


def _parse_session_file(path: Path) -> StoredSession | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    token = data.get("auth_token")
    if not isinstance(token, str) or not token.strip():
        return None
    email = data.get("account_email")
    ingest = data.get("ingest_url")
    ingest_url = ingest.strip() if isinstance(ingest, str) and ingest.strip() else DEFAULT_INGEST_URL
    account_email = email if isinstance(email, str) and email.strip() else None
    return StoredSession(
        auth_token=token.strip(),
        account_email=account_email,
        ingest_url=ingest_url,
    )


def _migrate_legacy_session() -> StoredSession | None:
    from notification_watcher.config import get_config_dir

    config_path = get_config_dir() / CONFIG_FILENAME
    if not config_path.exists():
        return None
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    token = data.get("auth_token") or data.get("api_key")
    if not isinstance(token, str) or not token.strip():
        return None
    email = data.get("account_email")
    ingest = data.get("ingest_url")
    session = StoredSession(
        auth_token=token.strip(),
        account_email=email if isinstance(email, str) and email.strip() else None,
        ingest_url=ingest.strip() if isinstance(ingest, str) and ingest.strip() else DEFAULT_INGEST_URL,
    )
    save_stored_session(session)
    return session
