"""The calculator window. Looks and works like a normal calculator.

First run: the keypad is used to set the 8-digit PIN, then a dialog sets the password.
Afterwards: typing the PIN as a number opens a password prompt; the right password
opens the locker, anything else quietly returns to the calculator.
"""

import tkinter as tk
from tkinter import messagebox

from .. import security, storage
from ..calculator import Calculator, parse_number
from ..history import load_history, save_history
from ..keymap import key_for
from ..locker import Locker, load_locker, save_locker
from . import theme
from .locker_window import LockerWindow
from .password_dialog import ask_secret

KEYPAD = [
    [("%", "fn"), ("CE", "fn"), ("C", "fn"), ("⌫", "fn")],
    [("7", "digit"), ("8", "digit"), ("9", "digit"), ("÷", "op")],
    [("4", "digit"), ("5", "digit"), ("6", "digit"), ("×", "op")],
    [("1", "digit"), ("2", "digit"), ("3", "digit"), ("−", "op")],
    [("±", "fn"), ("0", "digit"), (".", "digit"), ("+", "op")],
]
BUTTON_COLORS = {"digit": theme.DIGIT, "fn": theme.FUNCTION, "op": theme.OPERATOR}
FLASH_MS = 120

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

        root.title("Calculator")
        root.configure(bg=theme.BG)
        root.resizable(False, False)
        self._build_display_and_keypad()
        self._build_history_panel()
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
        left = tk.Frame(self.root, bg=theme.BG, padx=10, pady=10)
        left.grid(row=0, column=0, sticky="n")

        self.expression_label = tk.Label(left, text="", anchor="e", justify="right", bg=theme.BG,
                                         fg=theme.MUTED, font=theme.EXPRESSION_FONT, wraplength=300,
                                         height=2)
        self.expression_label.grid(row=0, column=0, columnspan=4, sticky="ew")
        self.display_label = tk.Label(left, text="0", anchor="e", bg=theme.BG, fg=theme.TEXT,
                                      font=theme.DISPLAY_FONT, width=14)
        self.display_label.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(0, 8))

        for r, row in enumerate(KEYPAD, start=2):
            for c, (label, kind) in enumerate(row):
                self._button(left, label, BUTTON_COLORS[kind]).grid(row=r, column=c, padx=3, pady=3)
        self._button(left, "=", theme.OPERATOR, width=19).grid(
            row=len(KEYPAD) + 2, column=0, columnspan=4, padx=3, pady=3, sticky="ew")

    def _button(self, parent, label, color, width=4):
        # takefocus=0: buttons never hold focus, so Space/Enter can't also press a focused button.
        button = tk.Button(parent, text=label, width=width, height=1, font=theme.BUTTON_FONT, bg=color,
                           fg=theme.TEXT, activebackground=theme.MUTED, activeforeground=theme.TEXT,
                           relief="flat", bd=0, takefocus=0, command=lambda: self.on_key(label))
        self.buttons[label] = (button, color)
        return button

    def _build_history_panel(self):
        right = tk.Frame(self.root, bg=theme.PANEL, padx=10, pady=10)
        right.grid(row=0, column=1, sticky="ns")
        tk.Label(right, text="History", bg=theme.PANEL, fg=theme.TEXT,
                 font=(theme.FONT, 12, "bold")).pack(anchor="w")
        self.history_list = tk.Listbox(right, width=28, height=17, bg=theme.PANEL, fg=theme.TEXT,
                                       selectbackground=theme.FUNCTION, highlightthickness=0,
                                       relief="flat", font=theme.BODY_FONT, activestyle="none")
        self.history_list.pack(fill="both", expand=True, pady=6)
        self.history_list.bind("<<ListboxSelect>>", self._on_history_pick)
        tk.Button(right, text="Clear history", command=self._clear_history, relief="flat",
                  bg=theme.FUNCTION, fg=theme.TEXT).pack(fill="x")
        self._refresh_history()

    # ----- input -------------------------------------------------------------
    def _take_focus(self):
        """Give the calculator keyboard focus (at start, and after dialogs/locker close)."""
        self.root.focus_force()

    def _on_keyboard(self, event):
        key = key_for(event.keysym, event.char)
        if key is None:
            return None
        self._flash(key)
        self.on_key(key)
        return "break"

    def _flash(self, key):
        """Briefly highlight the on-screen button for a key typed on the keyboard."""
        if key not in self.buttons:
            return
        button, color = self.buttons[key]
        button.config(bg=theme.MUTED)
        self.root.after(FLASH_MS, lambda: button.config(bg=color))

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

    def _refresh(self):
        if self.setup_stage:
            self.display_label.config(text=self.setup_buffer or "0")
            return
        text = self.calc.display
        size = 34 if len(text) <= 12 else 22
        self.display_label.config(text=text, font=(theme.FONT, size))
        self.expression_label.config(text=self.calc.expression)

    # ----- history -----------------------------------------------------------
    def _refresh_history(self):
        self.history_list.delete(0, "end")
        for item in self.history:
            self.history_list.insert("end", f"{item['expression']} = {item['result']}")

    def _on_history_pick(self, _event):
        selection = self.history_list.curselection()
        if selection and not self.setup_stage:
            self.calc.load_value(self.history.items[selection[0]]["result"])
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
        self.expression_label.config(text=message, fg=theme.OPERATOR)

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
                self.expression_label.config(text=f"{error}. {SETUP_PIN_PROMPT}")
                return
            self.new_pin = typed
            self.setup_stage = "confirm"
            self.expression_label.config(text=SETUP_CONFIRM_PROMPT)
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
        self.expression_label.config(fg=theme.MUTED)
        self._refresh()
        messagebox.showinfo("All set", "Your secret is ready.\n\nUse the calculator normally. "
                            "Whenever you type your PIN, you'll be asked for your password.",
                            parent=self.root)
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
            messagebox.showerror("Locker", "The locker file could not be opened.", parent=self.root)
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
    root = tk.Tk()
    CalculatorApp(root)
    root.mainloop()
