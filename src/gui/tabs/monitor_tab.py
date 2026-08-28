"""Pestana Monitor (P1): metricas en vivo de RAM por distro — ttkbootstrap moderno."""
from __future__ import annotations

import tkinter as tk

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from src.core.logger import get_logger
from src.gui.widgets import StatCard, StatusDot, SectionHeader, COLORS

log = get_logger("gui.monitor")


class MonitorTab(ttk.Frame):
    def __init__(self, master, ctx) -> None:
        super().__init__(master)
        self.ctx = ctx
        self._job: str | None = None
        self._build()
        self.refresh()

    def _build(self) -> None:
        # ════════════════════════════════════════════════════════════════════
        #  HEADER
        # ════════════════════════════════════════════════════════════════════
        header = ttk.Frame(self, bootstyle="dark")
        header.pack(fill="x", padx=12, pady=(10, 4))

        SectionHeader(header, text="\U0001f4ca Monitor de Recursos").pack(side="left")

        # ════════════════════════════════════════════════════════════════════
        #  STATS CARDS
        # ════════════════════════════════════════════════════════════════════
        cards_frame = ttk.Frame(self, bootstyle="dark")
        cards_frame.pack(fill="x", padx=12, pady=(0, 8))

        self.card_running = StatCard(cards_frame, value="0", label="Distros Running", bootstyle="success", icon="\u25b6")
        self.card_running.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.card_ram = StatCard(cards_frame, value="\u2014", label="RAM Total", bootstyle="info", icon="\U0001f4be")
        self.card_ram.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.card_cpu = StatCard(cards_frame, value="\u2014", label="CPU Total", bootstyle="warning", icon="\U0001f4bb")
        self.card_cpu.pack(side="left", fill="x", expand=True)

        ttk.Separator(self, bootstyle="secondary").pack(fill="x", padx=12, pady=4)

        # ════════════════════════════════════════════════════════════════════
        #  TABLA DE MONITOR
        # ════════════════════════════════════════════════════════════════════
        tree_frame = ttk.Frame(self, bootstyle="dark")
        tree_frame.pack(fill="both", expand=True, padx=12, pady=4)

        columns = [
            ("name", "Distro", 160),
            ("state", "Estado", 80),
            ("ram", "RAM usada/total", 150),
            ("pct", "%", 60),
            ("cpu", "CPU", 60),
            ("up", "Uptime (s)", 90),
        ]

        self.tree = ttk.Treeview(
            tree_frame,
            columns=[c[0] for c in columns],
            show="headings",
            height=14,
            bootstyle="primary",
        )
        for cid, title, width in columns:
            self.tree.heading(cid, text=title, anchor="w")
            self.tree.column(cid, width=width, anchor="w", minwidth=60)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview, bootstyle="round")
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        # Tags
        self.tree.tag_configure("running", foreground=COLORS["success"])
        self.tree.tag_configure("stopped", foreground=COLORS["muted"])
        self.tree.tag_configure("odd", background="#1a2030")
        self.tree.tag_configure("even", background="#1d2430")

        ttk.Separator(self, bootstyle="secondary").pack(fill="x", padx=12, pady=4)

        ttk.Label(
            self,
            text="Metricas de la VM compartida WSL2 (free -m). Se refresca cada 5s.",
            foreground=COLORS["muted"],
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=12, pady=(0, 4))

        # ════════════════════════════════════════════════════════════════════
        #  STATUS BAR
        # ════════════════════════════════════════════════════════════════════
        status_bar = ttk.Frame(self, bootstyle="dark")
        status_bar.pack(fill="x", padx=12, pady=(0, 6))

        self.status_dot = StatusDot(status_bar, state="stopped")
        self.status_dot.pack(side="left", padx=(0, 6))

        self.status_var = tk.StringVar(value="Cargando metricas...")
        ttk.Label(
            status_bar,
            textvariable=self.status_var,
            foreground=COLORS["muted"],
            font=("Segoe UI", 9),
            bootstyle="dark",
        ).pack(side="left")

        self.auto_refresh_label = ttk.Label(
            status_bar,
            text="Auto-refresh: 5s",
            foreground=COLORS["muted"],
            font=("Segoe UI", 8),
            bootstyle="dark",
        )
        self.auto_refresh_label.pack(side="right")

    def refresh(self) -> None:
        try:
            metrics = self.ctx.resources.get_metrics()
            try:
                self.tree.delete(*self.tree.get_children())
            except tk.TclError:
                pass

            running_count = 0
            total_ram = 0
            total_cpu = 0

            for idx, m in enumerate(metrics):
                is_running = m.running
                ram = f"{m.ram_used_mb}/{m.ram_total_mb} MB" if m.ram_total_mb else "-"
                state_display = "\u25cf RUN" if is_running else "\u25cb STOP"
                row_tag = "running" if is_running else "stopped"
                alt_tag = "odd" if idx % 2 else "even"

                self.tree.insert(
                    "", "end",
                    values=(
                        m.name,
                        state_display,
                        ram,
                        f"{m.ram_percent:.0f}%" if m.ram_percent is not None else "-",
                        m.cpus or "-",
                        m.uptime_s or 0,
                    ),
                    tags=(row_tag, alt_tag),
                )
                if is_running:
                    running_count += 1
                if m.ram_total_mb:
                    total_ram += m.ram_total_mb
                if m.cpus:
                    try:
                        total_cpu += int(m.cpus)
                    except (ValueError, TypeError):
                        pass

            # Update stats
            self.card_running.set_value(str(running_count))
            self.card_ram.set_value(f"{total_ram} MB" if total_ram else "\u2014")
            self.card_cpu.set_value(str(total_cpu) if total_cpu else "\u2014")

            self.status_var.set(f"{running_count} distros corriendo")
            self.status_dot.set_state("running" if running_count > 0 else "stopped")

        except Exception as exc:  # noqa: BLE001
            log.debug("monitor refresh fallo: %s", exc)
            self.status_var.set("Sin datos de metricas")
        finally:
            if self.winfo_exists():
                self._job = self.after(5000, self.refresh)

    def destroy(self) -> None:
        if self._job:
            self.after_cancel(self._job)
        super().destroy()
