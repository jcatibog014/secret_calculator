"""The hidden Info Locker window."""

import tkinter as tk
from tkinter import messagebox, ttk

from .. import security, storage
from ..locker import CATEGORIES, save_locker
from . import theme
from .password_dialog import ask_secret

ALL = "All"
CLIPBOARD_CLEAR_MS = 30_000


class LockerWindow(tk.Toplevel):
    def __init__(self, root, locker, keys, config, on_close):
        super().__init__(root)
        self.locker = locker
        self.keys = keys
        self.config_data = config
        self.on_close = on_close
        self.selected_id = None
        self.copied_secret = None

        self.title("Secret Locker")
        self.configure(bg=theme.BG, padx=12, pady=12)
        self.minsize(780, 480)
        self.protocol("WM_DELETE_WINDOW", self.lock)

        self._build_list()
        self._build_form()
        self._build_toolbar()
        self._refresh_list()
        self._new_entry()

    # ----- layout ---------------------------------------------------------------
    def _label(self, parent, text, **grid):
        tk.Label(parent, text=text, bg=theme.BG, fg=theme.MUTED, font=theme.BODY_FONT).grid(sticky="w", **grid)

    def _build_list(self):
        left = tk.Frame(self, bg=theme.BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self._label(left, "Search", row=0, column=0)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._refresh_list())
        tk.Entry(left, textvariable=self.search_var, width=22).grid(row=1, column=0, sticky="ew")
        self.filter_var = tk.StringVar(value=ALL)
        filter_box = ttk.Combobox(left, textvariable=self.filter_var, values=(ALL, *CATEGORIES),
                                  state="readonly", width=12)
        filter_box.grid(row=1, column=1, padx=(6, 0))
        filter_box.bind("<<ComboboxSelected>>", lambda _e: self._refresh_list())

        self.tree = ttk.Treeview(left, columns=("category",), height=16, selectmode="browse")
        self.tree.heading("#0", text="Title")
        self.tree.heading("category", text="Category")
        self.tree.column("#0", width=180)
        self.tree.column("category", width=100)
        self.tree.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(8, 0))
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        left.rowconfigure(2, weight=1)

    def _build_form(self):
        form = tk.Frame(self, bg=theme.BG)
        form.grid(row=0, column=1, sticky="nsew")
        form.columnconfigure(0, weight=1)

        self._label(form, "Category", row=0, column=0)
        self.category_var = tk.StringVar(value=CATEGORIES[0])
        ttk.Combobox(form, textvariable=self.category_var, values=CATEGORIES, state="readonly"
                     ).grid(row=1, column=0, sticky="w")

        self._label(form, "Title", row=2, column=0, pady=(8, 0))
        self.title_entry = tk.Entry(form)
        self.title_entry.grid(row=3, column=0, columnspan=3, sticky="ew")

        self._label(form, "Username / number", row=4, column=0, pady=(8, 0))
        self.username_entry = tk.Entry(form)
        self.username_entry.grid(row=5, column=0, columnspan=3, sticky="ew")

        self._label(form, "Secret (password, PIN, card no.)", row=6, column=0, pady=(8, 0))
        self.secret_entry = tk.Entry(form, show="•")
        self.secret_entry.grid(row=7, column=0, sticky="ew")
        self.show_var = tk.BooleanVar(value=False)
        tk.Checkbutton(form, text="Show", variable=self.show_var, command=self._toggle_secret,
                       bg=theme.BG, fg=theme.TEXT, selectcolor=theme.PANEL,
                       activebackground=theme.BG).grid(row=7, column=1, padx=6)
        tk.Button(form, text="Copy", command=self._copy_secret).grid(row=7, column=2)

        self._label(form, "Notes", row=8, column=0, pady=(8, 0))
        self.notes_text = tk.Text(form, height=8, wrap="word", font=theme.BODY_FONT)
        self.notes_text.grid(row=9, column=0, columnspan=3, sticky="nsew")
        form.rowconfigure(9, weight=1)

        self.message = tk.Label(form, text="", bg=theme.BG, fg=theme.DANGER, font=theme.BODY_FONT)
        self.message.grid(row=10, column=0, columnspan=3, sticky="w", pady=(6, 0))

        buttons = tk.Frame(form, bg=theme.BG)
        buttons.grid(row=11, column=0, columnspan=3, sticky="e", pady=(6, 0))
        tk.Button(buttons, text="New", width=9, command=self._new_entry).pack(side="left", padx=3)
        tk.Button(buttons, text="Save", width=9, command=self._save_entry).pack(side="left", padx=3)
        tk.Button(buttons, text="Delete", width=9, command=self._delete_entry).pack(side="left", padx=3)

    def _build_toolbar(self):
        bar = tk.Frame(self, bg=theme.BG)
        bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        tk.Button(bar, text="Change PIN", command=self._change_pin).pack(side="left")
        tk.Button(bar, text="Change password", command=self._change_password).pack(side="left", padx=6)
        tk.Button(bar, text="🔒 Lock", width=12, bg=theme.OPERATOR, command=self.lock).pack(side="right")

    # ----- list & form ------------------------------------------------------------
    def _refresh_list(self):
        category = None if self.filter_var.get() == ALL else self.filter_var.get()
        self.tree.delete(*self.tree.get_children())
        for entry in self.locker.search(self.search_var.get(), category):
            self.tree.insert("", "end", iid=entry.id, text=entry.title, values=(entry.category,))
        if self.selected_id and self.tree.exists(self.selected_id):
            self.tree.selection_set(self.selected_id)

    def _fill_form(self, entry=None):
        self.category_var.set(entry.category if entry else CATEGORIES[0])
        for widget, value in ((self.title_entry, entry and entry.title),
                              (self.username_entry, entry and entry.username),
                              (self.secret_entry, entry and entry.secret)):
            widget.delete(0, "end")
            widget.insert(0, value or "")
        self.notes_text.delete("1.0", "end")
        self.notes_text.insert("1.0", entry.notes if entry else "")
        self.show_var.set(False)
        self._toggle_secret()
        self.message.config(text="")

    def _on_select(self, _event):
        selection = self.tree.selection()
        if selection and selection[0] != self.selected_id:
            self.selected_id = selection[0]
            self._fill_form(self.locker.get(self.selected_id))

    def _new_entry(self):
        self.selected_id = None
        self.tree.selection_remove(*self.tree.selection())
        self._fill_form()
        self.title_entry.focus_set()

    def _save_entry(self):
        fields = dict(title=self.title_entry.get(), category=self.category_var.get(),
                      username=self.username_entry.get(), secret=self.secret_entry.get(),
                      notes=self.notes_text.get("1.0", "end-1c"))
        try:
            if self.selected_id:
                self.locker.update(self.selected_id, **fields)
            else:
                self.selected_id = self.locker.add(**fields).id
        except ValueError as exc:
            self.message.config(text=str(exc), fg=theme.DANGER)
            return
        self._persist()
        self._refresh_list()
        self.message.config(text="Saved", fg=theme.MUTED)

    def _delete_entry(self):
        if not self.selected_id:
            return
        title = self.locker.get(self.selected_id).title
        if not messagebox.askyesno("Delete", f"Delete “{title}”?", parent=self):
            return
        self.locker.delete(self.selected_id)
        self._persist()
        self._new_entry()
        self._refresh_list()

    def _toggle_secret(self):
        self.secret_entry.config(show="" if self.show_var.get() else "•")

    def _copy_secret(self):
        secret = self.secret_entry.get()
        if not secret:
            return
        self.clipboard_clear()
        self.clipboard_append(secret)
        self.copied_secret = secret
        self.message.config(text="Copied, clipboard clears in 30 seconds", fg=theme.MUTED)
        self.after(CLIPBOARD_CLEAR_MS, self._clear_clipboard)

    def _clear_clipboard(self):
        try:
            if self.copied_secret and self.clipboard_get() == self.copied_secret:
                self.clipboard_clear()
        except tk.TclError:
            pass  # clipboard empty or holds something else
        self.copied_secret = None

    # ----- saving & secrets --------------------------------------------------------
    def _persist(self):
        save_locker(self.locker, self.keys)

    def _rekey(self, config, keys):
        """Re-encrypt with new keys, then store the new config."""
        save_locker(self.locker, keys)
        storage.write_json(storage.config_path(), config)
        self.config_data, self.keys = config, keys

    def _change_pin(self):
        pin = ask_secret(self, "Change PIN", f"New {security.PIN_LENGTH}-digit PIN",
                         confirm=True, validator=security.validate_pin)
        if pin is not None:
            self._rekey(*security.change_pin(self.config_data, self.keys, pin))
            messagebox.showinfo("Change PIN", "PIN changed.", parent=self)

    def _change_password(self):
        password = ask_secret(self, "Change password", "New password (letters and numbers, 6-32 characters)",
                              confirm=True, validator=security.validate_password)
        if password is not None:
            self._rekey(*security.change_password(self.config_data, self.keys, password))
            messagebox.showinfo("Change password", "Password changed.", parent=self)

    def lock(self):
        self._clear_clipboard()
        self.destroy()
        self.on_close(self.config_data)
