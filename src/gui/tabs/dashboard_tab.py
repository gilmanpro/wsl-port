"""Pestana Dashboard (W1-W4): tabla de distros + ciclo de vida."""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from src.core.logger import get_logger
from src.gui.widgets import make_tree, status_text

log = get_logger("gui.dashboard")


class DashboardTab(ttk.Frame):
    def __init__(self, master, ctx) -> None:
        super().__init__(master)
        self.ctx = ctx
        self._build()
        self.refresh()

    def _build(self) -> None:
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=6, pady=6)
        ttk.Button(bar, text="🔄 Refrescar", command=self.refresh).pack(side="left", padx=2)
        ttk.Button(bar, text="⏹ Apagar todas", command=self._shutdown_all).pack(side="left", padx=2)
        ttk.Button(bar, text="▶ Iniciar todas", command=self._start_all).pack(side="left", padx=2)
        self.filter_var = tk.StringVar()
        ttk.Entry(bar, textvariable=self.filter_var, width=20).pack(side="right")
        ttk.Label(bar, text="Filtro:").pack(side="right", padx=2)
        self.filter_var.trace_add("write", lambda *_: self.refresh())

        self.tree = make_tree(
            self,
            [("name", "Distro", 180), ("state", "Estado", 90), ("ver", "WSL", 50), ("ip", "IP", 140), ("grp", "Grupo", 100)],
        )
        self.tree.bind("<Double-1>", lambda _e: self._actions())

        actions = ttk.Frame(self)
        actions.pack(fill="x", padx=6, pady=4)
        for text, cb in [
            ("▶ Iniciar", self._start),
            ("⏹ Detener", self._stop),
            ("↻ Reiniciar", self._restart),
            ("Terminal", self._shell),
            ("Explorador", self._explorer),
            ("Exportar...", self._export),
            ("Snapshot", self._snapshot),
            ("Clonar...", self._clone),
        ]:
            ttk.Button(actions, text=text, command=cb).pack(side="left", padx=2)

        self.status_var = tk.StringVar(value="cargando...")
        ttk.Label(self, textvariable=self.status_var).pack(anchor="w", padx=8, pady=(0, 4))

    # -- datos ----------------------------------------------------------------

    def refresh(self) -> None:
        try:
            distros = self.ctx.wsl.list_distros()
            for d in distros:
                if d.state == "Running":
                    d.ip = self.ctx.wsl.get_ip(d.name)
            inst = {i.name: i for i in self.ctx.config.distros.instances}
            self._distros = distros
            self.tree.delete(*self.tree.get_children())
            filtro = self.filter_var.get().lower()
            for d in distros:
                if filtro and filtro not in d.name.lower():
                    continue
                self.tree.insert(
                    "", "end",
                    values=(d.name, status_text(d.state), f"WSL{d.version}", d.ip or "-", inst.get(d.name).group if d.name in inst else ""),
                )
            running = sum(1 for d in distros if d.state == "Running")
            self.status_var.set(f"{running}/{len(distros)} distros corriendo")
        except Exception as e:  # noqa: BLE001
            log.exception("refresh dashboard fallo")
            self.status_var.set(f"error: {e}")

    def _selected(self) -> str | None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("WSL Manager", "Selecciona una distro")
            return None
        return self.tree.item(sel[0], "values")[0]

    # -- acciones ---------------------------------------------------------------

    def _run(self, fn, ok_msg: str) -> None:
        name = self._selected()
        if not name:
            return
        try:
            r = fn(name)
            if r and not r.ok:
                messagebox.showerror("WSL Manager", r.error)
                return
            self.ctx.metrics.log_event("gui_action", name, ok_msg)
            self.refresh()
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("WSL Manager", str(e))

    def _start(self) -> None:
        self._run(self.ctx.wsl.start, "iniciada desde GUI")

    def _stop(self) -> None:
        self._run(self.ctx.wsl.stop, "detenida desde GUI")

    def _restart(self) -> None:
        self._run(self.ctx.wsl.restart, "reiniciada desde GUI")

    def _shell(self) -> None:
        self._run(self.ctx.wsl.open_shell, "terminal abierta")

    def _explorer(self) -> None:
        self._run(self.ctx.wsl.open_explorer, "explorador abierto")

    def _export(self) -> None:
        name = self._selected()
        if not name:
            return
        path = filedialog.asksaveasfilename(defaultextension=".tar", initialfile=f"{name}.tar", filetypes=[("TAR", "*.tar")])
        if not path:
            return
        r = self.ctx.wsl.export(name, path)
        if not r.ok:
            messagebox.showerror("WSL Manager", r.error)
            return
        self.ctx.metrics.log_event("gui_export", name, f"exportada a {path}")
        messagebox.showinfo("WSL Manager", f"Exportada a {path}")

    def _snapshot(self) -> None:
        name = self._selected()
        if not name:
            return
        try:
            path = self.ctx.wsl.snapshot(name, self.ctx.config.snapshots.retention_days, self.ctx.config.snapshots.target_dir)
        except RuntimeError as e:
            messagebox.showerror("WSL Manager", str(e))
            return
        size = path.stat().st_size if path.exists() else 0
        self.ctx.metrics.record_snapshot(name, str(path), size)
        messagebox.showinfo("WSL Manager", f"Snapshot: {path}\n({size / 1e6:.1f} MB)")

    def _clone(self) -> None:
        import tkinter.simpledialog as sd

        name = self._selected()
        if not name:
            return
        new_name = sd.askstring("Clonar", f"Nuevo nombre para clon de {name}:")
        if not new_name:
            return
        r = self.ctx.wsl.clone(name, new_name)
        if not r.ok:
            messagebox.showerror("WSL Manager", r.error)
            return
        self.refresh()

    def _start_all(self) -> None:
        for d in self.ctx.wsl.list_distros():
            self.ctx.wsl.start(d.name)
        self.refresh()

    def _shutdown_all(self) -> None:
        if messagebox.askyesno("WSL Manager", "¿Apagar TODAS las distros?"):
            self.ctx.wsl.shutdown_all()
            self.refresh()
