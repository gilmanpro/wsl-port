"""Pestana Tunnels: tunnels SSH con CRUD y reconexion — ttkbootstrap moderno."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from src.core.config import TunnelCfg
from src.core.logger import get_logger

log = get_logger("gui.tunnels")


class TunnelsTab(ttk.Frame):
    """Pestana de tunnels SSH (con indicador de reconexion automatica)."""

    def __init__(self, master, ctx) -> None:
        super().__init__(master)
        self.ctx = ctx
        self._job: str | None = None
        self._build()
        self.refresh()

    # ── Construccion de la interfaz ──────────────────────────────────────
    def _build(self) -> None:
        # ── Header ──
        header = ttk.Frame(self)
        header.pack(fill="x", padx=12, pady=(10, 4))

        ttk.Label(
            header,
            text="SSH Tunnels",
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left")

        ttk.Button(
            header,
            text="+ Add Tunnel",
            bootstyle=SUCCESS,
            command=self._add_dialog,
            width=16,
        ).pack(side="right", padx=4)

        ttk.Separator(self, bootstyle="secondary").pack(fill="x", padx=12, pady=4)

        # ── Treeview ──
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=12, pady=4)

        columns = [
            ("name", "Nombre", 130),
            ("remote_host", "Host Remoto", 140),
            ("remote_port", "Puerto Remoto", 110),
            ("local_port", "Puerto Local", 100),
            ("ssh_user", "SSH User", 90),
            ("ssh_host", "SSH Host", 140),
            ("auto_reconnect", "Auto-Reconnect", 110),
            ("active", "Estado", 100),
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
            self.tree.column(cid, width=width, anchor="w", minwidth=70)

        vsb = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self.tree.yview, bootstyle="round"
        )
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        # ── Action buttons ──
        ttk.Separator(self, bootstyle="secondary").pack(fill="x", padx=12, pady=4)

        action_frame = ttk.Frame(self)
        action_frame.pack(fill="x", padx=12, pady=(0, 8))

        ttk.Button(
            action_frame,
            text="Start",
            bootstyle=SUCCESS,
            command=self._start,
            width=10,
        ).pack(side="left", padx=4)

        ttk.Button(
            action_frame,
            text="Stop",
            bootstyle=DANGER,
            command=self._stop,
            width=10,
        ).pack(side="left", padx=4)

        ttk.Button(
            action_frame,
            text="Remove",
            bootstyle=WARNING,
            command=self._remove,
            width=10,
        ).pack(side="left", padx=4)

        ttk.Button(
            action_frame,
            text="Refresh",
            bootstyle=INFO,
            command=self.refresh,
            width=10,
        ).pack(side="left", padx=4)

        # ── Status bar ──
        self.status_var = tk.StringVar(value="Cargando...")
        status_bar = ttk.Frame(self)
        status_bar.pack(fill="x", padx=12, pady=(0, 6))

        self.status_dot = ttk.Label(
            status_bar, text="\u25cf", font=("Segoe UI", 10), foreground="#888"
        )
        self.status_dot.pack(side="left", padx=(0, 4))

        ttk.Label(
            status_bar, textvariable=self.status_var, foreground="#888"
        ).pack(side="left")

    # ── Datos ────────────────────────────────────────────────────────────
    def refresh(self) -> None:
        try:
            tunnels = self.ctx.forwarding.list_tunnels()
            self.tree.delete(*self.tree.get_children())
            for t in tunnels:
                is_active = t.get("active", False)
                status = "ACTIVO" if is_active else "Inactivo"
                auto = "Si" if t.get("auto_reconnect") else "No"
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        t.get("name", ""),
                        t.get("remote_host", ""),
                        t.get("remote_port", ""),
                        t.get("local_port", ""),
                        t.get("ssh_user", ""),
                        t.get("ssh_host", ""),
                        auto,
                        status,
                    ),
                )
            active = sum(1 for t in tunnels if t.get("active"))
            total = len(tunnels)
            self.status_var.set(f"{active}/{total} tunnels activos")

            # Update status dot color
            if active > 0:
                self.status_dot.configure(foreground="#28a745")
            else:
                self.status_dot.configure(foreground="#888")

        except Exception as e:  # noqa: BLE001
            log.exception("refresh tunnels fallo")
            self.status_var.set(f"error: {e}")
            self.status_dot.configure(foreground="#dc3545")
        finally:
            if self.winfo_exists():
                self._job = self.after(5000, self.refresh)

    def _selected(self) -> str | None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("WSL Manager", "Selecciona un tunnel")
            return None
        return self.tree.item(sel[0], "values")[0]

    # ── Dialogo agregar ──────────────────────────────────────────────────
    def _add_dialog(self) -> None:
        dlg = ttk.Toplevel(self)
        dlg.title("Agregar Tunnel")
        dlg.geometry("440x480")
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        # Title
        ttk.Label(
            dlg, text="Nuevo SSH Tunnel", font=("Segoe UI", 13, "bold")
        ).pack(pady=(12, 8))

        ttk.Separator(dlg, bootstyle="secondary").pack(fill="x", padx=16, pady=4)

        form = ttk.Frame(dlg, padding=8)
        form.pack(fill="x", padx=16)

        # Nombre
        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Nombre:", width=16, anchor="w").pack(side="left")
        name_var = tk.StringVar()
        ttk.Entry(row, textvariable=name_var, width=28, bootstyle="default").pack(
            side="left", padx=(4, 0)
        )

        # Host Remoto
        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Host Remoto:", width=16, anchor="w").pack(side="left")
        remote_host_var = tk.StringVar()
        ttk.Entry(
            row, textvariable=remote_host_var, width=28, bootstyle="default"
        ).pack(side="left", padx=(4, 0))

        # Puerto Remoto
        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Puerto Remoto:", width=16, anchor="w").pack(side="left")
        remote_port_var = tk.StringVar(value="22")
        ttk.Entry(
            row, textvariable=remote_port_var, width=28, bootstyle="default"
        ).pack(side="left", padx=(4, 0))

        # Puerto Local
        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Puerto Local:", width=16, anchor="w").pack(side="left")
        local_port_var = tk.StringVar(value="2222")
        ttk.Entry(
            row, textvariable=local_port_var, width=28, bootstyle="default"
        ).pack(side="left", padx=(4, 0))

        # SSH User
        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="SSH User:", width=16, anchor="w").pack(side="left")
        ssh_user_var = tk.StringVar(value="root")
        ttk.Entry(
            row, textvariable=ssh_user_var, width=28, bootstyle="default"
        ).pack(side="left", padx=(4, 0))

        # SSH Host
        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="SSH Host:", width=16, anchor="w").pack(side="left")
        ssh_host_var = tk.StringVar()
        ttk.Entry(
            row, textvariable=ssh_host_var, width=28, bootstyle="default"
        ).pack(side="left", padx=(4, 0))

        ttk.Separator(dlg, bootstyle="secondary").pack(fill="x", padx=16, pady=6)

        # Checkboxes
        checks = ttk.Frame(dlg, padding=(16, 0))
        checks.pack(fill="x")

        auto_reconnect_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            checks,
            text="Auto-reconnect",
            variable=auto_reconnect_var,
            bootstyle="success",
        ).pack(anchor="w", pady=2)

        enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            checks,
            text="Habilitado",
            variable=enabled_var,
            bootstyle="success",
        ).pack(anchor="w", pady=2)

        ttk.Separator(dlg, bootstyle="secondary").pack(fill="x", padx=16, pady=6)

        def _ok() -> None:
            try:
                name = name_var.get().strip()
                if not name:
                    messagebox.showwarning("WSL Manager", "El nombre es obligatorio")
                    return
                tun = TunnelCfg(
                    name=name,
                    remote_host=remote_host_var.get().strip(),
                    remote_port=int(remote_port_var.get()),
                    local_port=int(local_port_var.get()),
                    ssh_user=ssh_user_var.get().strip(),
                    ssh_host=ssh_host_var.get().strip(),
                    auto_reconnect=auto_reconnect_var.get(),
                    enabled=enabled_var.get(),
                )
                r = self.ctx.forwarding.add_tunnel(tun)
                if not r.get("ok"):
                    messagebox.showerror("WSL Manager", r.get("error", "error"))
                    return
                dlg.destroy()
                self.refresh()
            except Exception as e:  # noqa: BLE001
                messagebox.showerror("WSL Manager", str(e))

        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(pady=12)
        ttk.Button(
            btn_frame, text="Agregar", command=_ok, bootstyle=SUCCESS, width=14
        ).pack(side="left", padx=6)
        ttk.Button(
            btn_frame, text="Cancelar", command=dlg.destroy, bootstyle=DANGER, width=14
        ).pack(side="left", padx=6)

    # ── Acciones ─────────────────────────────────────────────────────────
    def _remove(self) -> None:
        name = self._selected()
        if not name:
            return
        if not messagebox.askyesno("WSL Manager", f"Eliminar tunnel '{name}'?"):
            return
        r = self.ctx.forwarding.remove_tunnel(name)
        if not r.get("ok"):
            messagebox.showerror("WSL Manager", r.get("error", "error"))
        self.refresh()

    def _start(self) -> None:
        name = self._selected()
        if not name:
            return
        r = self.ctx.forwarding.start_tunnel(name)
        if not r.get("ok"):
            messagebox.showerror("WSL Manager", r.get("error", "error"))
        self.refresh()

    def _stop(self) -> None:
        name = self._selected()
        if not name:
            return
        r = self.ctx.forwarding.stop_tunnel(name)
        if not r.get("ok"):
            messagebox.showerror("WSL Manager", r.get("error", "error"))
        self.refresh()

    def destroy(self) -> None:
        if self._job:
            self.after_cancel(self._job)
        super().destroy()
