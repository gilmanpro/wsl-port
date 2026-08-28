"""Pestana Autoarranque (W5): distros que inician con Windows — ttkbootstrap moderno."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from src.core.logger import get_logger
from src.gui.widgets import StatCard, StatusDot, ActionButton, SectionHeader, COLORS

log = get_logger("gui.autostart")


class AutoStartTab(ttk.Frame):
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

        SectionHeader(header, text="\u26a1 Autoarranque de Distros").pack(side="left")

        ActionButton(header, text="\U0001f504 Refrescar", bootstyle=INFO, command=self.refresh, width=14).pack(side="right", padx=4)
        ActionButton(header, text="\u2212 Desactivar", bootstyle=DANGER, command=self._disable, width=14).pack(side="right", padx=4)
        ActionButton(header, text="\u270f Editar", bootstyle=WARNING, command=self._edit, width=14).pack(side="right", padx=4)
        ActionButton(header, text="\uff0b Activar...", bootstyle=SUCCESS, command=self._enable, width=14).pack(side="right", padx=4)

        # ════════════════════════════════════════════════════════════════════
        #  STATS CARDS
        # ════════════════════════════════════════════════════════════════════
        cards_frame = ttk.Frame(self, bootstyle="dark")
        cards_frame.pack(fill="x", padx=12, pady=(0, 8))

        self.card_total = StatCard(cards_frame, value="0", label="Total", bootstyle="info", icon="\U0001f4e6")
        self.card_total.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.card_active = StatCard(cards_frame, value="0", label="Activos", bootstyle="success", icon="\u25b6")
        self.card_active.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.card_inactive = StatCard(cards_frame, value="0", label="Inactivos", bootstyle="secondary", icon="\u23f9")
        self.card_inactive.pack(side="left", fill="x", expand=True)

        ttk.Separator(self, bootstyle="secondary").pack(fill="x", padx=12, pady=4)

        # ════════════════════════════════════════════════════════════════════
        #  TABLA DE AUTOARRANQUE
        # ════════════════════════════════════════════════════════════════════
        tree_frame = ttk.Frame(self, bootstyle="dark")
        tree_frame.pack(fill="both", expand=True, padx=12, pady=4)

        columns = [
            ("distro", "Distro", 180),
            ("delay", "Retraso (s)", 100),
            ("cmd", "Comando en Run", 480),
            ("status", "Estado", 100),
        ]

        self.tree = ttk.Treeview(
            tree_frame,
            columns=[c[0] for c in columns],
            show="headings",
            height=12,
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
        self.tree.tag_configure("active_row", foreground=COLORS["success"])
        self.tree.tag_configure("inactive_row", foreground=COLORS["muted"])
        self.tree.tag_configure("odd", background="#1a2030")
        self.tree.tag_configure("even", background="#1d2430")

        ttk.Separator(self, bootstyle="secondary").pack(fill="x", padx=12, pady=4)

        # Hint
        ttk.Label(
            self,
            text="Con WSL Manager: las distros marcadas aqui se inician automaticamente al entrar a Windows (HKCU Run).",
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

        self.status_var = tk.StringVar(value="Cargando...")
        ttk.Label(
            status_bar,
            textvariable=self.status_var,
            foreground=COLORS["muted"],
            font=("Segoe UI", 9),
            bootstyle="dark",
        ).pack(side="left")

    def refresh(self) -> None:
        try:
            items = self.ctx.autostart.list_autostart()
            self.tree.delete(*self.tree.get_children())

            total = 0
            active = 0

            for idx, (distro, info) in enumerate(items.items()):
                row_tag = "active_row"
                alt_tag = "odd" if idx % 2 else "even"

                self.tree.insert(
                    "", "end",
                    values=(distro, info["delay_s"], info["command"], "\u25cf ACTIVO"),
                    tags=(row_tag, alt_tag),
                )
                total += 1
                active += 1

            if not items:
                self.tree.insert(
                    "", "end",
                    values=("(sin distros en autoarranque)", "", "", "\u25cb inactivo"),
                    tags=("inactive_row", "even"),
                )

            self.card_total.set_value(str(total))
            self.card_active.set_value(str(active))
            self.card_inactive.set_value("0")

            self.status_var.set(f"{total} distros en autoarranque")
            self.status_dot.set_state("running" if active > 0 else "stopped")

        except Exception as e:  # noqa: BLE001
            log.exception("refresh autostart fallo")
            self.status_var.set(f"Error: {e}")
            self.status_dot.set_state("error")

    def _selected(self) -> str | None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("WSL Manager", "Selecciona una distro")
            return None
        val = self.tree.item(sel[0], "values")[0]
        if val.startswith("("):
            return None
        return val

    def _enable(self) -> None:
        import tkinter.simpledialog as sd

        distros = [d.name for d in self.ctx.wsl.list_distros()]
        if not distros:
            messagebox.showinfo("WSL Manager", "No hay distros detectadas")
            return
        from tkinter import simpledialog

        class _Dialog(simpledialog.Dialog):
            def body(self, master):
                self.distro = tk.StringVar(value=distros[0])
                self.delay = tk.StringVar(value="0")
                ttk.Label(master, text="Distro:").grid(row=0, column=0, sticky="w")
                ttk.Combobox(master, textvariable=self.distro, values=distros, state="readonly", width=24).grid(row=0, column=1, padx=4)
                ttk.Label(master, text="Retraso (s):").grid(row=1, column=0, sticky="w", pady=4)
                ttk.Entry(master, textvariable=self.delay, width=10).grid(row=1, column=1, sticky="w", padx=4)

            def apply(self):
                self.result = (self.distro.get(), int(self.delay.get() or 0))

        dlg = _Dialog(self, title="Autoarranque")
        if dlg.result:
            distro, delay = dlg.result
            r = self.ctx.autostart.set_autostart(distro, True, delay)
            if not r.ok:
                messagebox.showerror("WSL Manager", r.error)
                return
            self.ctx.metrics.log_event("gui_autostart", distro, f"autoarranque con delay {delay}s")
            self.refresh()

    def _edit(self) -> None:
        """Abrir dialogo para editar el retraso de la distro seleccionada."""
        distro = self._selected()
        if not distro:
            return

        # Obtener info actual
        items = self.ctx.autostart.list_autostart()
        info = items.get(distro)
        if not info:
            messagebox.showerror("WSL Manager", f"Distro '{distro}' no encontrada en autoarranque")
            return

        dlg = ttk.Toplevel(self)
        dlg.title(f"Editar autoarranque: {distro}")
        dlg.geometry("400x200")
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        ttk.Label(dlg, text=f"Editar: {distro}", font=("Segoe UI", 13, "bold")).pack(pady=(12, 8))
        ttk.Separator(dlg, bootstyle="secondary").pack(fill="x", padx=16, pady=4)

        form = ttk.Frame(dlg, padding=8)
        form.pack(fill="x", padx=16)

        # Distro (solo lectura)
        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Distro:", width=12, anchor="w").pack(side="left")
        ttk.Label(row, text=distro, font=("Segoe UI", 10, "bold"), foreground=COLORS["text"]).pack(side="left", padx=(4, 0))

        # Retraso
        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Retraso (s):", width=12, anchor="w").pack(side="left")
        delay_var = tk.StringVar(value=str(info["delay_s"]))
        ttk.Entry(row, textvariable=delay_var, width=12, bootstyle="default").pack(side="left", padx=(4, 0))

        ttk.Separator(dlg, bootstyle="secondary").pack(fill="x", padx=16, pady=4)

        def _save() -> None:
            try:
                new_delay = int(delay_var.get() or 0)
            except ValueError:
                messagebox.showwarning("WSL Manager", "Retraso debe ser un numero entero")
                return
            r = self.ctx.autostart.set_autostart(distro, True, new_delay)
            if not r.ok:
                messagebox.showerror("WSL Manager", r.error)
                return
            self.ctx.metrics.log_event("gui_autostart_edit", distro, f"retraso actualizado a {new_delay}s")
            dlg.destroy()
            self.refresh()

        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(pady=12)
        ActionButton(btn_frame, text="Guardar", command=_save, bootstyle=SUCCESS, width=14).pack(side="left", padx=6)
        ActionButton(btn_frame, text="Cancelar", command=dlg.destroy, bootstyle=DANGER, width=14).pack(side="left", padx=6)

    def _disable(self) -> None:
        distro = self._selected()
        if not distro:
            return
        r = self.ctx.autostart.set_autostart(distro, False)
        if not r.ok:
            messagebox.showerror("WSL Manager", r.error)
            return
        self.ctx.metrics.log_event("gui_autostart_disable", distro, "autoarranque desactivado")
        self.refresh()
