"""The hidden Info Locker window: categories | items + search | item details."""

import tkinter as tk

import customtkinter as ctk

from .. import APP_NAME, security, storage
from ..locker import CATEGORIES, save_locker
from . import theme
from .dialogs import ask_confirm, ask_secret, show_message
from .icon import keep_app_icon
from .widgets import clear_children, make_clickable, set_entry

ALL = None  # "All items" in the sidebar
CLIPBOARD_CLEAR_MS = 30_000
SIDEBAR_WIDTH = 230
LIST_WIDTH = 320


def _field_label(parent, text):
    return ctk.CTkLabel(parent, text=text, text_color=theme.MUTED, font=theme.font(12), anchor="w", height=20)


def _entry(parent, **kwargs):
    return ctk.CTkEntry(parent, height=theme.BUTTON_HEIGHT, corner_radius=theme.RADIUS,
                        fg_color=theme.SURFACE_ALT, border_color=theme.BORDER, text_color=theme.TEXT,
                        font=theme.font(14), **kwargs)


def _ghost_button(parent, text, command, **kwargs):
    options = dict(height=theme.BUTTON_HEIGHT, corner_radius=theme.RADIUS, fg_color="transparent",
                   hover_color=theme.HOVER, text_color=theme.TEXT, font=theme.font(13))
    return ctk.CTkButton(parent, text=text, command=command, **{**options, **kwargs})


class LockerWindow(ctk.CTkToplevel):
    def __init__(self, root, locker, keys, config, on_close):
        super().__init__(root, fg_color=theme.BG)
        keep_app_icon(self)
        self.locker = locker
        self.keys = keys
        self.config_data = config
        self.on_close = on_close
        self.selected_id = None
        self.copied_secret = None
        self.filter_category = ALL
        self.secret_visible = False

        self.title("Secret Locker")
        self.geometry("1120x680")
        self.minsize(1000, 600)
        self.protocol("WM_DELETE_WINDOW", self.lock)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_list()
        self._build_details()
        self._refresh_sidebar()
        self._refresh_list()
        self._new_entry()
        self.after(150, self.focus_force)

    # ----- layout ---------------------------------------------------------------
    def _build_sidebar(self):
        side = ctk.CTkFrame(self, fg_color=theme.SURFACE, corner_radius=18, width=SIDEBAR_WIDTH)
        side.grid(row=0, column=0, sticky="ns", padx=(18, 9), pady=18)
        side.grid_propagate(False)
        side.grid_columnconfigure(0, weight=1)
        side.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(side, text=APP_NAME.upper(), text_color=theme.MUTED, font=theme.font(11, "bold"),
                     anchor="w").grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 0))
        ctk.CTkLabel(side, text="Locker", text_color=theme.TEXT, font=theme.font(24, "bold"),
                     anchor="w").grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 12))

        self.category_rows = ctk.CTkFrame(side, fg_color="transparent")
        self.category_rows.grid(row=2, column=0, sticky="new", padx=10)
        self.category_rows.grid_columnconfigure(0, weight=1)

        _ghost_button(side, "Change PIN", self._change_pin, anchor="w", text_color=theme.MUTED
                      ).grid(row=3, column=0, sticky="ew", padx=10)
        _ghost_button(side, "Change password", self._change_password, anchor="w", text_color=theme.MUTED
                      ).grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 10))
        ctk.CTkButton(side, text="🔒  Lock", command=self.lock, height=56, corner_radius=14,
                      fg_color=theme.AMBER, hover_color=theme.AMBER_HOVER, text_color=theme.ON_AMBER,
                      font=theme.font(17, "bold")).grid(row=5, column=0, sticky="ew", padx=14, pady=(0, 16))

    def _build_list(self):
        panel = ctk.CTkFrame(self, fg_color=theme.SURFACE, corner_radius=18, width=LIST_WIDTH)
        panel.grid(row=0, column=1, sticky="ns", padx=9, pady=18)
        panel.grid_propagate(False)
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(2, weight=1)

        self.list_title = ctk.CTkLabel(panel, text="", text_color=theme.TEXT, font=theme.font(18, "bold"),
                                       anchor="w")
        self.list_title.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 8))

        search_row = ctk.CTkFrame(panel, fg_color="transparent")
        search_row.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))
        search_row.grid_columnconfigure(0, weight=1)
        self.search_entry = _entry(search_row, placeholder_text="Search", placeholder_text_color=theme.MUTED)
        self.search_entry.grid(row=0, column=0, sticky="ew")
        self.search_entry.bind("<KeyRelease>", lambda _e: self._refresh_list())
        add_text, add_font = theme.icon(self, "add", 16)
        ctk.CTkButton(search_row, text=add_text, font=add_font, width=theme.BUTTON_HEIGHT,
                      height=theme.BUTTON_HEIGHT, corner_radius=theme.RADIUS, fg_color=theme.AMBER,
                      hover_color=theme.AMBER_HOVER, text_color=theme.ON_AMBER,
                      command=self._new_entry).grid(row=0, column=1, padx=(8, 0))

        self.item_list = ctk.CTkScrollableFrame(panel, fg_color="transparent",
                                                scrollbar_button_color=theme.SURFACE_ALT,
                                                scrollbar_button_hover_color=theme.HOVER)
        self.item_list.grid(row=2, column=0, sticky="nsew", padx=(8, 4), pady=(0, 12))
        self.item_list.grid_columnconfigure(0, weight=1)

    def _build_details(self):
        panel = ctk.CTkFrame(self, fg_color=theme.SURFACE, corner_radius=18)
        panel.grid(row=0, column=2, sticky="nsew", padx=(9, 18), pady=18)
        panel.grid_columnconfigure(0, weight=1)
        form = ctk.CTkFrame(panel, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=24, pady=20)
        form.grid_columnconfigure(0, weight=1)

        self.details_title = ctk.CTkLabel(form, text="", text_color=theme.TEXT, font=theme.font(20, "bold"),
                                          anchor="w")
        self.details_title.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        _field_label(form, "Category").grid(row=1, column=0, sticky="w")
        self.category_var = tk.StringVar(value=CATEGORIES[0])
        self.category_menu = ctk.CTkOptionMenu(
            form, variable=self.category_var, values=list(CATEGORIES), command=self._paint_category,
            height=theme.BUTTON_HEIGHT, width=200, corner_radius=theme.RADIUS, font=theme.font(14, "bold"),
            text_color=theme.ON_AMBER, dropdown_fg_color=theme.SURFACE_ALT, dropdown_hover_color=theme.HOVER,
            dropdown_text_color=theme.TEXT, dropdown_font=theme.font(14))
        self.category_menu.grid(row=2, column=0, sticky="w", pady=(4, 14))

        _field_label(form, "Title").grid(row=3, column=0, sticky="w")
        self.title_entry = _entry(form)
        self.title_entry.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(4, 14))

        _field_label(form, "Username / number").grid(row=5, column=0, sticky="w")
        self.username_entry = _entry(form)
        self.username_entry.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(4, 14))

        _field_label(form, "Secret (password, PIN, card no.)").grid(row=7, column=0, sticky="w")
        self.secret_entry = _entry(form, show="•")
        self.secret_entry.grid(row=8, column=0, sticky="ew", pady=(4, 14))
        self.show_button = self._icon_button(form, "show", self._toggle_secret)
        self.show_button.grid(row=8, column=1, padx=(8, 0), pady=(4, 14))
        self._icon_button(form, "copy", self._copy_secret).grid(row=8, column=2, padx=(8, 0), pady=(4, 14))

        _field_label(form, "Notes").grid(row=9, column=0, sticky="w")
        self.notes_text = ctk.CTkTextbox(form, height=150, corner_radius=theme.RADIUS, fg_color=theme.SURFACE_ALT,
                                         border_color=theme.BORDER, border_width=2, text_color=theme.TEXT,
                                         font=theme.font(14), wrap="word")
        self.notes_text.grid(row=10, column=0, columnspan=3, sticky="nsew", pady=(4, 6))
        form.grid_rowconfigure(10, weight=1)

        self.message = ctk.CTkLabel(form, text="", text_color=theme.RED, font=theme.font(12), anchor="w",
                                    height=22)
        self.message.grid(row=11, column=0, columnspan=3, sticky="ew")

        actions = ctk.CTkFrame(form, fg_color="transparent")
        actions.grid(row=12, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        self.delete_button = ctk.CTkButton(
            actions, text="Delete", width=120, height=theme.BUTTON_HEIGHT, corner_radius=theme.RADIUS,
            fg_color=theme.RED_BUTTON, hover_color=theme.RED_BUTTON_HOVER, text_color=theme.RED,
            text_color_disabled=theme.BORDER, font=theme.font(14, "bold"), command=self._delete_entry)
        self.delete_button.pack(side="left")
        ctk.CTkButton(actions, text="Save", width=140, height=theme.BUTTON_HEIGHT, corner_radius=theme.RADIUS,
                      fg_color=theme.AMBER, hover_color=theme.AMBER_HOVER, text_color=theme.ON_AMBER,
                      font=theme.font(14, "bold"), command=self._save_entry).pack(side="right")

    def _icon_button(self, parent, name, command):
        text, icon_font = theme.icon(self, name)
        return ctk.CTkButton(parent, text=text, font=icon_font, width=theme.BUTTON_HEIGHT,
                             height=theme.BUTTON_HEIGHT, corner_radius=theme.RADIUS, fg_color=theme.SURFACE_ALT,
                             hover_color=theme.HOVER, text_color=theme.TEXT, command=command)

    # ----- sidebar & list ----------------------------------------------------------
    def _refresh_sidebar(self):
        clear_children(self.category_rows)
        rows = [(ALL, "All items", theme.TEXT, len(self.locker.entries))]
        for category in CATEGORIES:
            count = sum(entry.category == category for entry in self.locker.entries)
            rows.append((category, theme.CATEGORY_LABELS[category], theme.CATEGORY_COLORS[category], count))
        for index, (category, label, color, count) in enumerate(rows):
            selected = category == self.filter_category
            normal = theme.SURFACE_ALT if selected else theme.SURFACE
            row = ctk.CTkFrame(self.category_rows, fg_color=normal, corner_radius=theme.RADIUS,
                               height=theme.BUTTON_HEIGHT)
            row.grid(row=index, column=0, sticky="ew", pady=1)
            row.grid_propagate(False)
            row.grid_columnconfigure(1, weight=1)
            row.grid_rowconfigure(0, weight=1)
            ctk.CTkLabel(row, text="●", text_color=color, font=theme.font(22), width=20
                         ).grid(row=0, column=0, padx=(12, 8))
            ctk.CTkLabel(row, text=label, text_color=theme.TEXT, font=theme.font(14, "bold" if selected else "normal"),
                         anchor="w").grid(row=0, column=1, sticky="ew")
            ctk.CTkLabel(row, text=str(count), text_color=theme.MUTED, font=theme.font(12)
                         ).grid(row=0, column=2, padx=(4, 12))
            make_clickable(row, lambda c=category: self._pick_category(c), normal, theme.HOVER)

    def _pick_category(self, category):
        self.filter_category = category
        self._refresh_sidebar()
        self._refresh_list()

    def _refresh_list(self):
        category = self.filter_category
        title = "All items" if category is ALL else theme.CATEGORY_LABELS[category]
        self.list_title.configure(text=title)
        clear_children(self.item_list)
        entries = self.locker.search(self.search_entry.get(), category)
        if not entries:
            ctk.CTkLabel(self.item_list, text="Nothing here yet", text_color=theme.MUTED,
                         font=theme.font(13)).grid(row=0, column=0, pady=30)
        for index, entry in enumerate(entries):
            self._item_tile(index, entry)

    def _item_tile(self, index, entry):
        color = theme.CATEGORY_COLORS.get(entry.category, theme.MUTED)
        selected = entry.id == self.selected_id
        normal = theme.SURFACE_ALT if selected else theme.SURFACE
        tile = ctk.CTkFrame(self.item_list, fg_color=normal, corner_radius=theme.RADIUS, height=64,
                            border_width=2 if selected else 0, border_color=color)
        tile.grid(row=index, column=0, sticky="ew", pady=2)
        tile.grid_propagate(False)
        tile.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(tile, text=(entry.title[:1] or "?").upper(), width=40, height=40, corner_radius=10,
                     fg_color=color, text_color=theme.ON_AMBER, font=theme.font(17, "bold")
                     ).grid(row=0, column=0, rowspan=2, padx=12, pady=12)
        ctk.CTkLabel(tile, text=entry.title, text_color=theme.TEXT, font=theme.font(14, "bold"), anchor="sw",
                     height=22).grid(row=0, column=1, sticky="sew", padx=(0, 12), pady=(11, 0))
        ctk.CTkLabel(tile, text=theme.CATEGORY_LABELS.get(entry.category, entry.category), text_color=color,
                     font=theme.font(12), anchor="nw", height=18).grid(row=1, column=1, sticky="new",
                                                                        padx=(0, 12), pady=(0, 11))
        make_clickable(tile, lambda: self._on_select(entry.id), normal, theme.HOVER)

    # ----- form -------------------------------------------------------------------
    def _paint_category(self, category):
        color = theme.CATEGORY_COLORS.get(category, theme.MUTED)
        self.category_menu.configure(fg_color=color, button_color=color, button_hover_color=color)

    def _fill_form(self, entry=None):
        self.category_var.set(entry.category if entry else CATEGORIES[0])
        self._paint_category(self.category_var.get())
        set_entry(self.title_entry, entry and entry.title)
        set_entry(self.username_entry, entry and entry.username)
        set_entry(self.secret_entry, entry and entry.secret)
        self.notes_text.delete("1.0", "end")
        self.notes_text.insert("1.0", entry.notes if entry else "")
        self.secret_visible = False
        self._apply_secret_visibility()
        self.details_title.configure(text="Edit item" if entry else "New item")
        self.delete_button.configure(state="normal" if entry else "disabled")
        self.message.configure(text="")

    def _on_select(self, entry_id):
        if entry_id != self.selected_id:
            self.selected_id = entry_id
            self._fill_form(self.locker.get(entry_id))
            self._refresh_list()

    def _new_entry(self):
        self.selected_id = None
        self._fill_form()
        self._refresh_list()
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
            self.message.configure(text=str(exc), text_color=theme.RED)
            return
        self._persist()
        self._refresh_sidebar()
        self._refresh_list()
        self.details_title.configure(text="Edit item")
        self.delete_button.configure(state="normal")
        self.message.configure(text="Saved", text_color=theme.MUTED)

    def _delete_entry(self):
        if not self.selected_id:
            return
        title = self.locker.get(self.selected_id).title
        if not ask_confirm(self, "Delete", f"Delete “{title}”?\nThis can't be undone.", "Delete", danger=True):
            return
        self.locker.delete(self.selected_id)
        self._persist()
        self._refresh_sidebar()
        self._new_entry()

    def _apply_secret_visibility(self):
        self.secret_entry.configure(show="" if self.secret_visible else "•")
        text, _font = theme.icon(self, "hide" if self.secret_visible else "show")
        self.show_button.configure(text=text)

    def _toggle_secret(self):
        self.secret_visible = not self.secret_visible
        self._apply_secret_visibility()

    def _copy_secret(self):
        secret = self.secret_entry.get()
        if not secret:
            return
        self.clipboard_clear()
        self.clipboard_append(secret)
        self.copied_secret = secret
        self.message.configure(text="Copied, clipboard clears in 30 seconds", text_color=theme.MUTED)
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
            show_message(self, "Change PIN", "PIN changed.")

    def _change_password(self):
        password = ask_secret(self, "Change password", "New password (letters and numbers, 6-32 characters)",
                              confirm=True, validator=security.validate_password)
        if password is not None:
            self._rekey(*security.change_password(self.config_data, self.keys, password))
            show_message(self, "Change password", "Password changed.")

    def lock(self):
        self._clear_clipboard()
        self.destroy()
        self.on_close(self.config_data)
