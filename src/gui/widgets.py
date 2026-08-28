"""Widgets reutilizables con ttkbootstrap: StatCard, StatusDot, ActionButton, SectionHeader, make_tree."""
from __future__ import annotations

import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *


# ── Colores del tema darkly ──────────────────────────────────────────────
COLORS = {
    "bg": "#14181f",
    "card": "#1d2430",
    "border": "#2a3344",
    "text": "#e8eaf0",
    "muted": "#8b93a3",
    "success": "#2ecc71",
    "warning": "#f39c12",
    "danger": "#e74c3c",
    "info": "#3498db",
    "primary": "#3498db",
}


class StatCard(ttk.Frame):
    """Tarjeta de estadísticas con número grande, label e icono de color."""

    def __init__(
        self,
        master,
        value: str = "0",
        label: str = "",
        bootstyle: str = "info",
        icon: str = "",
        **kw,
    ) -> None:
        super().__init__(master, bootstyle="dark", **kw)
        self.configure(padding=(16, 12))

        self._value_var = tk.StringVar(value=value)
        self._label_var = tk.StringVar(value=label)

        # Color map for foreground
        color_map = {
            "success": COLORS["success"],
            "warning": COLORS["warning"],
            "danger": COLORS["danger"],
            "info": COLORS["info"],
            "primary": COLORS["primary"],
            "secondary": COLORS["muted"],
        }
        fg_color = color_map.get(bootstyle, COLORS["info"])

        # Top row: icon + value
        top = ttk.Frame(self, bootstyle="dark")
        top.pack(fill="x")

        if icon:
            ttk.Label(
                top, text=icon, font=("Segoe UI", 18),
                foreground=fg_color, bootstyle="dark",
            ).pack(side="left", padx=(0, 8))

        ttk.Label(
            top,
            textvariable=self._value_var,
            font=("Segoe UI", 26, "bold"),
            foreground=fg_color,
            bootstyle="dark",
        ).pack(side="left")

        # Bottom: label
        ttk.Label(
            self,
            textvariable=self._label_var,
            font=("Segoe UI", 9),
            foreground=COLORS["muted"],
            bootstyle="dark",
        ).pack(anchor="w", pady=(4, 0))

    def set_value(self, value: str) -> None:
        self._value_var.set(value)

    def set_label(self, label: str) -> None:
        self._label_var.set(label)


class StatusDot(tk.Canvas):
    """Dot de estado: verde (running), gris (stopped), rojo (error)."""

    _COLORS = {
        "running": COLORS["success"],
        "active": COLORS["success"],
        "stopped": COLORS["muted"],
        "inactive": COLORS["muted"],
        "error": COLORS["danger"],
    }
    RADIUS = 5

    def __init__(self, master, state: str = "stopped", **kw) -> None:
        size = self.RADIUS * 2 + 2
        super().__init__(master, width=size, height=size, highlightthickness=0, bg=COLORS["card"], **kw)
        self._dot_id = None
        self.set_state(state)

    def set_state(self, state: str) -> None:
        color = self._COLORS.get(state.lower(), COLORS["muted"])
        self.delete("all")
        cx = self.RADIUS + 1
        cy = self.RADIUS + 1
        self._dot_id = self.create_oval(
            cx - self.RADIUS, cy - self.RADIUS,
            cx + self.RADIUS, cy + self.RADIUS,
            fill=color, outline="", width=0,
        )


class ActionButton(ttk.Button):
    """Botón de acción con icono y bootstyle predefinido."""

    def __init__(self, master, text: str = "", bootstyle: str = "secondary", command=None, width: int = 12, **kw) -> None:
        super().__init__(
            master,
            text=text,
            bootstyle=bootstyle,
            command=command,
            width=width,
            **kw,
        )


class SectionHeader(ttk.Label):
    """Label de sección con estilo de encabezado."""

    def __init__(self, master, text: str = "", **kw) -> None:
        super().__init__(
            master,
            text=text,
            font=("Segoe UI", 14, "bold"),
            foreground=COLORS["text"],
            **kw,
        )


def make_tree(parent, columns: list[tuple[str, str, int]], height: int = 12, bootstyle: str = "primary") -> ttk.Treeview:
    """columns: [(id, titulo, ancho)]. Devuelve Treeview con scrollbars ttkbootstrap."""
    frame = ttk.Frame(parent, bootstyle="dark")
    frame.pack(fill="both", expand=True, padx=12, pady=4)
    tree = ttk.Treeview(
        frame,
        columns=[c[0] for c in columns],
        show="headings",
        height=height,
        bootstyle=bootstyle,
    )
    for cid, title, width in columns:
        tree.heading(cid, text=title, anchor="w")
        tree.column(cid, width=width, anchor="w", minwidth=60)
    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview, bootstyle="round")
    tree.configure(yscrollcommand=vsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)
    return tree


def status_text(state: str) -> str:
    return "\u25cf RUNNING" if state.lower() == "running" else "\u25cb stopped"


def status_color(state: str) -> str:
    """Return foreground color for a given state."""
    if state.lower() in ("running", "active", "connected"):
        return COLORS["success"]
    elif state.lower() in ("error",):
        return COLORS["danger"]
    return COLORS["muted"]
