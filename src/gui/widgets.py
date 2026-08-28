"""Widgets reutilizables: tabla con scrollbar y helpers de refresh."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def make_tree(parent, columns: list[tuple[str, str, int]]) -> ttk.Treeview:
    """columns: [(id, titulo, ancho)]. Devuelve Treeview con scrollbars."""
    frame = ttk.Frame(parent)
    frame.pack(fill="both", expand=True, padx=6, pady=6)
    tree = ttk.Treeview(frame, columns=[c[0] for c in columns], show="headings", height=10)
    for cid, title, width in columns:
        tree.heading(cid, text=title)
        tree.column(cid, width=width, anchor="w")
    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)
    return tree


def status_text(state: str) -> str:
    return "● RUNNING" if state.lower() == "running" else "○ stopped"
