"""Ventana principal con pestanas (seccion 7.2 del plan) — ttkbootstrap darkly."""
from __future__ import annotations

import tkinter as tk

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from src.gui.tabs import (
    autostart_tab,
    config_tab,
    dashboard_tab,
    forwards_tab,
    logs_tab,
    monitor_tab,
    profiles_tab,
    publish_tab,
    resources_tab,
    scheduler_tab,
    settings_tab,
    tunnels_tab,
)


class MainWindow:
    def __init__(self, ctx, theme: str = "darkly") -> None:
        self.ctx = ctx
        self.root = ttk.Window(themename=theme, title="WSL Manager")
        self.root.geometry("1100x700")
        self.root.minsize(900, 550)
        self.root.place_window_center()
        self._build_status_bar()
        self._build()

    def _build_status_bar(self) -> None:
        """Barra de estado inferior con info de la app."""
        self.status_var = tk.StringVar(value="WSL Manager v0.1.0 | Listo")
        self.status_bar = ttk.Frame(self.root, bootstyle="dark")
        self.status_bar.pack(fill="x", side="bottom")
        ttk.Label(
            self.status_bar,
            textvariable=self.status_var,
            font=("Segoe UI", 9),
            foreground="#8b93a3",
            bootstyle="dark",
        ).pack(side="left", padx=10, pady=3)
        ttk.Separator(self.status_bar, bootstyle="secondary").pack(fill="x")

    def _build(self) -> None:
        nb = ttk.Notebook(self.root, bootstyle="dark")
        nb.pack(fill="both", expand=True, padx=4, pady=(4, 0))

        self.tabs = {
            "dashboard": dashboard_tab.DashboardTab(nb, self.ctx),
            "resources": resources_tab.ResourcesTab(nb, self.ctx),
            "monitor": monitor_tab.MonitorTab(nb, self.ctx),
            "forwards": forwards_tab.ForwardsTab(nb, self.ctx),
            "tunnels": tunnels_tab.TunnelsTab(nb, self.ctx),
            "publish": publish_tab.PublishTab(nb, self.ctx),
            "config": config_tab.ConfigTab(nb, self.ctx),
            "autostart": autostart_tab.AutoStartTab(nb, self.ctx),
            "scheduler": scheduler_tab.SchedulerTab(nb, self.ctx),
            "profiles": profiles_tab.ProfilesTab(nb, self.ctx),
            "logs": logs_tab.LogsTab(nb, self.ctx),
            "settings": settings_tab.SettingsTab(nb, self.ctx),
        }
        labels = {
            "dashboard": "\U0001f4ca Dashboard",
            "resources": "\U0001f4bb Recursos",
            "monitor": "\U0001f4e1 Monitor",
            "forwards": "\U0001f504 Forwards",
            "tunnels": "\U0001f50c Tunnels",
            "publish": "\U0001f310 Publicar",
            "config": "\u2699\ufe0f Config",
            "autostart": "\u26a1 Autoarranque",
            "scheduler": "\U0001f4c5 Programador",
            "profiles": "\U0001f464 Perfiles",
            "logs": "\U0001f4dc Logs",
            "settings": "\U0001f527 Ajustes",
        }
        for key, frame in self.tabs.items():
            nb.add(frame, text=labels[key])

    def show(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def hide(self) -> None:
        self.root.withdraw()

    def toggle(self) -> None:
        if self.root.state() == "normal" and self.root.winfo_viewable():
            self.hide()
        else:
            self.show()

    def refresh_dashboard(self) -> None:
        if "dashboard" in self.tabs:
            self.tabs["dashboard"].refresh()

    def set_status(self, text: str) -> None:
        """Update the bottom status bar text."""
        self.status_var.set(text)

    def run(self) -> None:
        self.root.mainloop()

    def close(self) -> None:
        try:
            self.root.destroy()
        except tk.TclError:
            pass
