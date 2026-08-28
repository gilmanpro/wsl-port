"""Pestana Recursos (R1): limites globales de la VM via .wslconfig — ttkbootstrap moderno."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from src.core.config import GlobalLimits
from src.core.logger import get_logger
from src.gui.widgets import StatCard, StatusDot, ActionButton, SectionHeader, COLORS

log = get_logger("gui.resources")


class ResourcesTab(ttk.Frame):
    def __init__(self, master, ctx) -> None:
        super().__init__(master)
        self.ctx = ctx
        self._build()

    def _build(self) -> None:
        cur = self.ctx.resources.get_global_limits()

        # ════════════════════════════════════════════════════════════════════
        #  HEADER CON BOTONES
        # ════════════════════════════════════════════════════════════════════
        header = ttk.Frame(self, bootstyle="dark")
        header.pack(fill="x", padx=12, pady=(10, 4))

        SectionHeader(header, text="\u2699\ufe0f Recursos del Sistema").pack(side="left")

        ActionButton(header, text="\u21ba Restablecer", bootstyle=DANGER, command=self._reset, width=14).pack(side="right", padx=4)
        ActionButton(header, text="\u25b6 Aplicar limites", bootstyle=SUCCESS, command=self._apply, width=16).pack(side="right", padx=4)

        # ════════════════════════════════════════════════════════════════════
        #  STATS CARDS
        # ════════════════════════════════════════════════════════════════════
        cards_frame = ttk.Frame(self, bootstyle="dark")
        cards_frame.pack(fill="x", padx=12, pady=(0, 8))

        self.card_memory = StatCard(
            cards_frame,
            value=f"{cur.memory_gb} GB" if cur.memory_gb else "\u221e",
            label="Memoria",
            bootstyle="info",
            icon="\U0001f4be",
        )
        self.card_memory.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.card_cpus = StatCard(
            cards_frame,
            value=str(cur.processors) if cur.processors else "\u221e",
            label="Procesadores",
            bootstyle="warning",
            icon="\U0001f4bb",
        )
        self.card_cpus.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.card_swap = StatCard(
            cards_frame,
            value=f"{cur.swap_gb} GB" if cur.swap_gb else "\u221e",
            label="Swap",
            bootstyle="success",
            icon="\U0001f4e6",
        )
        self.card_swap.pack(side="left", fill="x", expand=True)

        ttk.Separator(self, bootstyle="secondary").pack(fill="x", padx=12, pady=4)

        # ════════════════════════════════════════════════════════════════════
        #  FORMULARIO DE RECURSOS
        # ════════════════════════════════════════════════════════════════════
        scroll_frame = ttk.Frame(self, bootstyle="dark")
        scroll_frame.pack(fill="both", expand=True, padx=12, pady=4)

        # Limites Globales
        lf_global = ttk.LabelFrame(scroll_frame, text=" Limites Globales (.wslconfig [wsl2])", bootstyle="default", padding=12)
        lf_global.pack(fill="x", padx=4, pady=4)

        self.memory_var = tk.StringVar(value=f"{cur.memory_gb} GB" if cur.memory_gb else "")
        self.proc_var = tk.StringVar(value=str(cur.processors) if cur.processors else "")
        self.swap_var = tk.StringVar(value=f"{cur.swap_gb} GB" if cur.swap_gb else "")

        rows = [
            ("Memoria de la VM (ej: 8 GB)", self.memory_var, "dejar vacio = sin limite"),
            ("Procesadores", self.proc_var, "dejar vacio = sin limite"),
            ("Swap (ej: 4 GB)", self.swap_var, "dejar vacio = sin limite"),
        ]
        for i, (label, var, hint) in enumerate(rows):
            ttk.Label(lf_global, text=label).grid(row=i, column=0, sticky="w", pady=4)
            ttk.Entry(lf_global, textvariable=var, width=18, bootstyle="default").grid(row=i, column=1, sticky="w", padx=8)
            ttk.Label(lf_global, text=hint, foreground=COLORS["muted"]).grid(row=i, column=2, sticky="w")

        lf_global.columnconfigure(2, weight=1)

        # Opciones Experimentales
        lf_exp = ttk.LabelFrame(scroll_frame, text=" Opciones Experimentales", bootstyle="default", padding=12)
        lf_exp.pack(fill="x", padx=4, pady=4)

        self.reclaim_var = tk.StringVar(value=cur.auto_memory_reclaim or "disabled")
        ttk.Label(lf_exp, text="Auto-memory reclaim:").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Combobox(
            lf_exp, textvariable=self.reclaim_var, values=["disabled", "gradual", "dropcache"],
            width=16, state="readonly", bootstyle="primary",
        ).grid(row=0, column=1, sticky="w", padx=8)

        self.sparse_var = tk.BooleanVar(value=bool(cur.sparse_vhd))
        ttk.Checkbutton(
            lf_exp, text="Sparse VHD (ahorro de disco)", variable=self.sparse_var, bootstyle="success",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=6)

        # Hint
        ttk.Label(
            self,
            text="Los cambios requieren 'wsl --shutdown' (boton del Dashboard).\nSe hace backup automatico de .wslconfig antes de escribir.",
            foreground=COLORS["muted"],
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=16, pady=(4, 4))

        # ════════════════════════════════════════════════════════════════════
        #  STATUS BAR
        # ════════════════════════════════════════════════════════════════════
        status_bar = ttk.Frame(self, bootstyle="dark")
        status_bar.pack(fill="x", padx=12, pady=(0, 6))

        self.status_dot = StatusDot(status_bar, state="running")
        self.status_dot.pack(side="left", padx=(0, 6))

        self.status_var = tk.StringVar(value="Configuracion cargada")
        ttk.Label(
            status_bar,
            textvariable=self.status_var,
            foreground=COLORS["muted"],
            font=("Segoe UI", 9),
            bootstyle="dark",
        ).pack(side="left")

    def _apply(self) -> None:
        limits = GlobalLimits()

        def parse_gb(v: str) -> float | None:
            v = v.strip().upper()
            if not v:
                return None
            try:
                return float(v[:-2]) if v.endswith("GB") else (float(v[:-2]) / 1024 if v.endswith("MB") else float(v))
            except ValueError:
                return None

        mem = parse_gb(self.memory_var.get())
        swap = parse_gb(self.swap_var.get())
        if mem is not None:
            limits.memory_gb = mem
        if swap is not None:
            limits.swap_gb = swap
        if self.proc_var.get().strip().isdigit():
            limits.processors = int(self.proc_var.get().strip())
        limits.auto_memory_reclaim = self.reclaim_var.get()  # type: ignore[assignment]
        limits.sparse_vhd = self.sparse_var.get()

        r = self.ctx.resources.set_global_limits(limits)
        if not r.ok:
            messagebox.showerror("WSL Manager", r.error)
            return
        self.ctx.metrics.log_event("gui_limits", message="limites aplicados desde GUI")
        self.status_var.set("Limites aplicados correctamente")
        self.status_dot.set_state("running")
        messagebox.showinfo("WSL Manager", "Limites aplicados.\nEjecuta 'wsl --shutdown' para que surtan efecto.")

    def _reset(self) -> None:
        """Restablecer todos los campos a vacio (sin limite)."""
        self.memory_var.set("")
        self.proc_var.set("")
        self.swap_var.set("")
        self.reclaim_var.set("disabled")
        self.sparse_var.set(False)
        self.status_var.set("Campos restablecidos (aplicar para guardar)")
        self.status_dot.set_state("stopped")
