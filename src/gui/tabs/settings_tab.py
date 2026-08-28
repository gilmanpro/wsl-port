"""Pestana Ajustes: tema, comportamiento, API y MCP."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk


class SettingsTab(ttk.Frame):
    def __init__(self, master, ctx) -> None:
        super().__init__(master)
        self.ctx = ctx
        self._build()

    def _build(self) -> None:
        ui = self.ctx.config.ui
        api = self.ctx.config.api

        form = ttk.Frame(self)
        form.pack(fill="x", padx=12, pady=12)

        self.theme_var = tk.StringVar(value=ui.theme)
        ttk.Label(form, text="Tema:").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Combobox(form, textvariable=self.theme_var, values=["darkly", "superhero", "cyborg", "cosmo", "flatly", "journal"], state="readonly", width=14).grid(row=0, column=1, sticky="w", padx=6)

        self.min_var = tk.BooleanVar(value=ui.start_minimized)
        ttk.Checkbutton(form, text="Iniciar minimizado (solo tray)", variable=self.min_var).grid(row=1, column=0, columnspan=2, sticky="w", pady=3)

        self.tray_var = tk.BooleanVar(value=ui.close_to_tray)
        ttk.Checkbutton(form, text="Cerrar ventana -> minimizar a tray", variable=self.tray_var).grid(row=2, column=0, columnspan=2, sticky="w", pady=3)

        self.stop_var = tk.BooleanVar(value=self.ctx.config.on_close.stop_distros)
        ttk.Checkbutton(form, text="Al salir: detener todas las distros", variable=self.stop_var).grid(row=3, column=0, columnspan=2, sticky="w", pady=3)

        ttk.Separator(form).grid(row=4, column=0, columnspan=2, sticky="ew", pady=8)

        self.api_var = tk.BooleanVar(value=api.enabled)
        ttk.Checkbutton(form, text="API REST habilitada (loopback)", variable=self.api_var).grid(row=5, column=0, columnspan=2, sticky="w", pady=3)
        self.api_port_var = tk.StringVar(value=str(api.port))
        ttk.Label(form, text="Puerto API:").grid(row=6, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.api_port_var, width=8).grid(row=6, column=1, sticky="w", padx=6)

        ttk.Button(form, text="💾 Guardar ajustes", command=self._save).grid(row=7, column=0, sticky="w", pady=10)

    def _save(self) -> None:
        cfg = self.ctx.store.get()
        cfg.ui.theme = self.theme_var.get()
        cfg.ui.start_minimized = self.min_var.get()
        cfg.ui.close_to_tray = self.tray_var.get()
        cfg.on_close.stop_distros = self.stop_var.get()
        try:
            cfg.api.enabled = self.api_var.get()
            port = int(self.api_port_var.get() or 8791)
            if not (1024 <= port <= 65535):
                messagebox.showerror(
                    "WSL Manager",
                    "Puerto fuera de rango. Use un valor entre 1024 y 65535.",
                )
                return
            cfg.api.port = port
        except ValueError:
            messagebox.showerror("WSL Manager", "Puerto invalido")
            return
        self.ctx.store.save(cfg)
        self.ctx.metrics.log_event("gui_settings", message="ajustes guardados")
        messagebox.showinfo("WSL Manager", "Ajustes guardados.\nEl tema se aplica al reiniciar.")
