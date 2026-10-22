import pytest

from secret_calculator.keymap import key_for


@pytest.mark.parametrize("keysym, char, expected", [
    ("7", "7", "7"), ("plus", "+", "+"), ("minus", "-", "−"), ("asterisk", "*", "×"),
    ("x", "x", "×"), ("slash", "/", "÷"), ("equal", "=", "="), ("percent", "%", "%"),
    ("period", ".", "."), ("comma", ",", "."), ("c", "c", "C"),
    ("Return", "\r", "="), ("BackSpace", "\b", "⌫"), ("Escape", "\x1b", "C"),
    ("Delete", "", "CE"), ("F9", "", "±"),
])
def test_main_keyboard(keysym, char, expected):
    assert key_for(keysym, char) == expected


@pytest.mark.parametrize("keysym, expected", [
    ("KP_0", "0"), ("KP_7", "7"), ("KP_Add", "+"), ("KP_Subtract", "−"), ("KP_Multiply", "×"),
    ("KP_Divide", "÷"), ("KP_Decimal", "."), ("KP_Enter", "="),
])
def test_numpad_without_char(keysym, expected):
    # Some systems send keypad keys with no character at all.
    assert key_for(keysym, "") == expected


@pytest.mark.parametrize("keysym, char", [
    ("a", "a"), ("Shift_L", ""), ("Control_L", ""), ("c", "\x03"), ("v", "\x16"), ("Tab", "\t"),
    ("KP_Home", ""), ("space", " "),
])
def test_unused_keys(keysym, char):
    assert key_for(keysym, char) is None
