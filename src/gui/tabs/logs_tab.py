"""Pestana Logs: cola circular del log en memoria + refresh — ttkbootstrap moderno."""
from __future__ import annotations

import tkinter as tk

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from src.core.logger import get_logger
from src.gui.widgets import StatCard, StatusDot, ActionButton, SectionHeader, COLORS

log = get_logger("gui.logs")


class LogsTab(ttk.Frame):
    def __init__(self, master, ctx) -> None:
        super().__init__(master)
        self.ctx = ctx
        self._build()
        self.refresh()

    def _build(self) -> None:
        # ════════════════════════════════════════════════════════════════════
        #  HEADER CON BOTONES
        # ════════════════════════════════════════════════════════════════════
        header = ttk.Frame(self, bootstyle="dark")
        header.pack(fill="x", padx=12, pady=(10, 4))

        SectionHeader(header, text="\U0001f4dc Logs del Sistema").pack(side="left")

        ActionButton(header, text="\U0001f504 Refrescar", bootstyle=INFO, command=self.refresh, width=14).pack(side="right", padx=4)

        # ════════════════════════════════════════════════════════════════════
        #  STATS CARDS
        # ════════════════════════════════════════════════════════════════════
        cards_frame = ttk.Frame(self, bootstyle="dark")
        cards_frame.pack(fill="x", padx=12, pady=(0, 8))

        self.card_total = StatCard(cards_frame, value="0", label="Total Eventos", bootstyle="info", icon="\U0001f4cb")
        self.card_total.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.card_types = StatCard(cards_frame, value="0", label="Tipos Diferentes", bootstyle="primary", icon="\U0001f4c2")
        self.card_types.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.card_latest = StatCard(cards_frame, value="\u2014", label="Ultimo Evento", bootstyle="success", icon="\u23f0")
        self.card_latest.pack(side="left", fill="x", expand=True)

        ttk.Separator(self, bootstyle="secondary").pack(fill="x", padx=12, pady=4)

        # ════════════════════════════════════════════════════════════════════
        #  EDITOR DE LOGS
        # ════════════════════════════════════════════════════════════════════
        editor_frame = ttk.Frame(self, bootstyle="dark")
        editor_frame.pack(fill="both", expand=True, padx=12, pady=4)

        self.text = tk.Text(
            editor_frame,
            wrap="none",
            font=("Consolas", 9),
            state="disabled",
            height=14,
            bg=COLORS["card"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            selectbackground=COLORS["primary"],
            relief="flat",
            padx=8,
            pady=8,
        )
        self.text.pack(fill="both", expand=True)

        hsb = ttk.Scrollbar(editor_frame, orient="horizontal", command=self.text.xview, bootstyle="round")
        vsb = ttk.Scrollbar(editor_frame, orient="vertical", command=self.text.yview, bootstyle="round")
        self.text.configure(xscrollcommand=hsb.set, yscrollcommand=vsb.set)

        # ════════════════════════════════════════════════════════════════════
        #  STATUS BAR
        # ════════════════════════════════════════════════════════════════════
        status_bar = ttk.Frame(self, bootstyle="dark")
        status_bar.pack(fill="x", padx=12, pady=(0, 6))

        self.status_dot = StatusDot(status_bar, state="stopped")
        self.status_dot.pack(side="left", padx=(0, 6))

        self.status_var = tk.StringVar(value="Cargando logs...")
        ttk.Label(
            status_bar,
            textvariable=self.status_var,
            foreground=COLORS["muted"],
            font=("Segoe UI", 9),
            bootstyle="dark",
        ).pack(side="left")

        ttk.Label(
            status_bar,
            text="Ultimos eventos del journal (SQLite)",
            foreground=COLORS["muted"],
            font=("Segoe UI", 8),
            bootstyle="dark",
        ).pack(side="right")

    def refresh(self) -> None:
        import datetime

        try:
            rows = self.ctx.metrics.list_events(200)
            self.text.configure(state="normal")
            self.text.delete("1.0", "end")
            for r in reversed(rows):
                ts = datetime.datetime.fromtimestamp(r["ts"]).strftime("%H:%M:%S")
                self.text.insert("end", f"{ts}  {r['type']:<22} {r['distro'] or '':<20} {r['message']}\n")
            self.text.configure(state="disabled")

            # Update stats
            total = len(rows)
            types = len({r["type"] for r in rows})
            latest = ""
            if rows:
                ts = datetime.datetime.fromtimestamp(rows[0]["ts"]).strftime("%H:%M:%S")
                latest = f"{ts}"

            self.card_total.set_value(str(total))
            self.card_types.set_value(str(types))
            self.card_latest.set_value(latest if latest else "\u2014")

            self.status_var.set(f"{total} eventos cargados")
            self.status_dot.set_state("running" if total > 0 else "stopped")

        except Exception as e:  # noqa: BLE001
            log.exception("refresh logs fallo")
            self.status_var.set(f"Error: {e}")
            self.status_dot.set_state("error")
