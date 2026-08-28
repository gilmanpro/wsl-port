"""Pestana Monitor (P1): metricas en vivo de RAM por distro."""
from __future__ import annotations

import logging
import tkinter as tk
from tkinter import ttk

from src.gui.widgets import make_tree

log = logging.getLogger("wslmanager.monitor_tab")


class MonitorTab(ttk.Frame):
    def __init__(self, master, ctx) -> None:
        super().__init__(master)
        self.ctx = ctx
        self._build()
        self._job: str | None = None
        self.refresh()

    def _build(self) -> None:
        self.tree = make_tree(
            self,
            [("name", "Distro", 160), ("state", "Estado", 80), ("ram", "RAM usada/total", 150), ("pct", "%", 60), ("cpu", "CPU", 60), ("up", "Uptime (s)", 90)],
        )
        ttk.Label(self, text="Metricas de la VM compartida WSL2 (free -m). Se refresca cada 5s.", foreground="#888").pack(anchor="w", padx=8, pady=(0, 4))

    def refresh(self) -> None:
        try:
            metrics = self.ctx.resources.get_metrics()
            self.tree.delete(*self.tree.get_children())
            for m in metrics:
                ram = f"{m.ram_used_mb}/{m.ram_total_mb} MB" if m.ram_total_mb else "-"
                self.tree.insert(
                    "", "end",
                    values=(m.name, "RUN" if m.running else "STOP", ram, f"{m.ram_percent:.0f}%" if m.ram_percent is not None else "-", m.cpus or "-", m.uptime_s or 0),
                )
        except Exception as exc:  # noqa: BLE001
            log.debug("monitor refresh fallo: %s", exc)
        finally:
            if self.winfo_exists():
                self._job = self.after(5000, self.refresh)

    def destroy(self) -> None:
        if self._job:
            self.after_cancel(self._job)
        super().destroy()
