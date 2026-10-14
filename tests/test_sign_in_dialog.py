import os
import sys

import pytest

from notification_watcher.sign_in_dialog import _dialog_fonts


def _has_tk_display() -> bool:
    if sys.platform == "darwin" or sys.platform == "win32":
        return True
    return bool(os.environ.get("DISPLAY"))


@pytest.mark.skipif(not _has_tk_display(), reason="requires a display for tkinter")
def test_dialog_fonts_use_system_family() -> None:
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()
    title, body, label, entry = _dialog_fonts(root)
    assert title.cget("weight") == "bold"
    assert body.cget("family") == label.cget("family") == entry.cget("family")
    root.destroy()
