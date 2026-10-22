"""Themed modal dialogs: secret entry (with optional confirm + validation), confirm, message."""

import tkinter as tk

import customtkinter as ctk

from . import theme
from .icon import keep_app_icon
from .widgets import center_over, fit_window

DIALOG_WIDTH = 360


class _Dialog(ctk.CTkToplevel):
    """Base: dark window, title, prompt text, a button row, Enter/Escape keys."""

    def __init__(self, parent, title, prompt):
        super().__init__(parent, fg_color=theme.BG)
        keep_app_icon(self)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.parent = parent
        self.result = None
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=24, pady=22)
        ctk.CTkLabel(self.body, text=prompt, text_color=theme.TEXT, font=theme.font(14),
                     justify="left", anchor="w", wraplength=DIALOG_WIDTH - 48).pack(fill="x")
        self.bind("<Escape>", lambda _e: self.destroy())

    def _label(self, text):
        ctk.CTkLabel(self.body, text=text, text_color=theme.MUTED, font=theme.font(12),
                     anchor="w").pack(fill="x", pady=(14, 4))

    def _entry(self, show):
        entry = ctk.CTkEntry(self.body, show=show, height=theme.BUTTON_HEIGHT, corner_radius=theme.RADIUS,
                             fg_color=theme.SURFACE_ALT, border_color=theme.BORDER, text_color=theme.TEXT,
                             font=theme.font(14))
        entry.pack(fill="x")
        return entry

    def _buttons(self, ok_text, on_ok, danger=False, cancel=True):
        row = ctk.CTkFrame(self.body, fg_color="transparent")
        row.pack(fill="x", pady=(18, 0))
        if danger:
            colors = dict(fg_color=theme.RED_BUTTON, hover_color=theme.RED_BUTTON_HOVER, text_color=theme.RED)
        else:
            colors = dict(fg_color=theme.AMBER, hover_color=theme.AMBER_HOVER, text_color=theme.ON_AMBER)
        ctk.CTkButton(row, text=ok_text, width=110, height=theme.BUTTON_HEIGHT, corner_radius=theme.RADIUS,
                      font=theme.font(14, "bold"), command=on_ok, **colors).pack(side="right")
        if cancel:
            ctk.CTkButton(row, text="Cancel", width=100, height=theme.BUTTON_HEIGHT, corner_radius=theme.RADIUS,
                          fg_color="transparent", hover_color=theme.HOVER, border_width=1,
                          border_color=theme.BORDER, text_color=theme.TEXT, font=theme.font(14),
                          command=self.destroy).pack(side="right", padx=(0, 10))
        self.bind("<Return>", lambda _e: on_ok())

    def _show(self, focus=None):
        fit_window(self, min_width=DIALOG_WIDTH)
        center_over(self, self.parent)
        self.after(150, (focus or self).focus_force)


class SecretDialog(_Dialog):
    def __init__(self, parent, title, prompt, confirm=False, validator=None, show="•"):
        super().__init__(parent, title, prompt)
        self.validator = validator
        self.first = self._entry(show)
        self.first.pack_configure(pady=(12, 0))
        self.second = None
        if confirm:
            self._label("Type it again to confirm")
            self.second = self._entry(show)
        self.error = ctk.CTkLabel(self.body, text="", text_color=theme.RED, font=theme.font(12),
                                  anchor="w", justify="left", wraplength=DIALOG_WIDTH - 48)
        self.error.pack(fill="x", pady=(8, 0))
        self._buttons("OK", self._ok)
        self._show(self.first)

    def _ok(self):
        value = self.first.get()
        if self.validator:
            message = self.validator(value)
            if message:
                self.error.configure(text=message)
                return
        if self.second is not None and self.second.get() != value:
            self.error.configure(text="The two entries don't match")
            self.second.delete(0, "end")
            self.second.focus_set()
            return
        self.result = value
        self.destroy()


class ConfirmDialog(_Dialog):
    def __init__(self, parent, title, prompt, ok_text, danger):
        super().__init__(parent, title, prompt)
        self._buttons(ok_text, self._ok, danger=danger)
        self._show()

    def _ok(self):
        self.result = True
        self.destroy()


class MessageDialog(_Dialog):
    def __init__(self, parent, title, prompt):
        super().__init__(parent, title, prompt)
        self._buttons("OK", self.destroy, cancel=False)
        self._show()


def _run(parent, dialog):
    try:
        dialog.wait_visibility()
        dialog.grab_set()
    except tk.TclError:
        pass  # window closed before it was shown
    parent.wait_window(dialog)
    return dialog.result


def ask_secret(parent, title, prompt, confirm=False, validator=None, show="•"):
    """Show the dialog and wait. Returns the text, or None if cancelled/closed."""
    return _run(parent, SecretDialog(parent, title, prompt, confirm, validator, show))


def ask_confirm(parent, title, prompt, ok_text="OK", danger=False):
    """Yes/no question. Returns True only when the OK button was pressed."""
    return bool(_run(parent, ConfirmDialog(parent, title, prompt, ok_text, danger)))


def show_message(parent, title, prompt):
    _run(parent, MessageDialog(parent, title, prompt))
