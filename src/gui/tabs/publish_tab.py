"""Pestana Publicar a Internet: VPS + tunnels para publicar servicios — ttkbootstrap moderno.

Combina gestion de VPS configurados y tunnels SSH hacia ellos para
abrir servicios al Internet de forma facil.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from src.core.config import VpsCfg
from src.core.logger import get_logger
from src.gui.widgets import StatCard, StatusDot, ActionButton, SectionHeader, COLORS

log = get_logger("gui.publish")


class PublishTab(ttk.Frame):
    """Pestana de Publicar a Internet: VPS + Tunnels."""

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

        SectionHeader(header, text="\U0001f310 Publicar a Internet").pack(side="left")

        ActionButton(
            header, text="+ Add VPS", bootstyle=SUCCESS,
            command=self._add_vps_dialog, width=16,
        ).pack(side="right", padx=4)

        # ── Stats Cards ──
        cards_frame = ttk.Frame(self, bootstyle="dark")
        cards_frame.pack(fill="x", padx=12, pady=(0, 8))

        self.card_vps = StatCard(cards_frame, value="0", label="VPS Configurados", bootstyle="info", icon="\U0001f310")
        self.card_vps.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.card_tunnels = StatCard(cards_frame, value="0", label="Tunnels Activos", bootstyle="success", icon="\U0001f50c")
        self.card_tunnels.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.card_inactive = StatCard(cards_frame, value="0", label="Sin Tunnels", bootstyle="secondary", icon="\u23f9")
        self.card_inactive.pack(side="left", fill="x", expand=True)

        ttk.Separator(self, bootstyle="secondary").pack(fill="x", padx=12, pady=4)

        # ── Main PanedWindow: VPS (top) + Tunnels (bottom) ──
        paned = tk.PanedWindow(self, orient="vertical", sashwidth=6, bg="#2a3344")
        paned.pack(fill="both", expand=True, padx=12, pady=4)

        # === VPS Section ===
        vps_lf = ttk.LabelFrame(paned, text="  VPS Configurados  ", bootstyle="primary", padding=4)
        paned.add(vps_lf)

        vps_tree_frame = ttk.Frame(vps_lf, bootstyle="dark")
        vps_tree_frame.pack(fill="both", expand=True)

        columns = [
            ("id", "ID", 140),
            ("host", "Host", 180),
            ("user", "Usuario", 100),
            ("port", "Puerto SSH", 100),
            ("identity_file", "Clave SSH", 160),
            ("status", "Estado", 120),
        ]

        self.vps_tree = ttk.Treeview(
            vps_tree_frame,
            columns=[c[0] for c in columns],
            show="headings",
            height=5,
            bootstyle="primary",
        )
        for cid, title, width in columns:
            self.vps_tree.heading(cid, text=title, anchor="w")
            self.vps_tree.column(cid, width=width, anchor="w", minwidth=70)

        vsb = ttk.Scrollbar(
            vps_tree_frame, orient="vertical", command=self.vps_tree.yview, bootstyle="round"
        )
        self.vps_tree.configure(yscrollcommand=vsb.set)
        self.vps_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        vps_tree_frame.rowconfigure(0, weight=1)
        vps_tree_frame.columnconfigure(0, weight=1)

        # VPS action buttons
        vps_actions = ttk.Frame(vps_lf, bootstyle="dark")
        vps_actions.pack(fill="x", pady=(4, 0))

        ActionButton(
            vps_actions, text="🗑 Remove VPS", bootstyle=DANGER,
            command=self._remove_vps, width=14,
        ).pack(side="left", padx=4)
        ActionButton(
            vps_actions, text="✏ Edit VPS", bootstyle=INFO,
            command=self._edit_vps_dialog, width=14,
        ).pack(side="left", padx=4)
        ActionButton(
            vps_actions, text="▶ Connect", bootstyle=PRIMARY,
            command=self._connect_vps, width=14,
        ).pack(side="left", padx=4)
        ActionButton(
            vps_actions, text="⏹ Disconnect", bootstyle=WARNING,
            command=self._disconnect_vps, width=14,
        ).pack(side="left", padx=4)
        ActionButton(
            vps_actions, text="🔄 Refresh", bootstyle="secondary-outline",
            command=self.refresh, width=10,
        ).pack(side="right", padx=4)

        # === Tunnels Section ===
        tun_lf = ttk.LabelFrame(paned, text="  Tunnels Activos por VPS  ", bootstyle="info", padding=4)
        paned.add(tun_lf)

        tun_tree_frame = ttk.Frame(tun_lf, bootstyle="dark")
        tun_tree_frame.pack(fill="both", expand=True)

        tun_columns = [
            ("vps_id", "VPS", 120),
            ("name", "Nombre Tunnel", 140),
            ("remote_host", "Host Remoto", 140),
            ("remote_port", "Puerto Remoto", 110),
            ("local_port", "Puerto Local", 100),
            ("active", "Estado", 100),
        ]

        self.tun_tree = ttk.Treeview(
            tun_tree_frame,
            columns=[c[0] for c in tun_columns],
            show="headings",
            height=5,
            bootstyle="info",
        )
        for cid, title, width in tun_columns:
            self.tun_tree.heading(cid, text=title, anchor="w")
            self.tun_tree.column(cid, width=width, anchor="w", minwidth=70)

        vsb2 = ttk.Scrollbar(
            tun_tree_frame, orient="vertical", command=self.tun_tree.yview, bootstyle="round"
        )
        self.tun_tree.configure(yscrollcommand=vsb2.set)
        self.tun_tree.grid(row=0, column=0, sticky="nsew")
        vsb2.grid(row=0, column=1, sticky="ns")
        tun_tree_frame.rowconfigure(0, weight=1)
        tun_tree_frame.columnconfigure(0, weight=1)

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
            cfg = self.ctx.store.get()

            # Refresh VPS tree
            self.vps_tree.delete(*self.vps_tree.get_children())
            vps_list = cfg.publish.vps_list
            for v in vps_list:
                active_tuns = sum(
                    1 for t in cfg.forwarding.tunnels
                    if t.ssh_host == v.host and t.enabled
                )
                status = f"\u25cf {active_tuns} tunnel(s)" if active_tuns > 0 else "\u25cb Sin tunnels"
                self.vps_tree.insert(
                    "", "end",
                    values=(v.id, v.host, v.user, v.port, v.identity_file or "(default)", status),
                )

            # Refresh tunnels tree
            self.tun_tree.delete(*self.tun_tree.get_children())
            tuns_active = 0
            for t in cfg.forwarding.tunnels:
                is_active = t.enabled
                vps_id = ""
                for v in vps_list:
                    if t.ssh_host == v.host or t.remote_host == v.host:
                        vps_id = v.id
                        break
                if not vps_id:
                    continue
                status = "\u25cf Activo" if is_active else "\u25cb Inactivo"
                self.tun_tree.insert(
                    "", "end",
                    values=(
                        vps_id,
                        t.name,
                        t.remote_host,
                        t.remote_port,
                        t.local_port,
                        status,
                    ),
                )
                if is_active:
                    tuns_active += 1

            # Update stats cards
            vps_count = len(vps_list)
            tuns_shown = len(self.tun_tree.get_children())
            self.card_vps.set_value(str(vps_count))
            self.card_tunnels.set_value(str(tuns_active))
            self.card_inactive.set_value(str(max(0, vps_count - tuns_active)))

            self.status_var.set(f"{vps_count} VPS configurados, {tuns_shown} tunnels visibles")
            self.status_dot.set_state("running" if vps_count > 0 else "stopped")

        except Exception as e:  # noqa: BLE001
            log.exception("refresh publish tab fallo")
            self.status_var.set(f"Error: {e}")
            self.status_dot.set_state("error")
        finally:
            if self.winfo_exists():
                self._job = self.after(5000, self.refresh)

    def _selected_vps(self) -> str | None:
        sel = self.vps_tree.selection()
        if not sel:
            messagebox.showinfo("WSL Manager", "Selecciona un VPS")
            return None
        return self.tree_item_id(sel[0])

    def tree_item_id(self, item) -> str:
        return self.vps_tree.item(item, "values")[0]

    # ── Dialogo agregar VPS ─────────────────────────────────────────────
    def _add_vps_dialog(self) -> None:
        self._vps_dialog("Agregar VPS")

    def _edit_vps_dialog(self) -> None:
        vps_id = self._selected_vps()
        if not vps_id:
            return
        cfg = self.ctx.store.get()
        vps = next((v for v in cfg.publish.vps_list if v.id == vps_id), None)
        if not vps:
            messagebox.showerror("WSL Manager", f"VPS '{vps_id}' no encontrado")
            return
        self._vps_dialog("Editar VPS", vps=vps)

    def _vps_dialog(self, title: str, vps: VpsCfg | None = None) -> None:
        dlg = ttk.Toplevel(self)
        dlg.title(title)
        dlg.geometry("460x360")
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        ttk.Label(dlg, text=title, font=("Segoe UI", 13, "bold")).pack(pady=(12, 8))
        ttk.Separator(dlg, bootstyle="secondary").pack(fill="x", padx=16, pady=4)

        form = ttk.Frame(dlg, padding=8)
        form.pack(fill="x", padx=16)

        # ID
        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="ID:", width=16, anchor="w").pack(side="left")
        id_var = tk.StringVar(value=vps.id if vps else "")
        id_entry = ttk.Entry(row, textvariable=id_var, width=28, bootstyle="default")
        id_entry.pack(side="left", padx=(4, 0))
        if vps:
            id_entry.configure(state="disabled")

        # Host
        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Host:", width=16, anchor="w").pack(side="left")
        host_var = tk.StringVar(value=vps.host if vps else "")
        ttk.Entry(row, textvariable=host_var, width=28, bootstyle="default").pack(
            side="left", padx=(4, 0)
        )

        # User
        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Usuario:", width=16, anchor="w").pack(side="left")
        user_var = tk.StringVar(value=vps.user if vps else "root")
        ttk.Entry(row, textvariable=user_var, width=28, bootstyle="default").pack(
            side="left", padx=(4, 0)
        )

        # Puerto SSH
        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Puerto SSH:", width=16, anchor="w").pack(side="left")
        port_var = tk.StringVar(value=str(vps.port) if vps else "22")
        ttk.Entry(row, textvariable=port_var, width=28, bootstyle="default").pack(
            side="left", padx=(4, 0)
        )

        # Identity file
        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Clave SSH:", width=16, anchor="w").pack(side="left")
        ident_var = tk.StringVar(value=vps.identity_file if vps else "")
        ttk.Entry(row, textvariable=ident_var, width=28, bootstyle="default").pack(
            side="left", padx=(4, 0)
        )

        ttk.Separator(dlg, bootstyle="secondary").pack(fill="x", padx=16, pady=6)

        def _ok() -> None:
            try:
                vps_id = id_var.get().strip()
                if not vps_id:
                    messagebox.showwarning("WSL Manager", "El ID es obligatorio")
                    return
                host = host_var.get().strip()
                if not host:
                    messagebox.showwarning("WSL Manager", "El host es obligatorio")
                    return
                new_vps = VpsCfg(
                    id=vps_id,
                    host=host,
                    user=user_var.get().strip() or "root",
                    port=int(port_var.get()),
                    identity_file=ident_var.get().strip(),
                )
                if vps:
                    self.ctx.store.remove_vps(vps.id)
                self.ctx.store.add_vps(new_vps)
                dlg.destroy()
                self.refresh()
            except Exception as e:  # noqa: BLE001
                messagebox.showerror("WSL Manager", str(e))

        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(pady=12)
        ActionButton(btn_frame, text="Guardar", command=_ok, bootstyle=SUCCESS, width=14).pack(
            side="left", padx=6
        )
        ActionButton(btn_frame, text="Cancelar", command=dlg.destroy, bootstyle=DANGER, width=14).pack(
            side="left", padx=6
        )

    # ── Acciones VPS ────────────────────────────────────────────────────
    def _remove_vps(self) -> None:
        vps_id = self._selected_vps()
        if not vps_id:
            return
        if not messagebox.askyesno("WSL Manager", f"Eliminar VPS '{vps_id}'?"):
            return
        try:
            self.ctx.store.remove_vps(vps_id)
            self.refresh()
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("WSL Manager", str(e))

    def _connect_vps(self) -> None:
        """Abre un tunnel SSH al VPS seleccionado."""
        vps_id = self._selected_vps()
        if not vps_id:
            return
        cfg = self.ctx.store.get()
        vps = next((v for v in cfg.publish.vps_list if v.id == vps_id), None)
        if not vps:
            return

        # Dialog for tunnel configuration
        dlg = ttk.Toplevel(self)
        dlg.title(f"Conectar a {vps_id}")
        dlg.geometry("420x300")
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        ttk.Label(dlg, text=f"Abrir tunnel a {vps.host}", font=("Segoe UI", 13, "bold")).pack(
            pady=(12, 8)
        )
        ttk.Separator(dlg, bootstyle="secondary").pack(fill="x", padx=16, pady=4)

        form = ttk.Frame(dlg, padding=8)
        form.pack(fill="x", padx=16)

        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Nombre:", width=16, anchor="w").pack(side="left")
        name_var = tk.StringVar(value=f"pub-{vps_id}")
        ttk.Entry(row, textvariable=name_var, width=28, bootstyle="default").pack(
            side="left", padx=(4, 0)
        )

        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Puerto Remoto:", width=16, anchor="w").pack(side="left")
        remote_port_var = tk.StringVar(value="80")
        ttk.Entry(row, textvariable=remote_port_var, width=28, bootstyle="default").pack(
            side="left", padx=(4, 0)
        )

        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Puerto Local:", width=16, anchor="w").pack(side="left")
        local_port_var = tk.StringVar(value="8080")
        ttk.Entry(row, textvariable=local_port_var, width=28, bootstyle="default").pack(
            side="left", padx=(4, 0)
        )

        ttk.Separator(dlg, bootstyle="secondary").pack(fill="x", padx=16, pady=6)

        def _ok() -> None:
            try:
                from src.core.config import TunnelCfg

                name = name_var.get().strip()
                if not name:
                    messagebox.showwarning("WSL Manager", "El nombre es obligatorio")
                    return
                tun = TunnelCfg(
                    name=name,
                    remote_host=vps.host,
                    remote_port=int(remote_port_var.get()),
                    local_port=int(local_port_var.get()),
                    ssh_user=vps.user,
                    ssh_host=vps.host,
                    auto_reconnect=True,
                    enabled=True,
                )
                r = self.ctx.forwarding.add_tunnel(tun)
                if not r.get("ok"):
                    messagebox.showerror("WSL Manager", r.get("error", "error"))
                    return
                r2 = self.ctx.forwarding.start_tunnel(name)
                if not r2.get("ok"):
                    messagebox.showwarning(
                        "WSL Manager",
                        f"Tunnel creado pero no se pudo iniciar: {r2.get('error', '')}",
                    )
                dlg.destroy()
                self.refresh()
            except Exception as e:  # noqa: BLE001
                messagebox.showerror("WSL Manager", str(e))

        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(pady=12)
        ActionButton(btn_frame, text="Abrir Tunnel", command=_ok, bootstyle=PRIMARY, width=14).pack(
            side="left", padx=6
        )
        ActionButton(btn_frame, text="Cancelar", command=dlg.destroy, bootstyle=DANGER, width=14).pack(
            side="left", padx=6
        )

    def _disconnect_vps(self) -> None:
        """Cierra todos los tunnels del VPS seleccionado."""
        vps_id = self._selected_vps()
        if not vps_id:
            return
        if not messagebox.askyesno(
            "WSL Manager",
            f"Cerrar todos los tunnels del VPS '{vps_id}'?",
        ):
            return

        cfg = self.ctx.store.get()
        vps = next((v for v in cfg.publish.vps_list if v.id == vps_id), None)
        if not vps:
            return

        closed = 0
        for t in cfg.forwarding.tunnels:
            if (t.ssh_host == vps.host or t.remote_host == vps.host) and t.enabled:
                r = self.ctx.forwarding.stop_tunnel(t.name)
                if r.get("ok"):
                    closed += 1

        if closed:
            messagebox.showinfo("WSL Manager", f"{closed} tunnel(s) cerrado(s)")
        else:
            messagebox.showinfo("WSL Manager", "No hay tunnels activos para este VPS")
        self.refresh()

    def destroy(self) -> None:
        if self._job:
            self.after_cancel(self._job)
        super().destroy()
