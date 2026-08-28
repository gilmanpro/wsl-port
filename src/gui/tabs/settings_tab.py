"""Pestana Ajustes: tema, comportamiento, API y MCP — ttkbootstrap moderno."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from src.gui.widgets import SectionHeader, ActionButton, COLORS


class SettingsTab(ttk.Frame):
    def __init__(self, master, ctx) -> None:
        super().__init__(master)
        self.ctx = ctx
        self._build()

    def _build(self) -> None:
        ui = self.ctx.config.ui
        api = self.ctx.config.api

        # ── Scrollable container ──
        canvas = tk.Canvas(self, highlightthickness=0, bg=COLORS["card"])
        vsb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview, bootstyle="round")
        scroll_frame = ttk.Frame(canvas, bootstyle="dark")

        scroll_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)

        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Mouse-wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        root = scroll_frame
        pad = {"padx": 16, "pady": 6}

        # ════════════════════════════════════════════════════════════════════
        #  HEADER
        # ════════════════════════════════════════════════════════════════════
        SectionHeader(root, text="\U0001f527 Ajustes de la Aplicacion").pack(anchor="w", **pad)

        ttk.Separator(root, bootstyle="secondary").pack(fill="x", **pad)

        # ════════════════════════════════════════════════════════════════════
        #  SECCION 1: APARIENCIA
        # ════════════════════════════════════════════════════════════════════
        appearance_lf = ttk.LabelFrame(
            root, text="  Apariencia  ", bootstyle="primary", padding=12
        )
        appearance_lf.pack(fill="x", **pad)

        # -- Tema --
        row = ttk.Frame(appearance_lf)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Tema:", width=20, anchor="w", font=("Segoe UI", 10)).pack(side="left")
        self.theme_var = tk.StringVar(value=ui.theme)
        themes_dark = ["darkly", "superhero", "solar", "cyborg", "vapor"]
        themes_light = ["cosmo", "flatly", "litera"]
        ttk.Combobox(
            row,
            textvariable=self.theme_var,
            values=themes_dark + themes_light,
            state="readonly",
            width=22,
            bootstyle="primary",
        ).pack(side="left", padx=(0, 8))

        ttk.Label(
            row,
            text="(se aplica al reiniciar)",
            foreground=COLORS["muted"],
            font=("Segoe UI", 8),
        ).pack(side="left")

        ttk.Separator(appearance_lf, bootstyle="secondary").pack(fill="x", pady=(8, 4))

        # -- Idioma --
        row = ttk.Frame(appearance_lf)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Idioma:", width=20, anchor="w", font=("Segoe UI", 10)).pack(side="left")
        self.lang_var = tk.StringVar(value="es")
        ttk.Combobox(
            row,
            textvariable=self.lang_var,
            values=["es", "en"],
            state="readonly",
            width=22,
            bootstyle="primary",
        ).pack(side="left", padx=(0, 8))

        ttk.Separator(appearance_lf, bootstyle="secondary").pack(fill="x", pady=(8, 4))

        # -- Intervalo de refresh --
        row = ttk.Frame(appearance_lf)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Intervalo refresh:", width=20, anchor="w", font=("Segoe UI", 10)).pack(side="left")
        self.refresh_var = tk.StringVar(value=str(ui.refresh_interval_seconds))
        ttk.Combobox(
            row,
            textvariable=self.refresh_var,
            values=["2", "5", "10"],
            state="readonly",
            width=10,
            bootstyle="primary",
        ).pack(side="left", padx=(0, 8))
        ttk.Label(
            row,
            text="segundos",
            foreground=COLORS["muted"],
            font=("Segoe UI", 9),
        ).pack(side="left")

        # -- Log Level --
        row = ttk.Frame(appearance_lf)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Nivel de log:", width=20, anchor="w", font=("Segoe UI", 10)).pack(side="left")
        self.loglevel_var = tk.StringVar(value=ui.log_level)
        ttk.Combobox(
            row,
            textvariable=self.loglevel_var,
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            state="readonly",
            width=10,
            bootstyle="primary",
        ).pack(side="left", padx=(0, 8))

        # ════════════════════════════════════════════════════════════════════
        #  SECCION 2: COMPORTAMIENTO
        # ════════════════════════════════════════════════════════════════════
        ttk.Separator(root, bootstyle="secondary").pack(fill="x", **pad)

        behavior_lf = ttk.LabelFrame(
            root, text="  Comportamiento  ", bootstyle="info", padding=12
        )
        behavior_lf.pack(fill="x", **pad)

        self.min_var = tk.BooleanVar(value=ui.start_minimized)
        ttk.Checkbutton(
            behavior_lf,
            text="Iniciar minimizado (solo tray)",
            variable=self.min_var,
            bootstyle="success",
        ).pack(anchor="w", pady=3)

        self.tray_var = tk.BooleanVar(value=ui.close_to_tray)
        ttk.Checkbutton(
            behavior_lf,
            text="Cerrar ventana \u2192 minimizar a tray",
            variable=self.tray_var,
            bootstyle="success",
        ).pack(anchor="w", pady=3)

        self.stop_var = tk.BooleanVar(value=self.ctx.config.on_close.stop_distros)
        ttk.Checkbutton(
            behavior_lf,
            text="Al salir: detener todas las distros",
            variable=self.stop_var,
            bootstyle="success",
        ).pack(anchor="w", pady=3)

        # ════════════════════════════════════════════════════════════════════
        #  SECCION 3: PANEL WEB
        # ════════════════════════════════════════════════════════════════════
        ttk.Separator(root, bootstyle="secondary").pack(fill="x", **pad)

        web_lf = ttk.LabelFrame(
            root, text="  Panel Web  ", bootstyle="warning", padding=12
        )
        web_lf.pack(fill="x", **pad)

        self.web_panel_var = tk.BooleanVar(value=ui.web_panel_enabled)
        ttk.Checkbutton(
            web_lf,
            text="Panel web habilitado",
            variable=self.web_panel_var,
            bootstyle="success",
        ).pack(anchor="w", pady=3)

        row = ttk.Frame(web_lf)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Puerto panel web:", width=20, anchor="w", font=("Segoe UI", 10)).pack(side="left")
        self.web_port_var = tk.StringVar(value=str(ui.refresh_interval_seconds))
        ttk.Entry(
            row, textvariable=self.web_port_var, width=10, bootstyle="default"
        ).pack(side="left", padx=(0, 8))

        row = ttk.Frame(web_lf)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Contraseña panel web:", width=20, anchor="w", font=("Segoe UI", 10)).pack(side="left")
        self.web_password_var = tk.StringVar(value=ui.web_password)
        ttk.Entry(
            row, textvariable=self.web_password_var, width=30, bootstyle="default", show="*"
        ).pack(side="left", padx=(0, 8))

        # ════════════════════════════════════════════════════════════════════
        #  SECCION 4: API REST
        # ════════════════════════════════════════════════════════════════════
        ttk.Separator(root, bootstyle="secondary").pack(fill="x", **pad)

        api_lf = ttk.LabelFrame(
            root, text="  API REST  ", bootstyle="danger", padding=12
        )
        api_lf.pack(fill="x", **pad)

        self.api_var = tk.BooleanVar(value=api.enabled)
        ttk.Checkbutton(
            api_lf,
            text="API REST habilitada",
            variable=self.api_var,
            bootstyle="success",
        ).pack(anchor="w", pady=3)

        # Puerto API
        row = ttk.Frame(api_lf)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Puerto API:", width=20, anchor="w", font=("Segoe UI", 10)).pack(side="left")
        self.api_port_var = tk.StringVar(value=str(api.port))
        ttk.Entry(
            row, textvariable=self.api_port_var, width=10, bootstyle="default"
        ).pack(side="left", padx=(0, 8))

        # Host API
        row = ttk.Frame(api_lf)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Host API:", width=20, anchor="w", font=("Segoe UI", 10)).pack(side="left")
        self.api_host_var = tk.StringVar(value=api.host)
        ttk.Combobox(
            row,
            textvariable=self.api_host_var,
            values=["127.0.0.1", "0.0.0.0"],
            state="readonly",
            width=14,
            bootstyle="primary",
        ).pack(side="left", padx=(0, 8))

        # ════════════════════════════════════════════════════════════════════
        #  SECCION 5: SEGURIDAD (placeholder)
        # ════════════════════════════════════════════════════════════════════
        ttk.Separator(root, bootstyle="secondary").pack(fill="x", **pad)

        security_lf = ttk.LabelFrame(
            root, text="  Seguridad  ", bootstyle="secondary", padding=12
        )
        security_lf.pack(fill="x", **pad)

        row = ttk.Frame(security_lf)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Token API:", width=20, anchor="w", font=("Segoe UI", 10)).pack(side="left")
        self.token_var = tk.StringVar(value="")
        ttk.Entry(
            row, textvariable=self.token_var, width=30, bootstyle="default", show="*"
        ).pack(side="left", padx=(0, 8))

        row = ttk.Frame(security_lf)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Rate Limit:", width=20, anchor="w", font=("Segoe UI", 10)).pack(side="left")
        self.ratelimit_var = tk.StringVar(value="100")
        ttk.Entry(
            row, textvariable=self.ratelimit_var, width=10, bootstyle="default"
        ).pack(side="left", padx=(0, 8))
        ttk.Label(
            row,
            text="requests/min",
            foreground=COLORS["muted"],
            font=("Segoe UI", 9),
        ).pack(side="left")

        # ════════════════════════════════════════════════════════════════════
        #  BOTONES DE ACCION
        # ════════════════════════════════════════════════════════════════════
        ttk.Separator(root, bootstyle="secondary").pack(fill="x", **pad)

        btn_frame = ttk.Frame(root, bootstyle="dark")
        btn_frame.pack(fill="x", padx=16, pady=(4, 16))

        ActionButton(
            btn_frame,
            text="💾 Guardar ajustes",
            command=self._save,
            bootstyle=SUCCESS,
            width=20,
        ).pack(side="left", padx=(0, 8))

        ActionButton(
            btn_frame,
            text="🔄 Restablecer",
            command=self._reset,
            bootstyle=DANGER,
            width=20,
        ).pack(side="left", padx=(0, 8))

    # ── Guardar ──────────────────────────────────────────────────────────
    def _save(self) -> None:
        cfg = self.ctx.store.get()

        # Apariencia
        cfg.ui.theme = self.theme_var.get()
        cfg.ui.log_level = self.loglevel_var.get()
        try:
            interval = int(self.refresh_var.get())
            if interval not in (2, 5, 10):
                raise ValueError
            cfg.ui.refresh_interval_seconds = interval
        except ValueError:
            messagebox.showerror(
                "WSL Manager", "Intervalo de refresh debe ser 2, 5 o 10 segundos."
            )
            return

        # Comportamiento
        cfg.ui.start_minimized = self.min_var.get()
        cfg.ui.close_to_tray = self.tray_var.get()
        cfg.on_close.stop_distros = self.stop_var.get()

        # Panel web
        cfg.ui.web_panel_enabled = self.web_panel_var.get()
        cfg.ui.web_password = self.web_password_var.get() or "wsl-manager"

        # API REST
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
            cfg.api.host = self.api_host_var.get()
        except ValueError:
            messagebox.showerror("WSL Manager", "Puerto invalido")
            return

        self.ctx.store.save(cfg)
        self.ctx.metrics.log_event("gui_settings", message="ajustes guardados")
        messagebox.showinfo(
            "WSL Manager", "Ajustes guardados.\nEl tema se aplica al reiniciar."
        )

    # ── Restablecer ──────────────────────────────────────────────────────
    def _reset(self) -> None:
        if not messagebox.askyesno(
            "WSL Manager", "Restablecer todos los ajustes a valores por defecto?"
        ):
            return

        from src.core.config import AppConfig

        default = AppConfig()
        self.theme_var.set(default.ui.theme)
        self.refresh_var.set(str(default.ui.refresh_interval_seconds))
        self.loglevel_var.set(default.ui.log_level)
        self.min_var.set(default.ui.start_minimized)
        self.tray_var.set(default.ui.close_to_tray)
        self.stop_var.set(default.on_close.stop_distros)
        self.web_panel_var.set(default.ui.web_panel_enabled)
        self.web_password_var.set(default.ui.web_password)
        self.api_var.set(default.api.enabled)
        self.api_port_var.set(str(default.api.port))
        self.api_host_var.set(default.api.host)
        messagebox.showinfo("WSL Manager", "Valores restablecidos. Presione Guardar para aplicar.")
