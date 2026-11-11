"""Cross-platform sign-in dialog (tkinter, Soft Sage styling)."""

from __future__ import annotations

import sys
import tkinter as tk
import tkinter.font as tkfont
import webbrowser
from pathlib import Path
from typing import Callable

from notification_watcher.product import APP_NAME, BRAND_NAME

_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"

_BG = "#F2F4F1"
_CARD = "#FFFFFF"
_INK = "#111111"
_MUTED = "#5C635A"
_PRIMARY = "#22C55E"
_PRIMARY_ACTIVE = "#16A34A"
_BORDER = "#D8DED5"
_ERROR = "#B91C1C"


def _dialog_fonts(root: tk.Misc) -> tuple[tkfont.Font, tkfont.Font, tkfont.Font, tkfont.Font]:
    base = tkfont.nametofont("TkDefaultFont")
    family = base.actual("family")
    size = int(base.actual("size"))
    if size <= 0:
        size = 13 if sys.platform == "darwin" else 10
    title_font = tkfont.Font(root=root, family=family, size=size + 7, weight="bold")
    body_font = tkfont.Font(root=root, family=family, size=size)
    label_font = tkfont.Font(root=root, family=family, size=size, weight="bold")
    entry_font = tkfont.Font(root=root, family=family, size=size + 1)
    return title_font, body_font, label_font, entry_font


def show_sign_in_dialog(
    root: tk.Tk,
    *,
    initial_email: str = "",
    on_submit: Callable[[str, str], tuple[bool, str]],
    on_redeem_code: Callable[[str], tuple[bool, str]] | None = None,
    desktop_sign_in_url: str | None = None,
) -> str | None:
    """Modal sign-in.

    ``on_submit`` and ``on_redeem_code`` return ``(success, error_or_email)``.
    On success the second value is the signed-in email. Returns that email or None.
    """
    result: str | None = None
    root.update_idletasks()
    win = tk.Toplevel(root)
    win.title(f"Sign in — {APP_NAME}")
    win.configure(bg=_BG)
    win.resizable(False, False)
    win.withdraw()

    width, height = 420, 620
    x = (win.winfo_screenwidth() // 2) - (width // 2)
    y = (win.winfo_screenheight() // 2) - (height // 2)
    win.geometry(f"{width}x{height}+{x}+{y}")

    card = tk.Frame(win, bg=_CARD, highlightbackground=_BORDER, highlightthickness=1)
    card.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

    title_font, body_font, label_font, entry_font = _dialog_fonts(win)

    header = tk.Frame(card, bg=_CARD)
    header.pack(fill=tk.X, padx=24, pady=(22, 8))

    logo_path = _ASSETS_DIR / "icon.png"
    if logo_path.is_file():
        try:
            photo = tk.PhotoImage(file=str(logo_path))
            photo = photo.subsample(max(photo.width() // 48, 1), max(photo.height() // 48, 1))
            logo_label = tk.Label(header, image=photo, bg=_CARD)
            logo_label.image = photo
            logo_label.pack(anchor=tk.W)
        except tk.TclError:
            pass

    tk.Label(
        header,
        text=f"Sign in to {BRAND_NAME}",
        font=title_font,
        fg=_INK,
        bg=_CARD,
        anchor=tk.W,
    ).pack(anchor=tk.W, pady=(10, 4))
    tk.Label(
        header,
        text=(
            f"Use Google, Apple, or email — same account as the {BRAND_NAME} website "
            "and Whop billing."
        ),
        font=body_font,
        fg=_MUTED,
        bg=_CARD,
        wraplength=340,
        justify=tk.LEFT,
        anchor=tk.W,
    ).pack(anchor=tk.W)

    form = tk.Frame(card, bg=_CARD)
    form.pack(fill=tk.X, padx=24, pady=(8, 0))

    error_var = tk.StringVar()

    def set_busy(busy: bool) -> None:
        state = tk.DISABLED if busy else tk.NORMAL
        sign_in_btn.configure(state=state, bg=_MUTED if busy else _PRIMARY)
        cancel_btn.configure(state=state)
        if browser_btn is not None:
            browser_btn.configure(state=state)
        if redeem_btn is not None:
            redeem_btn.configure(state=state)

    def finish_success(email: str) -> None:
        nonlocal result
        result = email
        close()

    browser_btn: tk.Button | None = None
    if desktop_sign_in_url:

        def open_browser() -> None:
            error_var.set("")
            webbrowser.open(desktop_sign_in_url)

        browser_btn = tk.Button(
            form,
            text="Continue with Google / Apple",
            font=label_font,
            fg=_INK,
            bg=_BG,
            activebackground=_BORDER,
            activeforeground=_INK,
            relief=tk.FLAT,
            cursor="hand2",
            padx=12,
            pady=8,
            command=open_browser,
        )
        browser_btn.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            form,
            text="Opens the website. Sign in, then paste the one-time code below.",
            font=body_font,
            fg=_MUTED,
            bg=_CARD,
            wraplength=340,
            justify=tk.LEFT,
            anchor=tk.W,
        ).pack(fill=tk.X, pady=(0, 12))

    redeem_btn: tk.Button | None = None
    code_entry: tk.Entry | None = None
    if on_redeem_code is not None:
        tk.Label(form, text="Desktop code", font=label_font, fg=_INK, bg=_CARD, anchor=tk.W).pack(
            fill=tk.X, pady=(0, 4)
        )
        code_var = tk.StringVar()
        code_entry = tk.Entry(
            form,
            textvariable=code_var,
            font=entry_font,
            relief=tk.FLAT,
            bg="#FAFBFA",
            fg=_INK,
            insertbackground=_INK,
            highlightthickness=1,
            highlightbackground=_BORDER,
            highlightcolor=_PRIMARY,
        )
        code_entry.pack(fill=tk.X, ipady=8, pady=(0, 8))

        def redeem() -> None:
            code = code_var.get().strip()
            if not code:
                error_var.set("Paste the code from the website.")
                if code_entry is not None:
                    code_entry.focus_set()
                return
            error_var.set("")
            set_busy(True)
            win.update_idletasks()
            ok, email_or_error = on_redeem_code(code)
            if ok:
                finish_success(email_or_error)
                return
            error_var.set(email_or_error or "Invalid or expired code.")
            set_busy(False)
            if code_entry is not None:
                code_entry.focus_set()
                code_entry.select_range(0, tk.END)

        redeem_btn = tk.Button(
            form,
            text="Link with code",
            font=label_font,
            fg=_INK,
            bg=_PRIMARY,
            activebackground=_PRIMARY_ACTIVE,
            activeforeground=_INK,
            relief=tk.FLAT,
            cursor="hand2",
            padx=12,
            pady=8,
            command=redeem,
        )
        redeem_btn.pack(fill=tk.X, pady=(0, 14))

        tk.Label(
            form,
            text="or email and password",
            font=body_font,
            fg=_MUTED,
            bg=_CARD,
            anchor=tk.W,
        ).pack(fill=tk.X, pady=(0, 10))

    tk.Label(form, text="Email", font=label_font, fg=_INK, bg=_CARD, anchor=tk.W).pack(
        fill=tk.X, pady=(0, 4)
    )
    email_var = tk.StringVar(value=initial_email)
    email_entry = tk.Entry(
        form,
        textvariable=email_var,
        font=entry_font,
        relief=tk.FLAT,
        bg="#FAFBFA",
        fg=_INK,
        insertbackground=_INK,
        highlightthickness=1,
        highlightbackground=_BORDER,
        highlightcolor=_PRIMARY,
    )
    email_entry.pack(fill=tk.X, ipady=8, pady=(0, 14))

    tk.Label(form, text="Password", font=label_font, fg=_INK, bg=_CARD, anchor=tk.W).pack(
        fill=tk.X, pady=(0, 4)
    )
    password_var = tk.StringVar()
    password_entry = tk.Entry(
        form,
        textvariable=password_var,
        font=entry_font,
        show="•",
        relief=tk.FLAT,
        bg="#FAFBFA",
        fg=_INK,
        insertbackground=_INK,
        highlightthickness=1,
        highlightbackground=_BORDER,
        highlightcolor=_PRIMARY,
    )
    password_entry.pack(fill=tk.X, ipady=8)

    tk.Label(
        form,
        textvariable=error_var,
        font=body_font,
        fg=_ERROR,
        bg=_CARD,
        wraplength=340,
        justify=tk.LEFT,
        anchor=tk.W,
    ).pack(fill=tk.X, pady=(10, 0))

    buttons = tk.Frame(card, bg=_CARD)
    buttons.pack(fill=tk.X, padx=24, pady=(18, 22))

    def close() -> None:
        try:
            win.grab_release()
        except tk.TclError:
            pass
        win.destroy()

    def submit() -> None:
        email = email_var.get().strip()
        password = password_var.get()
        if not email:
            error_var.set("Email is required.")
            email_entry.focus_set()
            return
        if not password:
            error_var.set("Password is required.")
            password_entry.focus_set()
            return
        error_var.set("")
        set_busy(True)
        win.update_idletasks()
        ok, message = on_submit(email, password)
        if ok:
            finish_success(email)
            return
        error_var.set(message or "Sign in failed.")
        set_busy(False)
        password_entry.focus_set()
        password_entry.select_range(0, tk.END)

    sign_in_btn = tk.Button(
        buttons,
        text="Sign in",
        font=label_font,
        fg=_INK,
        bg=_PRIMARY,
        activebackground=_PRIMARY_ACTIVE,
        activeforeground=_INK,
        relief=tk.FLAT,
        cursor="hand2",
        padx=16,
        pady=8,
        command=submit,
    )
    sign_in_btn.pack(side=tk.RIGHT)

    cancel_btn = tk.Button(
        buttons,
        text="Cancel",
        font=label_font,
        fg=_INK,
        bg=_BG,
        activebackground=_BORDER,
        activeforeground=_INK,
        relief=tk.FLAT,
        cursor="hand2",
        padx=12,
        pady=8,
        command=close,
    )
    cancel_btn.pack(side=tk.RIGHT, padx=(0, 10))

    win.bind("<Return>", lambda _e: submit())
    win.bind("<Escape>", lambda _e: close())
    win.protocol("WM_DELETE_WINDOW", close)

    win.deiconify()
    win.update_idletasks()
    win.lift()
    win.attributes("-topmost", True)
    win.after(150, lambda: win.attributes("-topmost", False))
    win.focus_force()
    try:
        win.grab_set()
    except tk.TclError:
        pass

    if initial_email:
        password_entry.focus_set()
        password_entry.icursor(tk.END)
    else:
        email_entry.focus_set()

    root.wait_window(win)
    return result
