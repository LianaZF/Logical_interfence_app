"""Единые Tkinter-компоненты в стиле основной программы."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


BACKGROUND = "#FFFFFF"
ACCENT = "#217346"
FONT = ("Times New Roman", 13)
FONT_BOLD = ("Times New Roman", 13, "bold")
TABLE_FONT = ("Times New Roman", 8)
TABLE_FONT_BOLD = ("Times New Roman", 8, "bold")


def setup_styles(root: tk.Misc) -> None:
    """Повторяет настройки виджетов из первой программы."""

    style = ttk.Style(root)
    style.configure("TFrame", background=BACKGROUND)
    style.configure("TLabelframe", background=BACKGROUND)
    style.configure("TLabelframe.Label", background=BACKGROUND, font=FONT_BOLD)
    style.configure("TLabel", background=BACKGROUND, font=FONT)
    style.configure(
        "TButton",
        font=FONT,
        padding=(6, 4),
        anchor="center",
        justify="center",
        foreground="#000000",
    )
    style.map(
        "TButton",
        background=[("pressed", "#056C18"), ("active", "#056C18"), ("disabled", "#FFFEFE")],
        foreground=[("disabled", "#FFFFFF"), ("pressed", "#056C18")],
    )
    style.configure("TEntry", padding=2, font=FONT_BOLD)
    style.configure("TCombobox", padding=2, font=FONT)
    style.configure("TRadiobutton", background=BACKGROUND, font=FONT)
    style.configure(
        "TopPlain.TButton",
        font=("Times New Roman", 12, "bold"),
        padding=(10, 6),
        anchor="center",
        justify="center",
        relief="flat",
        background=BACKGROUND,
        foreground="#000000",
        borderwidth=1,
    )
    style.configure(
        "TopPlainActive.TButton",
        font=("Times New Roman", 12, "bold"),
        padding=(10, 6),
        anchor="center",
        justify="center",
        relief="flat",
        background="#D9D9D9",
        foreground="#056C18",
        borderwidth=1,
    )
    style.configure(
        "Rules.Treeview",
        background=BACKGROUND,
        fieldbackground=BACKGROUND,
        foreground="#000000",
        rowheight=18,
        font=TABLE_FONT,
    )
    style.configure("Rules.Treeview.Heading", font=TABLE_FONT_BOLD)
    style.map(
        "Rules.Treeview",
        background=[("selected", ACCENT)],
        foreground=[("selected", "#FFFFFF")],
    )


def make_button(parent, text: str, command=None, **options) -> ttk.Button:
    """Создаёт кнопку тем же способом, что и первая программа."""

    return ttk.Button(
        parent,
        text=text,
        command=command,
        takefocus=False,
        **options,
    )


def readonly_value(parent, variable: tk.StringVar, width: int = 8) -> ttk.Entry:
    """Создаёт поле результата, визуально совпадающее со строками главного окна."""

    return ttk.Entry(
        parent,
        textvariable=variable,
        state="readonly",
        justify="center",
        width=width,
    )
