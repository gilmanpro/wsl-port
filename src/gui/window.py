"""Ventana principal con pestanas (seccion 7.2 del plan)."""
from __future__ import annotations

import tkinter as tk

import ttkbootstrap as ttk

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
        self.root.geometry("900x560")
        self.root.minsize(760, 420)
        self._build()

    def _build(self) -> None:
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True)

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
            "dashboard": "Dashboard",
            "resources": "Recursos",
            "monitor": "Monitor",
            "forwards": "Forwards",
            "tunnels": "Tunnels",
            "publish": "Publicar",
            "config": "Configuracion",
            "autostart": "Autoarranque",
            "scheduler": "Programador",
            "profiles": "Perfiles",
            "logs": "Logs",
            "settings": "Ajustes",
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

    def run(self) -> None:
        self.root.mainloop()

    def close(self) -> None:
        try:
            self.root.destroy()
        except tk.TclError:
            pass
