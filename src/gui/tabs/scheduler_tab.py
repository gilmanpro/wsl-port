"""Pestana Programador (A2): tareas programadas — ttkbootstrap moderno."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from src.core.config import ScheduleAction, ScheduleSpec, ScheduleTask
from src.core.logger import get_logger
from src.core.scheduler import Scheduler
from src.gui.widgets import StatCard, StatusDot, ActionButton, SectionHeader, COLORS

log = get_logger("gui.scheduler")


class SchedulerTab(ttk.Frame):
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

        SectionHeader(header, text="\U0001f4c5 Programador de Tareas").pack(side="left")

        ActionButton(header, text="\U0001f504 Refrescar", bootstyle=INFO, command=self.refresh, width=14).pack(side="right", padx=4)
        ActionButton(header, text="\u25b6 Ejecutar ahora", bootstyle=SUCCESS, command=self._run_now, width=14).pack(side="right", padx=4)
        ActionButton(header, text="\u270f Editar", bootstyle=WARNING, command=self._edit, width=14).pack(side="right", padx=4)
        ActionButton(header, text="\u2212 Eliminar", bootstyle=DANGER, command=self._remove, width=14).pack(side="right", padx=4)
        ActionButton(header, text="\uff0b Nueva tarea", bootstyle=PRIMARY, command=self._add, width=14).pack(side="right", padx=4)

        # ════════════════════════════════════════════════════════════════════
        #  STATS CARDS
        # ════════════════════════════════════════════════════════════════════
        cards_frame = ttk.Frame(self, bootstyle="dark")
        cards_frame.pack(fill="x", padx=12, pady=(0, 8))

        self.card_total = StatCard(cards_frame, value="0", label="Total Tareas", bootstyle="info", icon="\U0001f4cb")
        self.card_total.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.card_enabled = StatCard(cards_frame, value="0", label="Habilitadas", bootstyle="success", icon="\u25b6")
        self.card_enabled.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.card_disabled = StatCard(cards_frame, value="0", label="Deshabilitadas", bootstyle="secondary", icon="\u23f9")
        self.card_disabled.pack(side="left", fill="x", expand=True)

        ttk.Separator(self, bootstyle="secondary").pack(fill="x", padx=12, pady=4)

        # ════════════════════════════════════════════════════════════════════
        #  TABLA DE TAREAS
        # ════════════════════════════════════════════════════════════════════
        tree_frame = ttk.Frame(self, bootstyle="dark")
        tree_frame.pack(fill="both", expand=True, padx=12, pady=4)

        columns = [
            ("id", "ID", 120),
            ("name", "Nombre", 160),
            ("type", "Accion", 110),
            ("target", "Objetivo", 120),
            ("time", "Hora", 60),
            ("days", "Dias", 140),
            ("enabled", "Habilitado", 90),
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
        self.tree.tag_configure("enabled_row", foreground=COLORS["success"])
        self.tree.tag_configure("disabled_row", foreground=COLORS["muted"])
        self.tree.tag_configure("odd", background="#1a2030")
        self.tree.tag_configure("even", background="#1d2430")

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
            tasks = self.ctx.store.get().scheduler.tasks
            try:
                self.tree.delete(*self.tree.get_children())
            except tk.TclError:
                pass

            enabled_count = 0
            disabled_count = 0

            for idx, t in enumerate(tasks):
                target = t.action.distro or t.action.profile or ""
                days = ",".join(d[:2] for d in t.schedule.days)
                is_enabled = t.enabled
                status = "Si" if is_enabled else "No"
                row_tag = "enabled_row" if is_enabled else "disabled_row"
                alt_tag = "odd" if idx % 2 else "even"

                self.tree.insert(
                    "", "end",
                    values=(t.id, t.name, t.action.type, target, t.schedule.time, days, status),
                    tags=(row_tag, alt_tag),
                )
                if is_enabled:
                    enabled_count += 1
                else:
                    disabled_count += 1

            self.card_total.set_value(str(len(tasks)))
            self.card_enabled.set_value(str(enabled_count))
            self.card_disabled.set_value(str(disabled_count))

            self.status_var.set(f"{len(tasks)} tareas programadas ({enabled_count} habilitadas)")
            self.status_dot.set_state("running" if enabled_count > 0 else "stopped")

        except Exception as e:  # noqa: BLE001
            log.exception("refresh scheduler fallo")
            self.status_var.set(f"Error: {e}")
            self.status_dot.set_state("error")

    def _selected(self) -> str | None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("WSL Manager", "Selecciona una tarea")
            return None
        return self.tree.item(sel[0], "values")[0]

    def _add(self) -> None:
        import uuid

        from tkinter import simpledialog

        distros = [d.name for d in self.ctx.wsl.list_distros()]

        class _Dialog(simpledialog.Dialog):
            def body(self, master):
                self.name = tk.StringVar(value="Iniciar dev")
                self.type_ = tk.StringVar(value="distro_start")
                self.distro = tk.StringVar(value=distros[0] if distros else "")
                self.time = tk.StringVar(value="09:00")
                self.days = tk.StringVar(value="mon,tue,wed,thu,fri")
                ttk.Label(master, text="Nombre:").grid(row=0, column=0, sticky="w")
                ttk.Entry(master, textvariable=self.name, width=20).grid(row=0, column=1, padx=4, pady=2)
                ttk.Label(master, text="Accion:").grid(row=1, column=0, sticky="w")
                ttk.Combobox(
                    master, textvariable=self.type_, values=["distro_start", "distro_stop", "snapshot", "apply_profile"], state="readonly", width=18
                ).grid(row=1, column=1, padx=4, pady=2)
                ttk.Label(master, text="Distro:").grid(row=2, column=0, sticky="w")
                ttk.Combobox(master, textvariable=self.distro, values=distros, state="readonly", width=18).grid(row=2, column=1, padx=4, pady=2)
                ttk.Label(master, text="Hora (HH:MM):").grid(row=3, column=0, sticky="w")
                ttk.Entry(master, textvariable=self.time, width=10).grid(row=3, column=1, sticky="w", padx=4, pady=2)
                ttk.Label(master, text="Dias (mon,tue,...):").grid(row=4, column=0, sticky="w")
                ttk.Entry(master, textvariable=self.days, width=20).grid(row=4, column=1, padx=4, pady=2)

            def apply(self):
                self.result = (self.name.get(), self.type_.get(), self.distro.get(), self.time.get(), self.days.get())

        dlg = _Dialog(self, title="Nueva tarea")
        if not dlg.result:
            return
        name, type_, distro, time_, days = dlg.result
        task = ScheduleTask(
            id=f"tarea-{uuid.uuid4().hex[:8]}",
            name=name,
            action=ScheduleAction(type=type_, distro=distro or None),  # type: ignore[arg-type]
            schedule=ScheduleSpec(days=[d.strip() for d in days.split(",")], time=time_),
        )
        Scheduler(self.ctx.store, self.ctx.metrics, self.ctx.bus, self.ctx.wsl).add_task(task)
        self.ctx.metrics.log_event("gui_schedule", message=f"tarea {name} creada")
        self.refresh()

    def _edit(self) -> None:
        """Abrir dialogo para editar la tarea seleccionada."""
        task_id = self._selected()
        if not task_id:
            return

        tasks = self.ctx.store.get().scheduler.tasks
        task = next((t for t in tasks if t.id == task_id), None)
        if not task:
            messagebox.showerror("WSL Manager", f"Tarea '{task_id}' no encontrada")
            return

        distros = [d.name for d in self.ctx.wsl.list_distros()]

        dlg = ttk.Toplevel(self)
        dlg.title(f"Editar tarea: {task.name}")
        dlg.geometry("440x400")
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        ttk.Label(dlg, text=f"Editar tarea: {task.name}", font=("Segoe UI", 13, "bold")).pack(pady=(12, 8))
        ttk.Separator(dlg, bootstyle="secondary").pack(fill="x", padx=16, pady=4)

        form = ttk.Frame(dlg, padding=8)
        form.pack(fill="x", padx=16)

        # Nombre
        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Nombre:", width=14, anchor="w").pack(side="left")
        name_var = tk.StringVar(value=task.name)
        ttk.Entry(row, textvariable=name_var, width=26, bootstyle="default").pack(side="left", padx=(4, 0))

        # Accion
        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Accion:", width=14, anchor="w").pack(side="left")
        type_var = tk.StringVar(value=task.action.type)
        ttk.Combobox(
            row, textvariable=type_var, values=["distro_start", "distro_stop", "snapshot", "apply_profile"],
            state="readonly", width=24,
        ).pack(side="left", padx=(4, 0))

        # Distro
        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Distro:", width=14, anchor="w").pack(side="left")
        distro_var = tk.StringVar(value=task.action.distro or "")
        ttk.Combobox(row, textvariable=distro_var, values=distros, state="readonly", width=24).pack(side="left", padx=(4, 0))

        # Hora
        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Hora (HH:MM):", width=14, anchor="w").pack(side="left")
        time_var = tk.StringVar(value=task.schedule.time)
        ttk.Entry(row, textvariable=time_var, width=12, bootstyle="default").pack(side="left", padx=(4, 0))

        # Dias
        row = ttk.Frame(form)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="Dias:", width=14, anchor="w").pack(side="left")
        days_var = tk.StringVar(value=",".join(task.schedule.days))
        ttk.Entry(row, textvariable=days_var, width=24, bootstyle="default").pack(side="left", padx=(4, 0))

        # Habilitado
        enabled_var = tk.BooleanVar(value=task.enabled)
        ttk.Checkbutton(form, text="Habilitado", variable=enabled_var, bootstyle="success").pack(anchor="w", pady=6)

        ttk.Separator(dlg, bootstyle="secondary").pack(fill="x", padx=16, pady=4)

        def _save() -> None:
            new_name = name_var.get().strip()
            if not new_name:
                messagebox.showwarning("WSL Manager", "El nombre es obligatorio")
                return
            try:
                cfg = self.ctx.store.get()
                updated = False
                for i, t in enumerate(cfg.scheduler.tasks):
                    if t.id == task_id:
                        cfg.scheduler.tasks[i] = ScheduleTask(
                            id=task_id,
                            name=new_name,
                            action=ScheduleAction(type=type_var.get(), distro=distro_var.get() or None),
                            schedule=ScheduleSpec(
                                days=[d.strip() for d in days_var.get().split(",")],
                                time=time_var.get(),
                            ),
                            enabled=enabled_var.get(),
                        )
                        updated = True
                        break
                if updated:
                    self.ctx.store.save(cfg)
                self.ctx.metrics.log_event("gui_schedule_edit", message=f"tarea {task_id} editada")
                dlg.destroy()
                self.refresh()
            except Exception as e:  # noqa: BLE001
                messagebox.showerror("WSL Manager", str(e))

        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(pady=12)
        ActionButton(btn_frame, text="Guardar", command=_save, bootstyle=SUCCESS, width=14).pack(side="left", padx=6)
        ActionButton(btn_frame, text="Cancelar", command=dlg.destroy, bootstyle=DANGER, width=14).pack(side="left", padx=6)

    def _remove(self) -> None:
        task_id = self._selected()
        if not task_id:
            return
        if not messagebox.askyesno("WSL Manager", f"Eliminar tarea '{task_id}'?"):
            return
        s = Scheduler(self.ctx.store, self.ctx.metrics, self.ctx.bus, self.ctx.wsl)
        if s.remove_task(task_id):
            self.ctx.metrics.log_event("gui_schedule_remove", message=f"tarea {task_id} eliminada")
            self.refresh()

    def _run_now(self) -> None:
        task_id = self._selected()
        if not task_id:
            return
        s = Scheduler(self.ctx.store, self.ctx.metrics, self.ctx.bus, self.ctx.wsl)
        ok = s.run_task(task_id)
        messagebox.showinfo("WSL Manager", "Tarea ejecutada OK" if ok else "La tarea fallo (ver logs)")
        self.refresh()
