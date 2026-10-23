"""Translate keyboard events into calculator keys. Kept free of Tkinter so it can be tested."""

import sys

DIGITS = "0123456789"

# On Windows, Tk sets this bit in event.state for "extended" keys: the dedicated
# Home/End/arrow/Insert/Delete keys. The numeric keypad's keys are not extended.
WINDOWS_EXTENDED_MASK = 0x40000

# With NumLock off, the numeric keypad sends navigation keys instead of digits.
# Windows reports them with the plain names (told apart from the dedicated keys by
# the extended bit); X11 uses KP_-prefixed names.
NUMPAD_NAVIGATION = {
    "Home": "7", "Up": "8", "Prior": "9",
    "Left": "4", "Clear": "5", "Right": "6",
    "End": "1", "Down": "2", "Next": "3",
    "Insert": "0", "Delete": ".",
}
KP_NAVIGATION = {
    "KP_Home": "7", "KP_Up": "8", "KP_Prior": "9",
    "KP_Left": "4", "KP_Begin": "5", "KP_Right": "6",
    "KP_End": "1", "KP_Down": "2", "KP_Next": "3",
    "KP_Insert": "0", "KP_Delete": ".",
}

# Named keys (Tk keysyms), including the numeric keypad.
KEYSYM_KEYS = {
    "Return": "=",
    "KP_Enter": "=",
    "BackSpace": "⌫",
    "Escape": "C",
    "Delete": "CE",
    "F9": "±",
    "KP_Add": "+",
    "KP_Subtract": "−",
    "KP_Multiply": "×",
    "KP_Divide": "÷",
    "KP_Decimal": ".",
    **{f"KP_{d}": d for d in DIGITS},
    **KP_NAVIGATION,
}

# Typed characters.
CHAR_KEYS = {
    "+": "+",
    "-": "−",
    "*": "×",
    "x": "×",
    "X": "×",
    "/": "÷",
    "=": "=",
    "%": "%",
    ".": ".",
    ",": ".",
    "c": "C",
    "C": "C",
    **{d: d for d in DIGITS},
}


def is_numpad_navigation(keysym, state, platform=sys.platform):
    """True for a numpad key pressed with NumLock off (Windows only; X11 uses KP_ names)."""
    return platform == "win32" and keysym in NUMPAD_NAVIGATION and not state & WINDOWS_EXTENDED_MASK


def key_for(keysym, char, state=0, platform=sys.platform):
    """Return the calculator key for a key press, or None if the key isn't used.

    The numpad types digits whether NumLock is on or off.
    """
    if is_numpad_navigation(keysym, state, platform):
        return NUMPAD_NAVIGATION[keysym]
    if keysym in KEYSYM_KEYS:
        return KEYSYM_KEYS[keysym]
    return CHAR_KEYS.get(char)
