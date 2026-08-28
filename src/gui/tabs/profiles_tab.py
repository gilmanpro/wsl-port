"""Pestana Perfiles (A3): capturar y aplicar perfiles de distros — ttkbootstrap moderno."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from src.core.logger import get_logger
from src.core.profiles import ProfileService
from src.gui.widgets import StatCard, StatusDot, ActionButton, SectionHeader, COLORS

log = get_logger("gui.profiles")


class ProfilesTab(ttk.Frame):
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

        SectionHeader(header, text="\U0001f4cb Perfiles de Distros").pack(side="left")

        ActionButton(header, text="\U0001f4be Capturar", bootstyle=SUCCESS, command=self._capture, width=14).pack(side="right", padx=4)
        ActionButton(header, text="\u270f Editar", bootstyle=WARNING, command=self._edit, width=14).pack(side="right", padx=4)
        ActionButton(header, text="\u25b6 Aplicar", bootstyle=PRIMARY, command=self._apply, width=14).pack(side="right", padx=4)
        ActionButton(header, text="\U0001f504 Refrescar", bootstyle=INFO, command=self.refresh, width=14).pack(side="right", padx=4)

        # ════════════════════════════════════════════════════════════════════
        #  STATS CARDS
        # ════════════════════════════════════════════════════════════════════
        cards_frame = ttk.Frame(self, bootstyle="dark")
        cards_frame.pack(fill="x", padx=12, pady=(0, 8))

        self.card_total = StatCard(cards_frame, value="0", label="Total Perfiles", bootstyle="info", icon="\U0001f4c2")
        self.card_total.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.card_active = StatCard(cards_frame, value="-", label="Perfil Activo", bootstyle="success", icon="\u2b50")
        self.card_active.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.card_distros = StatCard(cards_frame, value="0", label="Distros Configuradas", bootstyle="warning", icon="\U0001f4e6")
        self.card_distros.pack(side="left", fill="x", expand=True)

        ttk.Separator(self, bootstyle="secondary").pack(fill="x", padx=12, pady=4)

        # ════════════════════════════════════════════════════════════════════
        #  TABLA DE PERFILES
        # ════════════════════════════════════════════════════════════════════
        tree_frame = ttk.Frame(self, bootstyle="dark")
        tree_frame.pack(fill="both", expand=True, padx=12, pady=4)

        columns = [
            ("name", "Perfil", 160),
            ("desc", "Descripcion", 220),
            ("distros", "Distros a iniciar", 300),
            ("active", "Activo", 80),
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
            text="Capturar = guarda el estado actual (distros activas). Aplicar = transiciona al perfil.",
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
            items = ProfileService(self.ctx.store, self.ctx.wsl).list()
            self.tree.delete(*self.tree.get_children())

            total_distros = 0
            active_name = "-"
            active_count = 0

            for idx, i in enumerate(items):
                mark = "\u25cf " if i["active"] else "\u25cb "
                status = "SI" if i["active"] else "No"
                row_tag = "active_row" if i["active"] else "inactive_row"
                alt_tag = "odd" if idx % 2 else "even"
                distros_str = ", ".join(i["distros_to_start"])
                total_distros += len(i["distros_to_start"])

                self.tree.insert(
                    "", "end",
                    values=(f"{mark}{i['name']}", i["description"], distros_str, status),
                    tags=(row_tag, alt_tag),
                )
                if i["active"]:
                    active_name = i["name"]
                    active_count += 1

            self.card_total.set_value(str(len(items)))
            self.card_active.set_value(active_name if active_name != "-" else "\u2014")
            self.card_distros.set_value(str(total_distros))

            self.status_var.set(f"{len(items)} perfiles configurados")
            self.status_dot.set_state("running" if active_count > 0 else "stopped")

        except Exception as e:  # noqa: BLE001
            log.exception("refresh profiles fallo")
            self.status_var.set(f"Error: {e}")
            self.status_dot.set_state("error")

    def _selected(self) -> str | None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("WSL Manager", "Selecciona un perfil")
            return None
        return self.tree.item(sel[0], "values")[0].lstrip("\u25cf \u25cb ")

    def _capture(self) -> None:
        import tkinter.simpledialog as sd

        name = sd.askstring("Capturar perfil", "Nombre del perfil:")
        if not name:
            return
        svc = ProfileService(self.ctx.store, self.ctx.wsl)
        item = svc.capture(name)
        self.ctx.metrics.log_event("gui_profile_capture", message=f"perfil {name} capturado")
        messagebox.showinfo("WSL Manager", f"Perfil '{name}' capturado:\n{', '.join(item.distros_to_start) or '(nada corriendo)'}")
        self.refresh()

    def _edit(self) -> None:
        """Abrir dialogo para editar el perfil seleccionado."""
        name = self._selected()
        if not name:
            return

        svc = ProfileService(self.ctx.store, self.ctx.wsl)
        items = svc.list()
        profile = next((i for i in items if i["name"] == name), None)
        if not profile:
            messagebox.showerror("WSL Manager", f"Perfil '{name}' no encontrado")
            return

        all_distros = [d.name for d in self.ctx.wsl.list_distros()]

        dlg = ttk.Toplevel(self)
        dlg.title(f"Editar perfil: {name}")
        dlg.geometry("450x420")
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        ttk.Label(dlg, text=f"Editar perfil: {name}", font=("Segoe UI", 13, "bold")).pack(pady=(12, 8))
        ttk.Separator(dlg, bootstyle="secondary").pack(fill="x", padx=16, pady=4)

        form = ttk.Frame(dlg, padding=8)
        form.pack(fill="x", padx=16)

        # Nombre
        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Nombre:", width=12, anchor="w").pack(side="left")
        name_var = tk.StringVar(value=name)
        ttk.Entry(row, textvariable=name_var, width=28, bootstyle="default").pack(side="left", padx=(4, 0))

        # Descripcion
        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Descripcion:", width=12, anchor="w").pack(side="left")
        desc_var = tk.StringVar(value=profile["description"])
        ttk.Entry(row, textvariable=desc_var, width=28, bootstyle="default").pack(side="left", padx=(4, 0))

        # Distros (checkbox list)
        ttk.Label(form, text="Distros a iniciar:", anchor="w").pack(anchor="w", pady=(8, 4))

        distro_frame = ttk.Frame(form)
        distro_frame.pack(fill="both", expand=True)

        distro_vars: dict[str, tk.BooleanVar] = {}
        for d in all_distros:
            var = tk.BooleanVar(value=d in profile["distros_to_start"])
            distro_vars[d] = var
            ttk.Checkbutton(distro_frame, text=d, variable=var, bootstyle="success").pack(anchor="w", padx=8)

        if not all_distros:
            ttk.Label(distro_frame, text="(No hay distros disponibles)", foreground=COLORS["muted"]).pack(anchor="w", padx=8)

        ttk.Separator(dlg, bootstyle="secondary").pack(fill="x", padx=16, pady=4)

        def _save() -> None:
            new_name = name_var.get().strip()
            if not new_name:
                messagebox.showwarning("WSL Manager", "El nombre es obligatorio")
                return
            selected = [d for d, v in distro_vars.items() if v.get()]

            cfg = self.ctx.store.get()
            # Actualizar o crear el perfil
            existing = [i for i in cfg.profiles.items if i["name"] != name]
            from src.core.config import ProfileItem
            new_item = ProfileItem(name=new_name, description=desc_var.get(), distros_to_start=selected)
            existing.append(new_item)
            cfg.profiles.items = existing
            self.ctx.store.save(cfg)

            self.ctx.metrics.log_event("gui_profile_edit", message=f"perfil {name} editado -> {new_name}")
            dlg.destroy()
            self.refresh()

        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(pady=12)
        ActionButton(btn_frame, text="Guardar", command=_save, bootstyle=SUCCESS, width=14).pack(side="left", padx=6)
        ActionButton(btn_frame, text="Cancelar", command=dlg.destroy, bootstyle=DANGER, width=14).pack(side="left", padx=6)

    def _apply(self) -> None:
        name = self._selected()
        if not name:
            return
        try:
            ok = ProfileService(self.ctx.store, self.ctx.wsl).apply(name)
        except KeyError as e:
            messagebox.showerror("WSL Manager", str(e))
            return
        if not ok:
            messagebox.showerror("WSL Manager", "Fallo al aplicar el perfil (ver logs)")
            return
        self.ctx.metrics.log_event("gui_profile_apply", message=f"perfil {name} aplicado")
        messagebox.showinfo("WSL Manager", f"Perfil '{name}' aplicado")
        self.refresh()
