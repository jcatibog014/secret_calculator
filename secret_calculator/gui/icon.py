"""App icon for the title bar, taskbar and dialogs."""

import sys
import tkinter as tk
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"
ICON_SIZES = (256, 48, 32, 16)
WINDOWS_APP_ID = "CountMeOut.Calculator"


def set_windows_app_id():
    """Without this, Windows shows the Python logo on the taskbar. Call before creating Tk."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)
    except (AttributeError, OSError):
        pass


def apply_app_icon(root):
    """Use the logo for this window and every dialog/window opened after it.

    Only iconphoto: on Windows, also calling iconbitmap(default=...) makes Tk fall back
    to the generic window icon.
    """
    try:
        images = [tk.PhotoImage(file=ASSETS / f"icon-{size}.png") for size in ICON_SIZES]
        root.iconphoto(True, *images)
        root._app_icons = images  # keep a reference so Tk doesn't drop the images
    except tk.TclError:
        pass  # a missing icon file should never stop the calculator from opening
