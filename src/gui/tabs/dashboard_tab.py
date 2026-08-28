"""Pestana Dashboard (W1-W4): tabla de distros + ciclo de vida — ttkbootstrap moderno."""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from src.core.logger import get_logger
from src.gui.widgets import StatCard, StatusDot, ActionButton, SectionHeader, COLORS

log = get_logger("gui.dashboard")


class DashboardTab(ttk.Frame):
    def __init__(self, master, ctx) -> None:
        super().__init__(master)
        self.ctx = ctx
        self._job = None
        self._build()
        self.refresh()

    def _build(self) -> None:
        # ════════════════════════════════════════════════════════════════════
        #  HEADER CON STATS CARDS
        # ════════════════════════════════════════════════════════════════════
        header_frame = ttk.Frame(self, bootstyle="dark")
        header_frame.pack(fill="x", padx=12, pady=(10, 4))

        SectionHeader(header_frame, text="\U0001f4ca Dashboard de Distros").pack(side="left")

        cards_frame = ttk.Frame(self, bootstyle="dark")
        cards_frame.pack(fill="x", padx=12, pady=(0, 8))

        self.card_total = StatCard(cards_frame, value="0", label="Total Distros", bootstyle="info", icon="\U0001f4e6")
        self.card_total.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.card_running = StatCard(cards_frame, value="0", label="Running", bootstyle="success", icon="\u25b6")
        self.card_running.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.card_stopped = StatCard(cards_frame, value="0", label="Stopped", bootstyle="secondary", icon="\u23f9")
        self.card_stopped.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.card_alerts = StatCard(cards_frame, value="0", label="Alertas", bootstyle="danger", icon="\u26a0")
        self.card_alerts.pack(side="left", fill="x", expand=True)

        ttk.Separator(self, bootstyle="secondary").pack(fill="x", padx=12, pady=4)

        # ════════════════════════════════════════════════════════════════════
        #  BARRA DE HERRAMIENTAS MODERNA
        # ════════════════════════════════════════════════════════════════════
        toolbar = ttk.Frame(self, bootstyle="dark")
        toolbar.pack(fill="x", padx=12, pady=(0, 4))

        ActionButton(toolbar, text="\U0001f504 Refrescar", bootstyle=PRIMARY, command=self.refresh, width=14).pack(side="left", padx=4)
        ActionButton(toolbar, text="\u25b6 Iniciar todas", bootstyle=SUCCESS, command=self._start_all, width=14).pack(side="left", padx=4)
        ActionButton(toolbar, text="\u23f9 Apagar todas", bootstyle=DANGER, command=self._shutdown_all, width=14).pack(side="left", padx=4)

        # Filtro a la derecha
        filter_frame = ttk.Frame(toolbar, bootstyle="dark")
        filter_frame.pack(side="right")
        ttk.Label(filter_frame, text="\U0001f50d Filtro:", foreground=COLORS["muted"], bootstyle="dark", font=("Segoe UI", 9)).pack(side="left", padx=(0, 4))
        self.filter_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.filter_var, width=22, bootstyle="default").pack(side="right")
        self.filter_var.trace_add("write", lambda *_: self.refresh())

        ttk.Separator(self, bootstyle="secondary").pack(fill="x", padx=12, pady=4)

        # ════════════════════════════════════════════════════════════════════
        #  TABLA DE DISTROS MEJORADA
        # ════════════════════════════════════════════════════════════════════
        tree_frame = ttk.Frame(self, bootstyle="dark")
        tree_frame.pack(fill="both", expand=True, padx=12, pady=4)

        columns = [
            ("name", "Distro", 180),
            ("state", "Estado", 100),
            ("ver", "WSL", 60),
            ("ip", "IP", 150),
            ("grp", "Grupo", 120),
            ("ram", "RAM%", 80),
        ]

        self.tree = ttk.Treeview(
            tree_frame,
            columns=[c[0] for c in columns],
            show="headings",
            height=14,
            bootstyle="primary",
        )
        for cid, title, width in columns:
            self.tree.heading(cid, text=title, anchor="w")
            self.tree.column(cid, width=width, anchor="w", minwidth=60)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview, bootstyle="round")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview, bootstyle="round")
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", lambda _e: self._actions())

        # Tag para filas alternas
        self.tree.tag_configure("running", foreground=COLORS["success"])
        self.tree.tag_configure("stopped", foreground=COLORS["muted"])
        self.tree.tag_configure("odd", background="#1a2030")
        self.tree.tag_configure("even", background="#1d2430")

        ttk.Separator(self, bootstyle="secondary").pack(fill="x", padx=12, pady=4)

        # ════════════════════════════════════════════════════════════════════
        #  BOTONES DE ACCION
        # ════════════════════════════════════════════════════════════════════
        actions = ttk.Frame(self, bootstyle="dark")
        actions.pack(fill="x", padx=12, pady=(0, 8))

        for text, cb, style in [
            ("\u25b6 Iniciar", self._start, SUCCESS),
            ("\u23f9 Detener", self._stop, DANGER),
            ("\u21bb Reiniciar", self._restart, WARNING),
            ("\U0001f5a5 Terminal", self._shell, INFO),
            ("\U0001f4c1 Explorador", self._explorer, INFO),
            ("\U0001f4e4 Exportar", self._export, PRIMARY),
            ("\U0001f4be Snapshot", self._snapshot, SUCCESS),
            ("\U0001f4cc Clonar", self._clone, SECONDARY),
        ]:
            ActionButton(actions, text=text, bootstyle=style, command=cb, width=14).pack(side="left", padx=3)

        # ════════════════════════════════════════════════════════════════════
        #  BARRA DE ESTADO INFERIOR
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

        self.auto_refresh_label = ttk.Label(
            status_bar,
            text="Auto-refresh: 5s",
            foreground=COLORS["muted"],
            font=("Segoe UI", 8),
            bootstyle="dark",
        )
        self.auto_refresh_label.pack(side="right")

    # ── datos ----------------------------------------------------------------

    def refresh(self) -> None:
        try:
            distros = self.ctx.wsl.list_distros()
            for d in distros:
                if d.state == "Running":
                    d.ip = self.ctx.wsl.get_ip(d.name)
            inst = {i.name: i for i in self.ctx.config.distros.instances}
            self._distros = distros
            # Safe delete: catch TclError for stale items
            try:
                self.tree.delete(*self.tree.get_children())
            except tk.TclError:
                pass
            filtro = self.filter_var.get().lower()

            running_count = 0
            stopped_count = 0
            alerts = 0

            for idx, d in enumerate(distros):
                if filtro and filtro not in d.name.lower():
                    continue
                is_running = d.state == "Running"
                state_display = "\u25cf RUNNING" if is_running else "\u25cb stopped"
                row_tag = "running" if is_running else "stopped"
                alt_tag = "odd" if idx % 2 else "even"

                # Try to get RAM info
                ram_pct = ""
                try:
                    info = getattr(d, 'memory_usage', None)
                    if info:
                        ram_pct = f"{info}%"
                except Exception:
                    pass

                self.tree.insert(
                    "", "end",
                    values=(
                        d.name,
                        state_display,
                        f"WSL{d.version}",
                        d.ip or "-",
                        inst.get(d.name).group if d.name in inst else "",
                        ram_pct,
                    ),
                    tags=(row_tag, alt_tag),
                )
                if is_running:
                    running_count += 1
                else:
                    stopped_count += 1

            # Update stats cards
            self.card_total.set_value(str(len(distros)))
            self.card_running.set_value(str(running_count))
            self.card_stopped.set_value(str(stopped_count))
            self.card_alerts.set_value(str(alerts))

            # Update status bar
            self.status_var.set(f"{running_count}/{len(distros)} distros corriendo")

            # Update status dot
            if running_count > 0:
                self.status_dot.set_state("running")
            else:
                self.status_dot.set_state("stopped")

        except Exception as e:  # noqa: BLE001
            log.exception("refresh dashboard fallo")
            self.status_var.set(f"Error: {e}")
            self.status_dot.set_state("error")
        finally:
            if self.winfo_exists():
                self._job = self.after(5000, self.refresh)

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
        path = filedialog.asksaveasfilename(
            defaultextension=".tar", initialfile=f"{name}.tar", filetypes=[("TAR", "*.tar")]
        )
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
            path = self.ctx.wsl.snapshot(
                name, self.ctx.config.snapshots.retention_days, self.ctx.config.snapshots.target_dir
            )
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
        if messagebox.askyesno("WSL Manager", "\u00bfApagar TODAS las distros?"):
            self.ctx.wsl.shutdown_all()
            self.refresh()

    def _actions(self) -> None:
        """Double-click action on tree row."""
        self._shell()

    def destroy(self) -> None:
        if self._job:
            self.after_cancel(self._job)
        super().destroy()
