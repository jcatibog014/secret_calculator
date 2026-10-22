"""Design tokens: colours, fonts, icon glyphs and category styling."""

import sys
import tkinter.font as tkfont

import customtkinter as ctk

# ----- colours ------------------------------------------------------------------
BG = "#1B1F27"
SURFACE = "#232833"       # panels
SURFACE_ALT = "#2C3240"   # cards, inputs, digit keys
HOVER = "#373E4E"
BORDER = "#3A4152"
TEXT = "#E8EBF0"
MUTED = "#8C94A4"

AMBER = "#F2B33D"
AMBER_HOVER = "#DDA02F"
ON_AMBER = "#1B1F27"

BLUE_KEY, BLUE_KEY_HOVER, BLUE_TEXT = "#26324A", "#30405E", "#9DBBFF"
CORAL_KEY, CORAL_KEY_HOVER, CORAL = "#3F2A2D", "#4E3338", "#FF8A73"
RED_BUTTON, RED_BUTTON_HOVER, RED = "#40262A", "#552E34", "#FF7B72"

# ----- locker categories (keys are the stored values in locker.CATEGORIES) ----------
CATEGORY_COLORS = {
    "Account": "#5B9BFF",
    "PIN / Card": AMBER,
    "ID": "#2EC4B6",
    "Contact": "#A78BFA",
    "Note": "#F472B6",
    "Other": MUTED,
}
CATEGORY_LABELS = {
    "Account": "Accounts",
    "PIN / Card": "PINs & cards",
    "ID": "IDs",
    "Contact": "Contacts",
    "Note": "Notes",
    "Other": "Other",
}

# ----- sizes ----------------------------------------------------------------------
RADIUS = 12
BUTTON_HEIGHT = 44  # minimum for every clickable control
KEY_HEIGHT = 60

# ----- fonts ----------------------------------------------------------------------
FONT_FAMILY = "Segoe UI" if sys.platform == "win32" else "Helvetica"
LIGHT_FAMILY = "Segoe UI Light" if sys.platform == "win32" else FONT_FAMILY


def font(size=14, weight="normal", family=None):
    return ctk.CTkFont(family=family or FONT_FAMILY, size=size, weight=weight)


# ----- icon glyphs ------------------------------------------------------------------
ICON_FONTS = ("Segoe Fluent Icons", "Segoe MDL2 Assets")
ICON_GLYPHS = {"show": "", "hide": "", "copy": "", "add": "", "lock": ""}
FALLBACK_GLYPHS = {"show": "👁", "hide": "◡", "copy": "⧉", "add": "+", "lock": "🔒"}


_icon_family = []  # cached lookup: [family or None]


def icon(widget, name, size=16):
    """(text, font) for an icon button: Windows icon font when available, else a Unicode symbol."""
    if not _icon_family:
        families = set(tkfont.families(widget))
        _icon_family.append(next((f for f in ICON_FONTS if f in families), None))
    family = _icon_family[0]
    if family:
        return ICON_GLYPHS[name], font(size, family=family)
    return FALLBACK_GLYPHS[name], font(size)


def setup():
    ctk.set_appearance_mode("dark")
