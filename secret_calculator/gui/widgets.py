"""Small helpers shared by the windows."""

import tkinter as tk

import customtkinter as ctk
from customtkinter import CTkBaseClass


def make_clickable(frame, command, normal_color, hover_color):
    """Make a frame and everything inside it act like one button with a hover colour."""

    def raw_widgets(widget):
        # CTk widgets draw on plain tkinter widgets; bind those once each. tk.Misc's version
        # is used because CTkFrame.winfo_children() hides the frame's own canvas.
        for child in tk.Misc.winfo_children(widget):
            if not isinstance(child, CTkBaseClass):
                yield child
            yield from raw_widgets(child)

    def on_enter(_event):
        frame.configure(fg_color=hover_color)

    def on_leave(_event):
        # Moving between child widgets fires Leave too: only reset when the pointer left the frame.
        inside = frame.winfo_containing(*frame.winfo_pointerxy())
        if inside is None or not str(inside).startswith(str(frame)):
            frame.configure(fg_color=normal_color)

    def on_click(_event):
        # Run after the click finishes: the command may rebuild (destroy) this very frame.
        frame.winfo_toplevel().after_idle(command)

    for widget in raw_widgets(frame):
        widget.bind("<Button-1>", on_click, add="+")
        widget.bind("<Enter>", on_enter, add="+")
        widget.bind("<Leave>", on_leave, add="+")
        widget.configure(cursor="hand2")


def fit_window(window, min_width=0, min_height=0):
    """Size a CTk window to its content (CTk windows otherwise start at a fixed size)."""
    window.update_idletasks()
    scale = window._get_window_scaling()
    width = max(min_width, round(window.winfo_reqwidth() / scale))
    height = max(min_height, round(window.winfo_reqheight() / scale))
    window.geometry(f"{width}x{height}")
    return width, height


def center_over(window, parent):
    """Place a dialog over the middle of its parent window."""
    window.update_idletasks()
    if not parent.winfo_viewable():
        return
    x = parent.winfo_rootx() + (parent.winfo_width() - window.winfo_width()) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - window.winfo_height()) // 3
    window.geometry(f"+{max(x, 0)}+{max(y, 0)}")


def clear_children(frame):
    for child in frame.winfo_children():
        child.destroy()


def set_entry(entry, value):
    entry.delete(0, "end")
    if value:
        entry.insert(0, value)


__all__ = ["ctk", "make_clickable", "fit_window", "center_over", "clear_children", "set_entry"]
