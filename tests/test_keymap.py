import pytest

from secret_calculator.keymap import WINDOWS_EXTENDED_MASK, key_for

EXTENDED = WINDOWS_EXTENDED_MASK


@pytest.mark.parametrize("keysym, char, expected", [
    ("7", "7", "7"), ("plus", "+", "+"), ("minus", "-", "−"), ("asterisk", "*", "×"),
    ("x", "x", "×"), ("slash", "/", "÷"), ("equal", "=", "="), ("percent", "%", "%"),
    ("period", ".", "."), ("comma", ",", "."), ("c", "c", "C"),
    ("Return", "\r", "="), ("BackSpace", "\b", "⌫"), ("Escape", "\x1b", "C"), ("F9", "", "±"),
])
def test_main_keyboard(keysym, char, expected):
    assert key_for(keysym, char) == expected


def test_dedicated_delete_key_is_clear_entry():
    assert key_for("Delete", "", EXTENDED, platform="win32") == "CE"
    assert key_for("Delete", "", 0, platform="linux") == "CE"


@pytest.mark.parametrize("keysym, expected", [
    ("KP_0", "0"), ("KP_7", "7"), ("KP_Add", "+"), ("KP_Subtract", "−"), ("KP_Multiply", "×"),
    ("KP_Divide", "÷"), ("KP_Decimal", "."), ("KP_Enter", "="),
])
def test_numpad_without_char(keysym, expected):
    # Some systems send keypad keys with no character at all.
    assert key_for(keysym, "") == expected


# What Windows really sends for the numpad with NumLock OFF (captured with SendInput).
@pytest.mark.parametrize("keysym, expected", [
    ("Home", "7"), ("Up", "8"), ("Prior", "9"), ("Left", "4"), ("Clear", "5"), ("Right", "6"),
    ("End", "1"), ("Down", "2"), ("Next", "3"), ("Insert", "0"), ("Delete", "."),
])
def test_windows_numpad_with_numlock_off(keysym, expected):
    assert key_for(keysym, "", 0, platform="win32") == expected


@pytest.mark.parametrize("keysym", ["Home", "End", "Up", "Down", "Left", "Right", "Prior", "Next", "Insert"])
def test_dedicated_navigation_keys_do_nothing(keysym):
    # The real Home/End/arrow keys carry the extended bit and must not type digits.
    assert key_for(keysym, "", EXTENDED, platform="win32") is None


@pytest.mark.parametrize("keysym", ["Home", "Up", "Insert"])
def test_navigation_names_ignored_off_windows(keysym):
    assert key_for(keysym, "", 0, platform="linux") is None


@pytest.mark.parametrize("keysym, expected", [
    ("KP_Home", "7"), ("KP_Up", "8"), ("KP_Prior", "9"), ("KP_Left", "4"), ("KP_Begin", "5"),
    ("KP_Right", "6"), ("KP_End", "1"), ("KP_Down", "2"), ("KP_Next", "3"), ("KP_Insert", "0"),
    ("KP_Delete", "."),
])
def test_x11_numpad_with_numlock_off(keysym, expected):
    assert key_for(keysym, "", 0, platform="linux") == expected


@pytest.mark.parametrize("keysym, char", [
    ("a", "a"), ("Shift_L", ""), ("Control_L", ""), ("c", "\x03"), ("v", "\x16"), ("Tab", "\t"),
    ("space", " "), ("Num_Lock", ""),
])
def test_unused_keys(keysym, char):
    assert key_for(keysym, char) is None
