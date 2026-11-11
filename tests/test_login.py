from pathlib import Path

import plistlib

from notification_watcher.login import (
    _macos_app_path,
    _set_macos_launch_at_login,
    repair_macos_launch_agent_if_needed,
)
from notification_watcher.product import BUNDLE_ID


def test_macos_app_path_resolves_bundle(tmp_path: Path, monkeypatch) -> None:
    bundle = tmp_path / "Trade Desky Watcher.app"
    exe = bundle / "Contents" / "MacOS" / "Trade Desky Watcher"
    exe.parent.mkdir(parents=True)
    exe.write_text("")

    monkeypatch.setattr("notification_watcher.login.sys.frozen", True, raising=False)
    monkeypatch.setattr("notification_watcher.login.sys.executable", str(exe))

    assert _macos_app_path() == bundle.resolve()


def test_macos_app_path_none_when_not_frozen(monkeypatch) -> None:
    monkeypatch.setattr("notification_watcher.login.sys.frozen", False, raising=False)
    assert _macos_app_path() is None


def test_set_macos_launch_at_login_writes_app_bundle(tmp_path: Path, monkeypatch) -> None:
    agents = tmp_path / "LaunchAgents"
    monkeypatch.setattr(
        "notification_watcher.login._plist_path",
        lambda label: agents / f"{label}.plist",
    )
    bundle = tmp_path / "Trade Desky Watcher.app"
    bundle.mkdir()

    _set_macos_launch_at_login(True, bundle)

    plist_path = agents / f"{BUNDLE_ID}.plist"
    assert plist_path.exists()
    data = plist_path.read_bytes()
    assert b"RunAtLoad" in data
    assert str(bundle).encode() in data
    assert b"/Contents<" not in data


def test_set_macos_launch_at_login_disable_removes_plist(tmp_path: Path, monkeypatch) -> None:
    agents = tmp_path / "LaunchAgents"
    agents.mkdir()
    plist_path = agents / f"{BUNDLE_ID}.plist"
    plist_path.write_text("stub")
    monkeypatch.setattr(
        "notification_watcher.login._plist_path",
        lambda label: agents / f"{label}.plist",
    )

    _set_macos_launch_at_login(False, None)

    assert not plist_path.exists()


def test_repair_macos_launch_agent_rewrites_contents_path(tmp_path: Path, monkeypatch) -> None:
    agents = tmp_path / "LaunchAgents"
    agents.mkdir()
    bundle = tmp_path / "Trade Desky Watcher.app"
    bundle.mkdir()
    bad = bundle / "Contents"
    bad.mkdir()
    plist_path = agents / f"{BUNDLE_ID}.plist"
    plist_path.write_bytes(
        plistlib.dumps(
            {
                "Label": BUNDLE_ID,
                "ProgramArguments": ["open", "-a", str(bad)],
                "RunAtLoad": True,
            }
        )
    )
    monkeypatch.setattr(
        "notification_watcher.login._plist_path",
        lambda label: agents / f"{label}.plist",
    )
    monkeypatch.setattr("notification_watcher.login.sys.platform", "darwin")

    assert repair_macos_launch_agent_if_needed(bundle) is True
    args = plistlib.loads(plist_path.read_bytes())["ProgramArguments"]
    assert args[-1] == str(bundle)
