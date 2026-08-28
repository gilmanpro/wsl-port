"""Pestana Configuracion: edicion segura de .wslconfig con backup + validacion — ttkbootstrap moderno."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from src.core.logger import get_logger
from src.gui.widgets import StatCard, StatusDot, ActionButton, SectionHeader, COLORS

log = get_logger("gui.config")


class ConfigTab(ttk.Frame):
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

        SectionHeader(header, text="\U0001f4dd Configuracion .wslconfig").pack(side="left")

        ActionButton(header, text="\U0001f504 Recargar", bootstyle=INFO, command=self.refresh, width=14).pack(side="right", padx=4)
        ActionButton(header, text="\U0001f4be Guardar (con backup)", bootstyle=SUCCESS, command=self._save, width=18).pack(side="right", padx=4)

        ttk.Label(
            header,
            text="  ~/.wslconfig — configuracion de la VM WSL2",
            foreground=COLORS["muted"],
            font=("Segoe UI", 9),
        ).pack(side="left", padx=(8, 0))

        # ════════════════════════════════════════════════════════════════════
        #  STATS CARDS
        # ════════════════════════════════════════════════════════════════════
        cards_frame = ttk.Frame(self, bootstyle="dark")
        cards_frame.pack(fill="x", padx=12, pady=(0, 8))

        self.card_lines = StatCard(cards_frame, value="0", label="Lineas", bootstyle="info", icon="\U0001f4c4")
        self.card_lines.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.card_sections = StatCard(cards_frame, value="0", label="Secciones", bootstyle="primary", icon="\U0001f4d1")
        self.card_sections.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.card_status = StatCard(cards_frame, value="\u2014", label="Estado", bootstyle="secondary", icon="\u2699\ufe0f")
        self.card_status.pack(side="left", fill="x", expand=True)

        ttk.Separator(self, bootstyle="secondary").pack(fill="x", padx=12, pady=4)

        # ════════════════════════════════════════════════════════════════════
        #  EDITOR DE TEXTO
        # ════════════════════════════════════════════════════════════════════
        editor_frame = ttk.Frame(self, bootstyle="dark")
        editor_frame.pack(fill="both", expand=True, padx=12, pady=4)

        self.text = tk.Text(
            editor_frame,
            wrap="none",
            font=("Consolas", 10),
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

        ttk.Separator(self, bootstyle="secondary").pack(fill="x", padx=12, pady=4)

        # ════════════════════════════════════════════════════════════════════
        #  STATUS BAR
        # ════════════════════════════════════════════════════════════════════
        status_bar = ttk.Frame(self, bootstyle="dark")
        status_bar.pack(fill="x", padx=12, pady=(0, 6))

        self.status_dot = StatusDot(status_bar, state="stopped")
        self.status_dot.pack(side="left", padx=(0, 6))

        self.status_var = tk.StringVar(value="Cargando...")
        ttk.Label(
            status_bar,
            textvariable=self.status_var,
            foreground=COLORS["muted"],
            font=("Segoe UI", 9),
            bootstyle="dark",
        ).pack(side="left")

        self._errors = tk.StringVar()
        ttk.Label(
            status_bar,
            textvariable=self._errors,
            foreground=COLORS["danger"],
            font=("Segoe UI", 9),
            bootstyle="dark",
        ).pack(side="right")

    def refresh(self) -> None:
        from src.providers.wsl_config_provider import WslConfigProvider

        try:
            p = WslConfigProvider()
            text = p.wslconfig_path.read_text(encoding="utf-8") if p.wslconfig_path.exists() else "# (sin .wslconfig; se creara al guardar)\n"
            self.text.delete("1.0", "end")
            self.text.insert("1.0", text)
            self._errors.set("")

            # Update stats
            lines = text.count("\n")
            sections = text.count("[")
            self.card_lines.set_value(str(lines))
            self.card_sections.set_value(str(sections))
            self.card_status.set_value("Valido" if p.wslconfig_path.exists() else "Sin archivo")
            self.card_status._value_var.set("Sin archivo" if not p.wslconfig_path.exists() else "Existe")

            self.status_var.set(f".wslconfig — {p.wslconfig_path}")
            self.status_dot.set_state("running" if p.wslconfig_path.exists() else "stopped")

        except Exception as e:  # noqa: BLE001
            log.exception("refresh config fallo")
            self.status_var.set(f"Error: {e}")
            self.status_dot.set_state("error")

    def _save(self) -> None:
        from src.providers.wsl_config_provider import WslConfigProvider

        content = self.text.get("1.0", "end-1c")
        p = WslConfigProvider()
        if not p._validate_ini(content):
            self._errors.set("INI invalido: revisa las secciones [wsl2], [experimental], etc.")
            self.status_dot.set_state("error")
            return
        backup = p.backup_now()
        try:
            p.wslconfig_path.write_text(content, encoding="utf-8")
        except OSError as e:
            messagebox.showerror("WSL Manager", str(e))
            return
        self.ctx.metrics.log_event("gui_wslconfig", message=f".wslconfig guardado (backup {backup.name})")
        self._errors.set("")
        self.status_var.set(f"Guardado OK. Backup: {backup.name}")
        self.card_status.set_value("Guardado")
        self.status_dot.set_state("running")
        messagebox.showinfo("WSL Manager", f"Guardado. Backup: {backup.name}\nRequiere 'wsl --shutdown'.")
