"""Translate keyboard events into calculator keys. Kept free of Tkinter so it can be tested."""

DIGITS = "0123456789"

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


def key_for(keysym, char):
    """Return the calculator key for a key press, or None if the key isn't used."""
    if keysym in KEYSYM_KEYS:
        return KEYSYM_KEYS[keysym]
    return CHAR_KEYS.get(char)
