"""Pestana Tunnels: lista de tunnels SSH con CRUD y reconexion."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from src.core.config import TunnelCfg
from src.core.logger import get_logger
from src.gui.widgets import make_tree

log = get_logger("gui.tunnels")


class TunnelsTab(ttk.Frame):
    """Pestana de tunnels SSH (con indicador de reconexion automatica)."""

    def __init__(self, master, ctx) -> None:
        super().__init__(master)
        self.ctx = ctx
        self._job: str | None = None
        self._build()
        self.refresh()

    def _build(self) -> None:
        # --- toolbar ---
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=6, pady=6)
        ttk.Button(bar, text="🔄 Refrescar", command=self.refresh).pack(side="left", padx=2)
        ttk.Button(bar, text="➕ Agregar...", command=self._add_dialog).pack(side="left", padx=2)
        ttk.Button(bar, text="🗑 Eliminar", command=self._remove).pack(side="left", padx=2)
        ttk.Button(bar, text="▶ Iniciar", command=self._start).pack(side="left", padx=2)
        ttk.Button(bar, text="⏹ Detener", command=self._stop).pack(side="left", padx=2)

        # --- tree ---
        self.tree = make_tree(
            self,
            [
                ("name", "Nombre", 140),
                ("remote_host", "Host Remoto", 150),
                ("remote_port", "Puerto Remoto", 100),
                ("local_port", "Puerto Local", 100),
                ("ssh_user", "Usuario SSH", 100),
                ("ssh_host", "SSH Host", 150),
                ("auto_reconnect", "Reconexion", 90),
                ("active", "Estado", 100),
            ],
        )

        # --- status ---
        self.status_var = tk.StringVar(value="cargando...")
        ttk.Label(self, textvariable=self.status_var, foreground="#888").pack(
            anchor="w", padx=8, pady=(0, 4)
        )

    # -- datos --------------------------------------------------------------

    def refresh(self) -> None:
        try:
            tunnels = self.ctx.forwarding.list_tunnels()
            self.tree.delete(*self.tree.get_children())
            for t in tunnels:
                status = "● ACTIVO" if t.get("active") else "○ inactivo"
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
            self.status_var.set(
                f"{active}/{len(tunnels)} tunnels activos"
            )
        except Exception as e:  # noqa: BLE001
            log.exception("refresh tunnels fallo")
            self.status_var.set(f"error: {e}")
        finally:
            if self.winfo_exists():
                self._job = self.after(5000, self.refresh)

    def _selected(self) -> str | None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("WSL Manager", "Selecciona un tunnel")
            return None
        return self.tree.item(sel[0], "values")[0]

    # -- acciones -----------------------------------------------------------

    def _add_dialog(self) -> None:
        """Dialogo para agregar un tunnel."""
        dlg = tk.Toplevel(self)
        dlg.title("Agregar Tunnel")
        dlg.geometry("400x380")
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        fields = {}
        for i, (label, key, default) in enumerate([
            ("Nombre:", "name", ""),
            ("Host Remoto:", "remote_host", ""),
            ("Puerto Remoto:", "remote_port", "22"),
            ("Puerto Local:", "local_port", "2222"),
            ("Usuario SSH:", "ssh_user", "root"),
            ("SSH Host:", "ssh_host", ""),
        ]):
            ttk.Label(dlg, text=label).grid(row=i, column=0, sticky="w", padx=8, pady=3)
            var = tk.StringVar(value=default)
            entry = ttk.Entry(dlg, textvariable=var, width=28)
            entry.grid(row=i, column=1, padx=8, pady=3)
            fields[key] = var

        auto_reconnect_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(dlg, text="Reconexion automatica", variable=auto_reconnect_var).grid(
            row=6, column=0, columnspan=2, sticky="w", padx=8, pady=4
        )

        enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(dlg, text="Habilitado", variable=enabled_var).grid(
            row=7, column=0, columnspan=2, sticky="w", padx=8, pady=4
        )

        def _ok() -> None:
            try:
                name = fields["name"].get().strip()
                if not name:
                    messagebox.showwarning("WSL Manager", "El nombre es obligatorio")
                    return
                tun = TunnelCfg(
                    name=name,
                    remote_host=fields["remote_host"].get().strip(),
                    remote_port=int(fields["remote_port"].get()),
                    local_port=int(fields["local_port"].get()),
                    ssh_user=fields["ssh_user"].get().strip(),
                    ssh_host=fields["ssh_host"].get().strip(),
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
        btn_frame.grid(row=8, column=0, columnspan=2, pady=12)
        ttk.Button(btn_frame, text="Agregar", command=_ok).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Cancelar", command=dlg.destroy).pack(side="left", padx=4)

    def _remove(self) -> None:
        name = self._selected()
        if not name:
            return
        if not messagebox.askyesno("WSL Manager", f"¿Eliminar tunnel '{name}'?"):
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
