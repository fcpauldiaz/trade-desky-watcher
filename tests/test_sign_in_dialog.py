import tkinter as tk

from notification_watcher.sign_in_dialog import _dialog_fonts


def test_dialog_fonts_use_system_family() -> None:
    root = tk.Tk()
    root.withdraw()
    title, body, label, entry = _dialog_fonts(root)
    assert title.cget("weight") == "bold"
    assert body.cget("family") == label.cget("family") == entry.cget("family")
    root.destroy()
