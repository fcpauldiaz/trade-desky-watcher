import sqlite3
from pathlib import Path

from notification_watcher.macos import (
    can_read_notification_db,
    connect_notification_db,
    is_notification_db_access_error,
    sqlite_readonly_uri,
)


def test_sqlite_readonly_uri_prefers_wal_reader():
    uri = sqlite_readonly_uri(Path("/tmp/notifications.db"))
    assert uri.startswith("file://")
    assert "mode=ro" in uri
    assert "immutable=1" not in uri


def test_sqlite_readonly_uri_immutable_fallback():
    uri = sqlite_readonly_uri(Path("/tmp/notifications.db"), immutable=True)
    assert "mode=ro" in uri
    assert "immutable=1" in uri


def test_can_read_notification_db(tmp_path: Path):
    missing = tmp_path / "missing.db"
    assert can_read_notification_db(None) is False
    assert can_read_notification_db(missing) is False
    db_path = tmp_path / "ok.db"
    sqlite3.connect(str(db_path)).close()
    assert can_read_notification_db(db_path) is True


def test_connect_sees_uncheckpointed_wal_rows(tmp_path: Path):
    db_path = tmp_path / "notif.db"
    writer = sqlite3.connect(str(db_path))
    writer.execute("PRAGMA journal_mode=WAL")
    writer.execute("CREATE TABLE record (id INTEGER)")
    writer.commit()
    writer.execute("PRAGMA wal_checkpoint(FULL)")
    snapshot = sqlite3.connect(sqlite_readonly_uri(db_path, immutable=True), uri=True)
    writer.execute("INSERT INTO record VALUES (1)")
    writer.commit()
    live = connect_notification_db(db_path)
    try:
        live_count = live.execute("SELECT COUNT(*) FROM record").fetchone()[0]
        frozen_count = snapshot.execute("SELECT COUNT(*) FROM record").fetchone()[0]
    finally:
        live.close()
        snapshot.close()
        writer.close()
    assert live_count == 1
    assert frozen_count == 0


def test_is_notification_db_access_error():
    assert is_notification_db_access_error(sqlite3.OperationalError("unable to open database file"))
    assert is_notification_db_access_error(PermissionError("denied"))
    assert is_notification_db_access_error(FileNotFoundError("gone"))
    assert not is_notification_db_access_error(sqlite3.OperationalError("no such table: record"))
    assert not is_notification_db_access_error(ValueError("other"))
