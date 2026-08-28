"""Pestana Forwards: port-forwards Windows -> WSL con CRUD — ttkbootstrap moderno."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from src.core.config import ForwardItem
from src.core.logger import get_logger
from src.gui.widgets import StatCard, StatusDot, ActionButton, SectionHeader, COLORS

log = get_logger("gui.forwards")


class ForwardsTab(ttk.Frame):
    """Pestana de port-forwarding (Windows -> WSL via netsh portproxy)."""

    def __init__(self, master, ctx) -> None:
        super().__init__(master)
        self.ctx = ctx
        self._job: str | None = None
        self._build()
        self.refresh()

    # ── Construccion de la interfaz ──────────────────────────────────────
    def _build(self) -> None:
        # ── Header ──
        header = ttk.Frame(self, bootstyle="dark")
        header.pack(fill="x", padx=12, pady=(10, 4))

        SectionHeader(header, text="\U0001f504 Port Forwards").pack(side="left")

        ActionButton(
            header, text="+ Add Forward", bootstyle=SUCCESS,
            command=self._add_dialog, width=16,
        ).pack(side="right", padx=4)

        ActionButton(
            header, text="Apply All", bootstyle="info-outline",
            command=self._apply_all, width=12,
        ).pack(side="right", padx=4)

        ActionButton(
            header, text="Clear All", bootstyle=(DANGER, OUTLINE),
            command=self._clear_all, width=12,
        ).pack(side="right", padx=4)

        # ── Stats Cards ──
        cards_frame = ttk.Frame(self, bootstyle="dark")
        cards_frame.pack(fill="x", padx=12, pady=(0, 8))

        self.card_total = StatCard(cards_frame, value="0", label="Total", bootstyle="info", icon="\U0001f4e6")
        self.card_total.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.card_active = StatCard(cards_frame, value="0", label="Active", bootstyle="success", icon="\u25b6")
        self.card_active.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.card_inactive = StatCard(cards_frame, value="0", label="Inactive", bootstyle="secondary", icon="\u23f9")
        self.card_inactive.pack(side="left", fill="x", expand=True)

        ttk.Separator(self, bootstyle="secondary").pack(fill="x", padx=12, pady=4)

        # ── Treeview ──
        tree_frame = ttk.Frame(self, bootstyle="dark")
        tree_frame.pack(fill="both", expand=True, padx=12, pady=4)

        columns = [
            ("name", "Nombre", 160),
            ("local_port", "Puerto Local", 110),
            ("wsl_port", "Puerto WSL", 110),
            ("wsl_ip", "IP WSL", 140),
            ("enabled", "Habilitado", 100),
            ("active", "Estado", 120),
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
            self.tree.column(cid, width=width, anchor="w", minwidth=80)

        vsb = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self.tree.yview, bootstyle="round"
        )
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        # Tags para filas alternas
        self.tree.tag_configure("active_row", foreground=COLORS["success"])
        self.tree.tag_configure("inactive_row", foreground=COLORS["muted"])
        self.tree.tag_configure("odd", background="#1a2030")
        self.tree.tag_configure("even", background="#1d2430")

        # ── Action buttons ──
        ttk.Separator(self, bootstyle="secondary").pack(fill="x", padx=12, pady=4)

        action_frame = ttk.Frame(self, bootstyle="dark")
        action_frame.pack(fill="x", padx=12, pady=(0, 8))

        ActionButton(action_frame, text="▶ Start", bootstyle=SUCCESS, command=self._start, width=10).pack(side="left", padx=4)
        ActionButton(action_frame, text="⏹ Stop", bootstyle=DANGER, command=self._stop, width=10).pack(side="left", padx=4)
        ActionButton(action_frame, text="✏ Edit", bootstyle=PRIMARY, command=self._edit_dialog, width=10).pack(side="left", padx=4)
        ActionButton(action_frame, text="🗑 Remove", bootstyle=WARNING, command=self._remove, width=10).pack(side="left", padx=4)
        ActionButton(action_frame, text="🔄 Refresh", bootstyle=INFO, command=self.refresh, width=10).pack(side="left", padx=4)

        # ── Status bar ──
        self.status_var = tk.StringVar(value="Cargando...")
        status_bar = ttk.Frame(self, bootstyle="dark")
        status_bar.pack(fill="x", padx=12, pady=(0, 6))

        self.status_dot = StatusDot(status_bar, state="stopped")
        self.status_dot.pack(side="left", padx=(0, 6))

        ttk.Label(
            status_bar, textvariable=self.status_var, foreground=COLORS["muted"],
            font=("Segoe UI", 9), bootstyle="dark",
        ).pack(side="left")

    # ── Datos ────────────────────────────────────────────────────────────
    def refresh(self) -> None:
        try:
            forwards = self.ctx.forwarding.list_forwards()
            try:
                self.tree.delete(*self.tree.get_children())
            except tk.TclError:
                pass
            active_count = 0
            inactive_count = 0

            for idx, f in enumerate(forwards):
                is_active = f.get("active", False)
                status = "\u25cf ACTIVO" if is_active else "\u25cb Inactivo"
                row_tag = "active_row" if is_active else "inactive_row"
                alt_tag = "odd" if idx % 2 else "even"

                self.tree.insert(
                    "", "end",
                    values=(
                        f.get("name", ""),
                        f.get("local_port", ""),
                        f.get("wsl_port", ""),
                        f.get("wsl_ip", ""),
                        "Si" if f.get("enabled") else "No",
                        status,
                    ),
                    tags=(row_tag, alt_tag),
                )
                if is_active:
                    active_count += 1
                else:
                    inactive_count += 1

            # Update stats cards
            self.card_total.set_value(str(len(forwards)))
            self.card_active.set_value(str(active_count))
            self.card_inactive.set_value(str(inactive_count))

            self.status_var.set(f"{active_count}/{len(forwards)} forwards activos")
            self.status_dot.set_state("running" if active_count > 0 else "stopped")

        except Exception as e:  # noqa: BLE001
            log.exception("refresh forwards fallo")
            self.status_var.set(f"Error: {e}")
            self.status_dot.set_state("error")
        finally:
            if self.winfo_exists():
                self._job = self.after(5000, self.refresh)

    def _selected(self) -> str | None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("WSL Manager", "Selecciona un forward")
            return None
        return self.tree.item(sel[0], "values")[0]

    # ── Dialogo agregar ──────────────────────────────────────────────────
    def _add_dialog(self) -> None:
        dlg = ttk.Toplevel(self)
        dlg.title("Agregar Forward")
        dlg.geometry("420x380")
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        # Title
        ttk.Label(
            dlg, text="Nuevo Port Forward", font=("Segoe UI", 13, "bold")
        ).pack(pady=(12, 8))

        ttk.Separator(dlg, bootstyle="secondary").pack(fill="x", padx=16, pady=4)

        form = ttk.Frame(dlg, padding=8)
        form.pack(fill="x", padx=16)

        # Nombre
        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Nombre:", width=14, anchor="w").pack(side="left")
        name_var = tk.StringVar()
        ttk.Entry(row, textvariable=name_var, width=28, bootstyle="default").pack(
            side="left", padx=(4, 0)
        )

        # Puerto Local
        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Puerto Local:", width=14, anchor="w").pack(side="left")
        local_var = tk.StringVar(value="8080")
        ttk.Entry(row, textvariable=local_var, width=28, bootstyle="default").pack(
            side="left", padx=(4, 0)
        )

        # Puerto WSL
        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Puerto WSL:", width=14, anchor="w").pack(side="left")
        wsl_port_var = tk.StringVar(value="80")
        ttk.Entry(row, textvariable=wsl_port_var, width=28, bootstyle="default").pack(
            side="left", padx=(4, 0)
        )

        # IP WSL
        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="IP WSL:", width=14, anchor="w").pack(side="left")
        wsl_ip_var = tk.StringVar(value="127.0.0.1")
        ttk.Entry(row, textvariable=wsl_ip_var, width=28, bootstyle="default").pack(
            side="left", padx=(4, 0)
        )

        # Enabled
        enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            form, text="Habilitado", variable=enabled_var, bootstyle="success"
        ).pack(anchor="w", pady=4)

        ttk.Separator(dlg, bootstyle="secondary").pack(fill="x", padx=16, pady=4)

        def _ok() -> None:
            try:
                name = name_var.get().strip()
                if not name:
                    messagebox.showwarning("WSL Manager", "El nombre es obligatorio")
                    return
                fwd = ForwardItem(
                    name=name,
                    local_port=int(local_var.get()),
                    wsl_port=int(wsl_port_var.get()),
                    wsl_ip=wsl_ip_var.get().strip() or "127.0.0.1",
                    enabled=enabled_var.get(),
                )
                r = self.ctx.forwarding.add_forward(fwd)
                if not r.get("ok"):
                    messagebox.showerror("WSL Manager", r.get("error", "error"))
                    return
                dlg.destroy()
                self.refresh()
            except Exception as e:  # noqa: BLE001
                messagebox.showerror("WSL Manager", str(e))

        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(pady=12)
        ActionButton(
            btn_frame, text="Agregar", command=_ok, bootstyle=SUCCESS, width=14
        ).pack(side="left", padx=6)
        ActionButton(
            btn_frame, text="Cancelar", command=dlg.destroy, bootstyle=DANGER, width=14
        ).pack(side="left", padx=6)

    # ── Dialogo editar ──────────────────────────────────────────────────
    def _edit_dialog(self) -> None:
        name = self._selected()
        if not name:
            return
        # Buscar el forward actual
        forwards = self.ctx.forwarding.list_forwards()
        fwd = next((f for f in forwards if f.get("name") == name), None)
        if not fwd:
            messagebox.showerror("WSL Manager", f"Forward '{name}' no encontrado")
            return

        dlg = ttk.Toplevel(self)
        dlg.title(f"Editar Forward: {name}")
        dlg.geometry("420x340")
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        ttk.Label(dlg, text=f"Editar: {name}", font=("Segoe UI", 13, "bold")).pack(pady=(12, 8))
        ttk.Separator(dlg, bootstyle="secondary").pack(fill="x", padx=16, pady=4)

        form = ttk.Frame(dlg, padding=8)
        form.pack(fill="x", padx=16)

        # Nombre (no editable)
        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Nombre:", width=14, anchor="w").pack(side="left")
        ttk.Label(row, text=name, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(4, 0))

        # Puerto Local
        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Puerto Local:", width=14, anchor="w").pack(side="left")
        local_var = tk.StringVar(value=str(fwd.get("local_port", "")))
        ttk.Entry(row, textvariable=local_var, width=28, bootstyle="default").pack(side="left", padx=(4, 0))

        # Puerto WSL
        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Puerto WSL:", width=14, anchor="w").pack(side="left")
        wsl_port_var = tk.StringVar(value=str(fwd.get("wsl_port", "")))
        ttk.Entry(row, textvariable=wsl_port_var, width=28, bootstyle="default").pack(side="left", padx=(4, 0))

        # IP WSL
        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="IP WSL:", width=14, anchor="w").pack(side="left")
        wsl_ip_var = tk.StringVar(value=fwd.get("wsl_ip", "127.0.0.1"))
        ttk.Entry(row, textvariable=wsl_ip_var, width=28, bootstyle="default").pack(side="left", padx=(4, 0))

        # Enabled
        enabled_var = tk.BooleanVar(value=fwd.get("enabled", True))
        ttk.Checkbutton(form, text="Habilitado", variable=enabled_var, bootstyle="success").pack(anchor="w", pady=4)

        ttk.Separator(dlg, bootstyle="secondary").pack(fill="x", padx=16, pady=4)

        def _ok() -> None:
            try:
                # Eliminar el anterior y crear uno nuevo
                self.ctx.forwarding.remove_forward(name)
                new_fwd = ForwardItem(
                    name=name,
                    local_port=int(local_var.get()),
                    wsl_port=int(wsl_port_var.get()),
                    wsl_ip=wsl_ip_var.get().strip() or "127.0.0.1",
                    enabled=enabled_var.get(),
                )
                r = self.ctx.forwarding.add_forward(new_fwd)
                if not r.get("ok"):
                    messagebox.showerror("WSL Manager", r.get("error", "error"))
                    return
                dlg.destroy()
                self.refresh()
            except Exception as e:
                messagebox.showerror("WSL Manager", str(e))

        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(pady=12)
        ActionButton(btn_frame, text="Guardar", command=_ok, bootstyle=SUCCESS, width=14).pack(side="left", padx=6)
        ActionButton(btn_frame, text="Cancelar", command=dlg.destroy, bootstyle=DANGER, width=14).pack(side="left", padx=6)

    # ── Acciones ─────────────────────────────────────────────────────────
    def _remove(self) -> None:
        name = self._selected()
        if not name:
            return
        if not messagebox.askyesno("WSL Manager", f"Eliminar forward '{name}'?"):
            return
        r = self.ctx.forwarding.remove_forward(name)
        if not r.get("ok"):
            messagebox.showerror("WSL Manager", r.get("error", "error"))
        self.refresh()

    def _start(self) -> None:
        name = self._selected()
        if not name:
            return
        r = self.ctx.forwarding.start_forward(name)
        if not r.get("ok"):
            messagebox.showerror("WSL Manager", r.get("error", "error"))
        self.refresh()

    def _stop(self) -> None:
        name = self._selected()
        if not name:
            return
        r = self.ctx.forwarding.stop_forward(name)
        if not r.get("ok"):
            messagebox.showerror("WSL Manager", r.get("error", "error"))
        self.refresh()

    def _apply_all(self) -> None:
        r = self.ctx.forwarding.apply_all_forwards()
        if not r.get("ok"):
            messagebox.showerror("WSL Manager", r.get("error", "error"))
        self.refresh()

    def _clear_all(self) -> None:
        if not messagebox.askyesno(
            "WSL Manager", "Limpiar TODOS los portproxies? Esto es destructivo."
        ):
            return
        r = self.ctx.forwarding.clear_all_forwards()
        if not r.get("ok"):
            messagebox.showerror("WSL Manager", r.get("error", "error"))
        self.refresh()

    def destroy(self) -> None:
        if self._job:
            self.after_cancel(self._job)
        super().destroy()
