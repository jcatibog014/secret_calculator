"""The calculator window. Looks and works like a normal calculator.

First run: the keypad is used to set the 8-digit PIN, then a dialog sets the password.
Afterwards: typing the PIN as a number opens a password prompt; the right password
opens the locker, anything else quietly returns to the calculator.
"""

import tkinter as tk

import customtkinter as ctk

from .. import APP_NAME, security, storage
from ..calculator import Calculator, parse_number
from ..history import load_history, save_history
from ..keymap import key_for
from ..locker import Locker, load_locker, save_locker
from . import theme
from .dialogs import ask_secret, show_message
from .icon import apply_app_icon, set_windows_app_id
from .locker_window import LockerWindow
from .widgets import clear_children, fit_window, make_clickable

KEYPAD = [
    [("%", "fn"), ("CE", "fn"), ("C", "clear"), ("⌫", "fn")],
    [("7", "digit"), ("8", "digit"), ("9", "digit"), ("÷", "op")],
    [("4", "digit"), ("5", "digit"), ("6", "digit"), ("×", "op")],
    [("1", "digit"), ("2", "digit"), ("3", "digit"), ("−", "op")],
    [("±", "digit"), ("0", "digit"), (".", "digit"), ("+", "op")],
]
# kind -> (background, hover, text colour, font size)
KEY_STYLES = {
    "digit": (theme.SURFACE_ALT, theme.HOVER, theme.TEXT, 22),
    "fn": (theme.BLUE_KEY, theme.BLUE_KEY_HOVER, theme.BLUE_TEXT, 19),
    "clear": (theme.CORAL_KEY, theme.CORAL_KEY_HOVER, theme.CORAL, 19),
    "op": (theme.SURFACE, theme.HOVER, theme.AMBER, 26),
    "equals": (theme.AMBER, theme.AMBER_HOVER, theme.ON_AMBER, 26),
}
KEY_WIDTH = 78
KEY_GAP = 8
FLASH_MS = 120
DISPLAY_SIZE, DISPLAY_SIZE_SMALL = 56, 34

SETUP_PIN_PROMPT = f"Welcome! Set a secret {security.PIN_LENGTH}-digit PIN, then press ="
SETUP_CONFIRM_PROMPT = "Type the same PIN again, then press ="


class CalculatorApp:
    def __init__(self, root):
        self.root = root
        self.calc = Calculator()
        self.history = load_history()
        self.config = storage.read_json(storage.config_path())
        self.setup_stage = None  # None, "pin" or "confirm"
        self.setup_buffer = ""
        self.new_pin = None
        self.buttons = {}  # key label -> (button, colour), for keyboard flashes

        root.title(APP_NAME)
        apply_app_icon(root)
        root.configure(fg_color=theme.BG)
        root.resizable(False, False)
        self._build_display_and_keypad()
        self._build_history_panel()
        fit_window(root)
        root.bind("<Key>", self._on_keyboard)
        for sequence in ("<Control-c>", "<Control-C>"):
            root.bind(sequence, self._copy_display)
        for sequence in ("<Control-v>", "<Control-V>"):
            root.bind(sequence, self._paste_number)

        if self.config is None:
            self._start_setup()
        self._refresh()
        self._take_focus()

    # ----- layout ---------------------------------------------------------
    def _build_display_and_keypad(self):
        left = ctk.CTkFrame(self.root, fg_color="transparent")
        left.grid(row=0, column=0, sticky="n", padx=(22, 14), pady=22)
        keypad_width = 4 * KEY_WIDTH + 3 * KEY_GAP

        self.expression_label = ctk.CTkLabel(left, text="", anchor="e", justify="right",
                                             text_color=theme.MUTED, font=theme.font(15),
                                             wraplength=keypad_width, height=44, width=keypad_width)
        self.expression_label.grid(row=0, column=0, columnspan=4, sticky="ew")
        self.display_font = theme.font(DISPLAY_SIZE, family=theme.LIGHT_FAMILY)
        self.display_label = ctk.CTkLabel(left, text="0", anchor="e", text_color=theme.TEXT,
                                          font=self.display_font, height=76, width=keypad_width)
        self.display_label.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(0, 14))

        for r, row in enumerate(KEYPAD, start=2):
            for c, (label, kind) in enumerate(row):
                self._button(left, label, kind).grid(row=r, column=c, padx=(0 if c == 0 else KEY_GAP, 0),
                                                     pady=(0, KEY_GAP))
        self._button(left, "=", "equals", width=keypad_width).grid(
            row=len(KEYPAD) + 2, column=0, columnspan=4, sticky="ew")

    def _button(self, parent, label, kind, width=KEY_WIDTH):
        color, hover, text_color, size = KEY_STYLES[kind]
        button = ctk.CTkButton(parent, text=label, width=width, height=theme.KEY_HEIGHT, corner_radius=16,
                               fg_color=color, hover_color=hover, text_color=text_color,
                               font=theme.font(size), command=lambda: self.on_key(label))
        self.buttons[label] = (button, color, hover)
        return button

    def _build_history_panel(self):
        right = ctk.CTkFrame(self.root, fg_color=theme.SURFACE, corner_radius=18, width=290)
        right.grid(row=0, column=1, sticky="nsew", padx=(0, 22), pady=22)
        right.grid_rowconfigure(1, weight=1)
        right.grid_propagate(False)
        right.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(right, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 6))
        ctk.CTkLabel(header, text="History", text_color=theme.TEXT, font=theme.font(17, "bold")
                     ).pack(side="left")
        ctk.CTkButton(header, text="Clear", width=64, height=theme.BUTTON_HEIGHT, corner_radius=theme.RADIUS,
                      fg_color="transparent", hover_color=theme.HOVER, text_color=theme.MUTED,
                      font=theme.font(13), command=self._clear_history).pack(side="right")

        self.history_frame = ctk.CTkScrollableFrame(right, fg_color="transparent",
                                                    scrollbar_button_color=theme.SURFACE_ALT,
                                                    scrollbar_button_hover_color=theme.HOVER)
        self.history_frame.grid(row=1, column=0, sticky="nsew", padx=(10, 6), pady=(0, 12))
        self.history_frame.grid_columnconfigure(0, weight=1)
        self._refresh_history()

    # ----- input -------------------------------------------------------------
    def _take_focus(self):
        """Give the calculator keyboard focus (at start, and after dialogs/locker close)."""
        self.root.focus_force()

    def _on_keyboard(self, event):
        key = key_for(event.keysym, event.char, event.state)
        if key is None:
            return None
        self._flash(key)
        self.on_key(key)
        return "break"

    def _flash(self, key):
        """Briefly highlight the on-screen button for a key typed on the keyboard."""
        if key not in self.buttons:
            return
        button, color, hover = self.buttons[key]
        button.configure(fg_color=hover)
        self.root.after(FLASH_MS, lambda: button.configure(fg_color=color))

    def _copy_display(self, _event=None):
        if self.setup_stage or self.calc.error:
            return "break"  # never put a PIN being set up on the clipboard
        self.root.clipboard_clear()
        self.root.clipboard_append(self.calc.display)
        return "break"

    def _paste_number(self, _event=None):
        if self.setup_stage:
            return "break"
        try:
            value = parse_number(self.root.clipboard_get())
        except tk.TclError:
            value = None  # clipboard empty or not text
        if value is not None:
            self.calc.load_value(str(value))
            self._refresh()
        return "break"

    def on_key(self, key):
        if self.setup_stage:
            self._setup_key(key)
            return
        calc = self.calc
        if key.isdigit():
            calc.press_digit(key)
        elif key == ".":
            calc.press_decimal()
        elif key == "=":
            entry = calc.press_equals()
            if entry:
                self.history.add(*entry)
                save_history(self.history)
                self._refresh_history()
        elif key == "C":
            calc.clear()
        elif key == "CE":
            calc.clear_entry()
        elif key == "⌫":
            calc.backspace()
        elif key == "%":
            calc.press_percent()
        elif key == "±":
            calc.toggle_sign()
        else:
            calc.press_operator(key)
        self._refresh()
        if key.isdigit():
            self._check_secret()

    def _set_display(self, text, color=theme.TEXT):
        self.display_font.configure(size=DISPLAY_SIZE if len(text) <= 10 else DISPLAY_SIZE_SMALL)
        self.display_label.configure(text=text, text_color=color)

    def _refresh(self):
        if self.setup_stage:
            self._set_display(self.setup_buffer or "0")
            return
        self._set_display(self.calc.display, theme.CORAL if self.calc.error else theme.TEXT)
        self.expression_label.configure(text=self.calc.expression)

    # ----- history -----------------------------------------------------------
    def _refresh_history(self):
        clear_children(self.history_frame)
        if not len(self.history):
            ctk.CTkLabel(self.history_frame, text="No calculations yet", text_color=theme.MUTED,
                         font=theme.font(13)).grid(row=0, column=0, pady=24)
            return
        for index, item in enumerate(self.history):
            card = ctk.CTkFrame(self.history_frame, fg_color=theme.SURFACE_ALT, corner_radius=theme.RADIUS)
            card.grid(row=index, column=0, sticky="ew", pady=(0, 8))
            ctk.CTkLabel(card, text=item["expression"], text_color=theme.MUTED, font=theme.font(12),
                         anchor="e", height=18).pack(fill="x", padx=14, pady=(10, 0))
            ctk.CTkLabel(card, text=item["result"], text_color=theme.TEXT, font=theme.font(19, "bold"),
                         anchor="e", height=26).pack(fill="x", padx=14, pady=(0, 10))
            make_clickable(card, lambda i=index: self._on_history_pick(i), theme.SURFACE_ALT, theme.HOVER)

    def _on_history_pick(self, index):
        if not self.setup_stage:
            self.calc.load_value(self.history.items[index]["result"])
            self._refresh()

    def _clear_history(self):
        self.history.clear()
        save_history(self.history)
        self._refresh_history()

    # ----- first-run setup ------------------------------------------------------
    def _start_setup(self, message=SETUP_PIN_PROMPT):
        self.setup_stage = "pin"
        self.setup_buffer = ""
        self.new_pin = None
        self.expression_label.configure(text=message, text_color=theme.AMBER)

    def _setup_key(self, key):
        if key.isdigit():
            if len(self.setup_buffer) < security.PIN_LENGTH:
                self.setup_buffer += key
        elif key == "⌫":
            self.setup_buffer = self.setup_buffer[:-1]
        elif key in ("C", "CE"):
            self.setup_buffer = ""
        elif key == "=":
            self._submit_setup()
        self._refresh()

    def _submit_setup(self):
        typed, self.setup_buffer = self.setup_buffer, ""
        if self.setup_stage == "pin":
            error = security.validate_pin(typed)
            if error:
                self.expression_label.configure(text=f"{error}. {SETUP_PIN_PROMPT}")
                return
            self.new_pin = typed
            self.setup_stage = "confirm"
            self.expression_label.configure(text=SETUP_CONFIRM_PROMPT)
            return
        if typed != self.new_pin:
            self._start_setup(f"PINs didn't match. {SETUP_PIN_PROMPT}")
            return
        self._refresh()
        self.root.after(50, self._setup_password)

    def _setup_password(self):
        pin = self.new_pin
        password = ask_secret(
            self.root, "Set password",
            "Second lock: choose a password (letters and numbers, 6-32 characters).\n"
            "After typing your PIN you will be asked for this password.",
            confirm=True, validator=lambda value: security.validate_password(value, pin))
        self._take_focus()
        if password is None:
            self._start_setup(f"Setup cancelled. {SETUP_PIN_PROMPT}")
            self._refresh()
            return
        config = security.create_credentials(pin, password)
        save_locker(Locker(), security.unlock_keys(config, pin, password))
        storage.write_json(storage.config_path(), config)
        self.config = config
        self.setup_stage = None
        self.new_pin = None
        self.calc.clear()
        self.expression_label.configure(text_color=theme.MUTED)
        self._refresh()
        show_message(self.root, "All set", "Your secret is ready.\n\nUse the calculator normally. "
                     "Whenever you type your PIN, you'll be asked for your password.")
        self._take_focus()

    # ----- secret unlock --------------------------------------------------------
    def _check_secret(self):
        digits = self.calc.typed_digits
        if (len(digits) == security.PIN_LENGTH and self.config
                and security.verify_pin(digits, self.config)):
            self.calc.clear()
            self._refresh()
            self.root.after(50, lambda: self._ask_password(digits))

    def _ask_password(self, pin):
        password = ask_secret(self.root, "Password", "Enter password")
        if password is None or not security.verify_password(password, self.config):
            self._take_focus()
            return  # quietly back to the calculator
        keys = security.unlock_keys(self.config, pin, password)
        try:
            locker = load_locker(keys)
        except security.InvalidToken:
            show_message(self.root, "Locker", "The locker file could not be opened.")
            return
        self.root.withdraw()
        LockerWindow(self.root, locker, keys, self.config, on_close=self._on_locker_closed)

    def _on_locker_closed(self, config):
        self.config = config  # may hold a new PIN or password
        self.calc.clear()
        self._refresh()
        self.root.deiconify()
        self._take_focus()


def main():
    set_windows_app_id()
    theme.setup()
    root = ctk.CTk()
    CalculatorApp(root)
    root.mainloop()
