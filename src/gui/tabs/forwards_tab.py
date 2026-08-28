"""Pestana Forwards: lista de port-forwards Windows -> WSL con CRUD."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from src.core.config import ForwardItem
from src.core.logger import get_logger
from src.gui.widgets import make_tree

log = get_logger("gui.forwards")


class ForwardsTab(ttk.Frame):
    """Pestana de port-forwarding (Windows -> WSL via netsh portproxy)."""

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
        ttk.Button(bar, text="Aplicar todos", command=self._apply_all).pack(side="left", padx=2)
        ttk.Button(bar, text="Limpiar todo", command=self._clear_all).pack(side="left", padx=2)

        # --- tree ---
        self.tree = make_tree(
            self,
            [
                ("name", "Nombre", 160),
                ("local_port", "Puerto Local", 100),
                ("wsl_ip", "WSL IP", 140),
                ("wsl_port", "WSL Port", 100),
                ("enabled", "Habilitado", 80),
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
            forwards = self.ctx.forwarding.list_forwards()
            self.tree.delete(*self.tree.get_children())
            for f in forwards:
                status = "● ACTIVO" if f.get("active") else "○ inactivo"
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        f.get("name", ""),
                        f.get("local_port", ""),
                        f.get("wsl_ip", ""),
                        f.get("wsl_port", ""),
                        "Si" if f.get("enabled") else "No",
                        status,
                    ),
                )
            active = sum(1 for f in forwards if f.get("active"))
            self.status_var.set(
                f"{active}/{len(forwards)} forwards activos"
            )
        except Exception as e:  # noqa: BLE001
            log.exception("refresh forwards fallo")
            self.status_var.set(f"error: {e}")
        finally:
            if self.winfo_exists():
                self._job = self.after(5000, self.refresh)

    def _selected(self) -> str | None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("WSL Manager", "Selecciona un forward")
            return None
        return self.tree.item(sel[0], "values")[0]

    # -- acciones -----------------------------------------------------------

    def _add_dialog(self) -> None:
        """Dialogo para agregar un forward."""
        dlg = tk.Toplevel(self)
        dlg.title("Agregar Forward")
        dlg.geometry("380x320")
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        fields = {}
        for i, (label, key, default) in enumerate([
            ("Nombre:", "name", ""),
            ("Puerto Local:", "local_port", "8080"),
            ("WSL IP:", "wsl_ip", "127.0.0.1"),
            ("WSL Port:", "wsl_port", "80"),
        ]):
            ttk.Label(dlg, text=label).grid(row=i, column=0, sticky="w", padx=8, pady=4)
            var = tk.StringVar(value=default)
            entry = ttk.Entry(dlg, textvariable=var, width=28)
            entry.grid(row=i, column=1, padx=8, pady=4)
            fields[key] = var

        enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(dlg, text="Habilitado", variable=enabled_var).grid(
            row=4, column=0, columnspan=2, sticky="w", padx=8, pady=4
        )

        def _ok() -> None:
            try:
                name = fields["name"].get().strip()
                if not name:
                    messagebox.showwarning("WSL Manager", "El nombre es obligatorio")
                    return
                fwd = ForwardItem(
                    name=name,
                    local_port=int(fields["local_port"].get()),
                    wsl_port=int(fields["wsl_port"].get()),
                    wsl_ip=fields["wsl_ip"].get().strip() or "127.0.0.1",
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
        btn_frame.grid(row=5, column=0, columnspan=2, pady=12)
        ttk.Button(btn_frame, text="Agregar", command=_ok).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Cancelar", command=dlg.destroy).pack(side="left", padx=4)

    def _remove(self) -> None:
        name = self._selected()
        if not name:
            return
        if not messagebox.askyesno("WSL Manager", f"¿Eliminar forward '{name}'?"):
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
            "WSL Manager", "¿Limpiar TODOS los portproxies? Esto es destructivo."
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
