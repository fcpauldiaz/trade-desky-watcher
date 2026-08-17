import plistlib
import sqlite3
import subprocess
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from notification_watcher.types import DeliveredDate, Notification

MAC_EPOCH_OFFSET = 978307200
PLATFORM_NAME = "macos"


def _notification_db_candidates() -> Iterator[Path]:
    home = Path.home()
    yield home / "Library" / "Group Containers" / "group.com.apple.usernoted" / "db2" / "db"
    result = subprocess.run(
        ["getconf", "DARWIN_USER_DIR"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    if result.returncode == 0 and result.stdout.strip():
        base = Path(result.stdout.strip())
        yield base / "com.apple.notificationcenter" / "db2" / "db"
        yield base / "com.apple.notificationcenter" / "db" / "db"
    yield home / "Library" / "Application Support" / "NotificationCenter" / "db2" / "db"
    yield home / "Library" / "Application Support" / "NotificationCenter" / "db" / "db"
    yield (
        home
        / "Library"
        / "Group Containers"
        / "group.com.apple.UserNotifications"
        / "Library"
        / "UserNotifications"
        / "db2"
        / "db"
    )


def sqlite_readonly_uri(db_path: Path) -> str:
    return f"{db_path.resolve().as_uri()}?mode=ro&immutable=1"


def can_read_notification_db(db_path: Path | None) -> bool:
    if db_path is None or not db_path.exists():
        return False
    try:
        conn = sqlite3.connect(sqlite_readonly_uri(db_path), uri=True)
        try:
            conn.execute("SELECT 1")
        finally:
            conn.close()
    except sqlite3.Error:
        return False
    return True


def is_notification_db_access_error(exc: BaseException) -> bool:
    if isinstance(exc, (PermissionError, FileNotFoundError)):
        return True
    if isinstance(exc, sqlite3.OperationalError):
        msg = str(exc).lower()
        return "unable to open" in msg or "authorization" in msg
    return False


def get_notification_db_path() -> Path | None:
    for candidate in _notification_db_candidates():
        if candidate.exists():
            return candidate
    return next(_notification_db_candidates(), None)


def _to_str(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, list):
        return " ".join(_to_str(x) for x in value)
    return str(value)


def parse_notification_plist(data: bytes) -> dict[str, str]:
    out: dict[str, str] = {"title": "", "subtitle": "", "body": ""}
    try:
        plist = plistlib.loads(data)
    except (plistlib.InvalidFileException, ValueError):
        return out
    req = plist.get("req") if isinstance(plist, dict) else None
    if not isinstance(req, dict):
        return out
    out["title"] = _to_str(req.get("titl") or req.get("title"))
    out["subtitle"] = _to_str(req.get("subt") or req.get("subtitle"))
    out["body"] = _to_str(req.get("body") or req.get("message"))
    return out


def to_unix_timestamp(delivered_date: DeliveredDate) -> float | None:
    if delivered_date is None or delivered_date <= 0:
        return None
    return delivered_date + MAC_EPOCH_OFFSET


def format_delivered_date(delivered_date: DeliveredDate) -> str:
    unix_ts = to_unix_timestamp(delivered_date)
    if unix_ts is None:
        return ""
    return datetime.utcfromtimestamp(unix_ts).strftime("%Y-%m-%d %H:%M:%S UTC")


def iter_notifications(
    db_path: Path,
    app_filter: str | None = None,
    since_date: DeliveredDate = None,
) -> Iterator[Notification]:
    if not db_path.exists():
        raise FileNotFoundError(
            f"Notification Center database not found at {db_path}. "
            "On macOS Tahoe (26) and Sequoia (15) the DB may be in a protected location. "
            "Grant Full Disk Access to Terminal (or this app) in System Settings > Privacy & Security, "
            "or pass the DB path with --db if you know it."
        )
    conn = sqlite3.connect(sqlite_readonly_uri(db_path), uri=True)
    conn.row_factory = sqlite3.Row
    try:
        sql = """
            SELECT
                (SELECT identifier FROM app WHERE app.app_id = record.app_id) AS app_id,
                record.rec_id,
                record.data,
                record.delivered_date,
                record.presented
            FROM record
            WHERE 1=1
        """
        params: list[object] = []
        if app_filter is not None:
            sql += (
                " AND LOWER((SELECT identifier FROM app WHERE app.app_id = record.app_id)) LIKE ?"
            )
            params.append(app_filter.lower())
        if since_date is not None and since_date > 0:
            sql += " AND record.delivered_date > ?"
            params.append(since_date)
        sql += " ORDER BY record.delivered_date DESC"
        cursor = conn.execute(sql, tuple(params))
        for row in cursor:
            app_id = row["app_id"] or ""
            parsed = parse_notification_plist(row["data"])
            yield (
                app_id,
                parsed["title"],
                parsed["subtitle"],
                parsed["body"],
                row["presented"],
                row["delivered_date"],
            )
    finally:
        conn.close()
