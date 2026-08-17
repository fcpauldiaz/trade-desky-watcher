import sqlite3
from pathlib import Path

from notification_watcher.macos import (
    can_read_notification_db,
    is_notification_db_access_error,
    sqlite_readonly_uri,
)


def test_sqlite_readonly_uri_uses_file_uri():
    uri = sqlite_readonly_uri(Path("/tmp/notifications.db"))
    assert uri.startswith("file://")
    assert "mode=ro" in uri
    assert "immutable=1" in uri


def test_can_read_notification_db(tmp_path: Path):
    missing = tmp_path / "missing.db"
    assert can_read_notification_db(None) is False
    assert can_read_notification_db(missing) is False
    db_path = tmp_path / "ok.db"
    sqlite3.connect(str(db_path)).close()
    assert can_read_notification_db(db_path) is True


def test_is_notification_db_access_error():
    assert is_notification_db_access_error(sqlite3.OperationalError("unable to open database file"))
    assert is_notification_db_access_error(PermissionError("denied"))
    assert is_notification_db_access_error(FileNotFoundError("gone"))
    assert not is_notification_db_access_error(sqlite3.OperationalError("no such table: record"))
    assert not is_notification_db_access_error(ValueError("other"))
