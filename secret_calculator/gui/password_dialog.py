"""Small modal dialog for typing a secret, with optional confirm field and validation."""

import tkinter as tk

from . import theme


class SecretDialog(tk.Toplevel):
    def __init__(self, parent, title, prompt, confirm=False, validator=None, show="•"):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=theme.BG, padx=20, pady=16)
        self.resizable(False, False)
        self.transient(parent)
        self.validator = validator
        self.result = None

        tk.Label(self, text=prompt, bg=theme.BG, fg=theme.TEXT, font=theme.BODY_FONT,
                 justify="left", wraplength=280).pack(anchor="w")
        self.first = self._entry(show)
        self.second = None
        if confirm:
            tk.Label(self, text="Type it again to confirm", bg=theme.BG, fg=theme.MUTED,
                     font=theme.BODY_FONT).pack(anchor="w", pady=(8, 0))
            self.second = self._entry(show)
        self.error = tk.Label(self, text="", bg=theme.BG, fg=theme.DANGER, font=theme.BODY_FONT,
                              wraplength=280, justify="left")
        self.error.pack(anchor="w", pady=(6, 0))

        buttons = tk.Frame(self, bg=theme.BG)
        buttons.pack(fill="x", pady=(10, 0))
        tk.Button(buttons, text="OK", width=10, command=self._ok).pack(side="right")
        tk.Button(buttons, text="Cancel", width=10, command=self.destroy).pack(side="right", padx=6)

        self.bind("<Return>", lambda _e: self._ok())
        self.bind("<Escape>", lambda _e: self.destroy())
        self.first.focus_set()

    def _entry(self, show):
        entry = tk.Entry(self, show=show, width=30, font=(theme.FONT, 12))
        entry.pack(fill="x", pady=(4, 0), ipady=3)
        return entry

    def _ok(self):
        value = self.first.get()
        if self.validator:
            message = self.validator(value)
            if message:
                self.error.config(text=message)
                return
        if self.second is not None and self.second.get() != value:
            self.error.config(text="The two entries don't match")
            self.second.delete(0, "end")
            self.second.focus_set()
            return
        self.result = value
        self.destroy()


def ask_secret(parent, title, prompt, confirm=False, validator=None, show="•"):
    """Show the dialog and wait. Returns the text, or None if cancelled/closed."""
    dialog = SecretDialog(parent, title, prompt, confirm, validator, show)
    dialog.grab_set()
    parent.wait_window(dialog)
    return dialog.result
