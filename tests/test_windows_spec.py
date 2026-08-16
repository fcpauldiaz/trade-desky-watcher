import sys
from pathlib import Path

from notification_watcher.product import COPYRIGHT
from notification_watcher.version import __version__

SPEC_PATH = Path(__file__).resolve().parent.parent / "notification_watcher.spec"


def test_spec_imports_package_from_specpath(monkeypatch):
    repo = SPEC_PATH.parent.resolve()
    monkeypatch.setattr(
        sys,
        "path",
        [path for path in sys.path if Path(path).resolve() != repo],
    )
    for name in list(sys.modules):
        if name == "notification_watcher" or name.startswith("notification_watcher."):
            monkeypatch.delitem(sys.modules, name, raising=False)

    preamble = []
    for line in SPEC_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("a = Analysis"):
            break
        preamble.append(line)
    ns = {"SPECPATH": str(repo)}
    exec("\n".join(preamble), ns)
    written = Path(ns["version_file"]).read_text(encoding="utf-8")
    assert COPYRIGHT in written
    assert __version__ in written
