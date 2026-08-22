"""Ventana integrada de wsl-port: distros WSL + tunnels/forwards + publicar."""
from __future__ import annotations

import datetime
import queue
import threading
import tkinter as tk
import webbrowser
from tkinter import ttk as _ttk, filedialog
from pathlib import Path

import ttkbootstrap as ttk

from .. import core
from .publish_tab import PublishTab

_FONT = "Segoe UI"


def _fmt_bytes(n) -> str:
    n = float(n or 0)
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or u == "TB":
            return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} TB"


def _make_tree(parent, columns: list[str], widths: list[int]) -> _ttk.Treeview:
    tv = _ttk.Treeview(parent, columns=columns, show="headings", height=8)
    for col, w in zip(columns, widths):
        tv.heading(col, text=col)
        tv.column(col, width=w, anchor="w")
    tv.pack(fill="both", expand=True, padx=6, pady=(0, 6))
    return tv


class _FormDialog(tk.Toplevel):
    """Dialogo modal generico con campos dinamicos."""
    def __init__(self, parent, title: str, fields: list[tuple[str, str, str]],
                 validate=None, size=(420, 400)):
        super().__init__(parent)
        self.title(title)
        self.geometry(f"{size[0]}x{size[1]}")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.result = None
        self._validate = validate

        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)

        self._vars: dict[str, tk.Variable] = {}
        for i, (key, label, kind) in enumerate(fields):
            ttk.Label(frame, text=label + ":").grid(row=i, column=0, sticky="w", pady=4)
            if kind == "entry":
                var = tk.StringVar()
                ttk.Entry(frame, textvariable=var, width=30).grid(
                    row=i, column=1, sticky="w", padx=8, pady=4)
            elif kind == "password":
                var = tk.StringVar()
                ttk.Entry(frame, textvariable=var, width=30, show="*").grid(
                    row=i, column=1, sticky="w", padx=8, pady=4)
            elif kind == "int":
                var = tk.IntVar(value=0)
                ttk.Entry(frame, textvariable=var, width=10).grid(
                    row=i, column=1, sticky="w", padx=8, pady=4)
            elif kind == "combo":
                var = tk.StringVar()
                ttk.Combobox(frame, textvariable=var, width=27, state="readonly").grid(
                    row=i, column=1, sticky="w", padx=8, pady=4)
            elif kind == "file":
                var = tk.StringVar()
                f = ttk.Frame(frame)
                f.grid(row=i, column=1, sticky="w", padx=8, pady=4)
                ttk.Entry(f, textvariable=var, width=22).pack(side="left")
                ttk.Button(f, text="...", width=3,
                           command=lambda v=var: self._browse(v)).pack(side="left", padx=2)
            else:
                var = tk.StringVar()
                ttk.Entry(frame, textvariable=var, width=30).grid(
                    row=i, column=1, sticky="w", padx=8, pady=4)
            self._vars[key] = var

        btns = ttk.Frame(frame)
        btns.grid(row=len(fields), column=0, columnspan=2, pady=(16, 0))
        ttk.Button(btns, text="Aceptar", bootstyle="success",
                   command=self._ok).pack(side="left", padx=6)
        ttk.Button(btns, text="Cancelar", bootstyle="secondary",
                   command=self.cancel).pack(side="left", padx=6)

        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.cancel())

    def _browse(self, var: tk.StringVar):
        p = filedialog.askopenfilename(title="Seleccionar clave SSH")
        if p:
            var.set(p)

    def set_combo_values(self, key: str, values: list[str]):
        var = self._vars.get(key)
        if var and hasattr(self, "_vars"):
            for child in self.winfo_children():
                for sub in child.winfo_children():
                    if isinstance(sub, ttk.Combobox) and sub.cget("textvariable") == str(var):
                        sub["values"] = values
                        if values:
                            var.set(values[0])

    def _ok(self):
        data = {}
        for key, var in self._vars.items():
            try:
                data[key] = var.get()
            except Exception:
                data[key] = ""
        if self._validate:
            try:
                self._validate(data)
            except ValueError as e:
                from tkinter import messagebox
                messagebox.showerror("Validacion", str(e), parent=self)
                return
        self.result = data
        self.destroy()

    def cancel(self):
        self.result = None
        self.destroy()


class MainWindow:
    def __init__(self) -> None:
        self.root = ttk.Window(themename="darkly", title="wsl-port — WSL + Port Forwarding")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 650)
        self._q: queue.Queue = queue.Queue()
        self._build()
        self._refresh()
        self.root.after(200, self._poll)
        self.root.after(15000, self._schedule_refresh)
        self.root.lift()
        self.root.focus_force()

    # -- UI ------------------------------------------------------------------

    def _build(self) -> None:
        style = ttk.Style()
        style.configure("Treeview", rowheight=26, font=(_FONT, 10))
        style.configure("Treeview.Heading", font=(_FONT, 10, "bold"))
        style.configure("Header.TLabel", font=(_FONT, 14, "bold"))
        style.configure("Muted.TLabel", foreground="#8f9aa8")

        header = ttk.Frame(self.root, padding=(16, 12))
        header.pack(fill="x")
        ttk.Label(header, text="wsl-port", style="Header.TLabel").pack(side="left")
        ttk.Label(header, text="WSL Manager + Port Forwarding integrados",
                  style="Muted.TLabel").pack(side="left", padx=(10, 0))
        self.header_status = ttk.Label(header, text="", style="Muted.TLabel")
        self.header_status.pack(side="right")
        ttk.Separator(self.root).pack(fill="x")

        nb = ttk.Notebook(self.root, padding=6)
        nb.pack(fill="both", expand=True, padx=8, pady=(4, 0))

        # -- pestana Distros WSL -------------------------------------------------
        d_tab = ttk.Frame(nb)
        nb.add(d_tab, text="  Distros WSL  ")
        d_bar = ttk.Frame(d_tab)
        d_bar.pack(fill="x", padx=6, pady=6)
        ttk.Button(d_bar, text="Refrescar", bootstyle="success",
                   command=self._refresh).pack(side="left", padx=2)
        ttk.Button(d_bar, text="Iniciar distro", bootstyle="info",
                   command=self._start_selected_distro).pack(side="left", padx=2)
        ttk.Button(d_bar, text="Detener distro", bootstyle="warning",
                   command=self._stop_selected_distro).pack(side="left", padx=2)
        ttk.Button(d_bar, text="Reiniciar distro", bootstyle="info",
                   command=self._restart_selected_distro).pack(side="left", padx=2)
        ttk.Button(d_bar, text="Iniciar todas", bootstyle="info",
                   command=self._start_all_distros).pack(side="left", padx=2)
        ttk.Button(d_bar, text="Apagar todas", bootstyle="danger",
                   command=self._shutdown_all_distros).pack(side="left", padx=2)
        ttk.Button(d_bar, text="Snapshot", bootstyle="secondary",
                   command=self._snapshot_selected).pack(side="left", padx=2)
        ttk.Button(d_bar, text="Metricas", bootstyle="secondary",
                   command=self._show_metrics).pack(side="left", padx=2)
        self.distro_tree = _make_tree(d_tab, ["Distro", "Estado", "IP", "Version"],
                                      [200, 100, 160, 80])

        # -- pestana Publicar ----------------------------------------------------
        self.publish_tab = PublishTab(nb)
        nb.add(self.publish_tab, text="  Publicar en Internet  ")

        # -- pestana Tunnels / VPS -----------------------------------------------
        t_tab = ttk.Frame(nb)
        nb.add(t_tab, text="  Tunnels / VPS  ")

        # Tunnels section
        ttk.Label(t_tab, text="Tunnels SSH", style="Header.TLabel").pack(anchor="w", padx=6, pady=(6, 2))
        tun_bar = ttk.Frame(t_tab)
        tun_bar.pack(fill="x", padx=6, pady=4)
        ttk.Button(tun_bar, text="Refrescar", bootstyle="success",
                   command=self._refresh).pack(side="left", padx=2)
        ttk.Button(tun_bar, text="Nuevo Tunnel...", bootstyle="info",
                   command=self._add_tunnel_dialog).pack(side="left", padx=2)
        ttk.Button(tun_bar, text="Iniciar tunnel", bootstyle="success",
                   command=self._start_selected_tunnel).pack(side="left", padx=2)
        ttk.Button(tun_bar, text="Detener tunnel", bootstyle="warning",
                   command=self._stop_selected_tunnel).pack(side="left", padx=2)
        ttk.Button(tun_bar, text="Eliminar tunnel", bootstyle="danger",
                   command=self._remove_selected_tunnel).pack(side="left", padx=2)
        self.tun_tree = _make_tree(t_tab, ["ID", "Tipo", "VPS", "Local", "Remoto", "Estado", "Trafico"],
                                   [150, 70, 130, 140, 170, 80, 200])

        ttk.Separator(t_tab).pack(fill="x", padx=6, pady=6)

        # VPS section
        ttk.Label(t_tab, text="Servidores VPS", style="Header.TLabel").pack(anchor="w", padx=6, pady=(2, 2))
        vps_bar = ttk.Frame(t_tab)
        vps_bar.pack(fill="x", padx=6, pady=4)
        ttk.Button(vps_bar, text="Nuevo VPS...", bootstyle="info",
                   command=self._add_vps_dialog).pack(side="left", padx=2)
        ttk.Button(vps_bar, text="Editar VPS...", bootstyle="secondary",
                   command=self._edit_vps_selected).pack(side="left", padx=2)
        ttk.Button(vps_bar, text="Eliminar VPS", bootstyle="danger",
                   command=self._remove_vps_selected).pack(side="left", padx=2)
        self.vps_tree = _make_tree(t_tab, ["VPS", "Host", "Usuario", "Puerto", "Auth"],
                                   [150, 220, 130, 80, 120])

        # -- pestana Forwards ----------------------------------------------------
        f_tab = ttk.Frame(nb)
        nb.add(f_tab, text="  Forwards  ")
        fwd_bar = ttk.Frame(f_tab)
        fwd_bar.pack(fill="x", padx=6, pady=6)
        ttk.Button(fwd_bar, text="Refrescar", bootstyle="success",
                   command=self._refresh).pack(side="left", padx=2)
        ttk.Button(fwd_bar, text="Nuevo Forward...", bootstyle="info",
                   command=self._add_forward_dialog).pack(side="left", padx=2)
        ttk.Button(fwd_bar, text="Reaplicar todos", bootstyle="info",
                   command=self._apply_forwards).pack(side="left", padx=2)
        ttk.Button(fwd_bar, text="Eliminar forward", bootstyle="danger",
                   command=self._remove_selected_forward).pack(side="left", padx=2)
        ttk.Button(fwd_bar, text="Limpiar todos", bootstyle="danger",
                   command=self._clear_forwards).pack(side="left", padx=2)
        self.fwd_tree = _make_tree(f_tab, ["ID", "Listen", "Distro", "WSL Port", "Proto", "Estado"],
                                   [160, 90, 160, 90, 70, 100])

        # -- pestana Logs --------------------------------------------------------
        l_tab = ttk.Frame(nb)
        nb.add(l_tab, text="  Logs  ")
        self.log_text = tk.Text(l_tab, font=("Consolas", 9), bg="#17191d", fg="#c9d1d9",
                                state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=6, pady=6)
        ttk.Button(l_tab, text="Refrescar logs", bootstyle="success",
                   command=self._refresh_logs).pack(anchor="w", padx=6, pady=(0, 6))

        # -- pestana Ajustes -----------------------------------------------------
        settings_tab = ttk.Frame(nb)
        nb.add(settings_tab, text="  Ajustes  ")
        self._build_settings_tab(settings_tab)

        # -- barra inferior ------------------------------------------------------
        ttk.Separator(self.root).pack(fill="x")
        bar = ttk.Frame(self.root, padding=(16, 6))
        bar.pack(fill="x", side="bottom")
        self.status_var = tk.StringVar(value="cargando...")
        ttk.Label(bar, textvariable=self.status_var, style="Muted.TLabel").pack(side="left")

    def _build_settings_tab(self, parent) -> None:
        frame = ttk.Frame(parent, padding=12)
        frame.pack(fill="both", expand=True)

        row = 0
        ttk.Label(frame, text="General", style="Header.TLabel").grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(0, 8))
        row += 1

        ttk.Label(frame, text="Tema:").grid(row=row, column=0, sticky="w", pady=3)
        self.theme_var = tk.StringVar(value="darkly")
        ttk.Combobox(frame, textvariable=self.theme_var, values=[
            "darkly", "cosmo", "flatly", "journal", "litera", "lumen",
            "minty", "pulse", "sandstone", "united", "yeti",
        ], width=15, state="readonly").grid(row=row, column=1, sticky="w", padx=6, pady=3)
        row += 1

        ttk.Label(frame, text="Panel web puerto:").grid(row=row, column=0, sticky="w", pady=3)
        self.web_port_var = tk.StringVar(value="8780")
        ttk.Entry(frame, textvariable=self.web_port_var, width=8).grid(
            row=row, column=1, sticky="w", padx=6, pady=3)
        row += 1

        ttk.Label(frame, text="API puerto:").grid(row=row, column=0, sticky="w", pady=3)
        self.api_port_var = tk.StringVar(value="8781")
        ttk.Entry(frame, textvariable=self.api_port_var, width=8).grid(
            row=row, column=1, sticky="w", padx=6, pady=3)
        row += 1

        ttk.Label(frame, text="MCP puerto:").grid(row=row, column=0, sticky="w", pady=3)
        self.mcp_port_var = tk.StringVar(value="8782")
        ttk.Entry(frame, textvariable=self.mcp_port_var, width=8).grid(
            row=row, column=1, sticky="w", padx=6, pady=3)
        row += 1

        ttk.Button(frame, text="Guardar ajustes", bootstyle="success",
                   command=self._save_settings).grid(row=row, column=0, columnspan=2, pady=12)

    def _save_settings(self) -> None:
        try:
            store = core.pf_store()
            store.cfg.ui.web_panel_port = int(self.web_port_var.get())
            store.cfg.api.port = int(self.api_port_var.get())
            store.cfg.mcp.port = int(self.mcp_port_var.get())
            store.save()
            from tkinter import messagebox
            messagebox.showinfo("Ajustes", "Ajustes guardados correctamente")
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Ajustes", f"Error: {e}")

    # -- WSL distro actions ---------------------------------------------------

    def _get_selected_distro(self) -> str | None:
        sel = self.distro_tree.selection()
        if not sel:
            from tkinter import messagebox
            messagebox.showwarning("Distros", "Selecciona una distro primero")
            return None
        return str(self.distro_tree.item(sel[0])["values"][0])

    def _start_selected_distro(self) -> None:
        name = self._get_selected_distro()
        if not name:
            return
        def _work():
            core.start_distro(name)
            self._q.put({"_action": "refresh"})
        threading.Thread(target=_work, daemon=True).start()

    def _stop_selected_distro(self) -> None:
        name = self._get_selected_distro()
        if not name:
            return
        def _work():
            core.stop_distro(name)
            self._q.put({"_action": "refresh"})
        threading.Thread(target=_work, daemon=True).start()

    def _restart_selected_distro(self) -> None:
        name = self._get_selected_distro()
        if not name:
            return
        def _work():
            core.restart_distro(name)
            self._q.put({"_action": "refresh"})
        threading.Thread(target=_work, daemon=True).start()

    def _start_all_distros(self) -> None:
        def _work():
            for d in core.distros():
                if not d.get("running"):
                    core.start_distro(d["name"])
            self._q.put({"_action": "refresh"})
        threading.Thread(target=_work, daemon=True).start()

    def _shutdown_all_distros(self) -> None:
        from tkinter import messagebox
        if messagebox.askyesno("Apagar todas", "Apagar WSL completamente?"):
            def _work():
                core.shutdown_all()
                self._q.put({"_action": "refresh"})
            threading.Thread(target=_work, daemon=True).start()

    def _snapshot_selected(self) -> None:
        name = self._get_selected_distro()
        if not name:
            return
        from tkinter import messagebox
        def _work():
            r = core.snapshot(name)
            if r.get("ok"):
                messagebox.showinfo("Snapshot", f"Snapshot creado:\n{r['path']}")
            else:
                messagebox.showerror("Snapshot", f"Error: {r.get('error')}")
        threading.Thread(target=_work, daemon=True).start()

    def _show_metrics(self) -> None:
        name = self._get_selected_distro()
        if not name:
            return
        from tkinter import messagebox
        m = core.distro_metrics(name)
        if m is None:
            messagebox.showinfo("Metricas", f"La distro '{name}' no esta corriendo")
            return
        msg = (f"Distro: {m['name']}\n"
               f"IP: {m.get('ip', '-')}\n"
               f"RAM: {m.get('ram_used_mb',0)}/{m.get('ram_total_mb',0)} MB ({m.get('ram_percent',0)}%)\n"
               f"CPUs: {m.get('cpus', '?')}\n"
               f"Uptime: {m.get('uptime_s',0)}s")
        messagebox.showinfo("Metricas", msg)

    # -- Tunnel actions -------------------------------------------------------

    def _get_selected_tunnel(self) -> str | None:
        sel = self.tun_tree.selection()
        if not sel:
            from tkinter import messagebox
            messagebox.showwarning("Tunnels", "Selecciona un tunnel primero")
            return None
        return str(self.tun_tree.item(sel[0])["values"][0])

    def _add_tunnel_dialog(self) -> None:
        """Dialogo para agregar tunnel con seleccion facil."""
        vps_list = core.vps_list()
        if not vps_list:
            from tkinter import messagebox
            messagebox.showwarning("Tunnels", "Primero crea un VPS en la seccion Servidores VPS")
            return

        def _validate(data):
            if not data.get("id", "").strip():
                raise ValueError("El ID es obligatorio")
            if not data.get("local_port", 0):
                raise ValueError("El puerto local es obligatorio")
            if not data.get("remote_port", 0):
                raise ValueError("El puerto remoto es obligatorio")

        fields = [
            ("id", "ID del tunnel", "entry"),
            ("vps_id", "VPS destino", "combo"),
            ("local_port", "Puerto local (WSL)", "int"),
            ("remote_port", "Puerto publico (VPS)", "int"),
            ("local_host", "Host local", "entry"),
            ("remote_host", "Host remoto", "entry"),
        ]
        dlg = _FormDialog(self.root, "Nuevo Tunnel SSH", fields, validate=_validate)
        dlg._vars["local_host"].set("127.0.0.1")
        dlg._vars["remote_host"].set("0.0.0.0")
        # Set VPS combo values
        vps_ids = [v["id"] for v in vps_list]
        dlg.set_combo_values("vps_id", vps_ids)

        self.root.wait_window(dlg)
        if not dlg.result:
            return
        data = dlg.result
        r = core.add_tunnel(
            tun_id=data["id"].strip(),
            vps_id=data["vps_id"].strip(),
            local_host=data.get("local_host", "127.0.0.1").strip() or "127.0.0.1",
            local_port=int(data["local_port"]),
            remote_host=data.get("remote_host", "0.0.0.0").strip() or "0.0.0.0",
            remote_port=int(data["remote_port"]),
        )
        from tkinter import messagebox
        if r.get("ok"):
            messagebox.showinfo("Tunnel", f"Tunnel '{data['id']}' creado")
            self._refresh()
        else:
            messagebox.showerror("Tunnel", f"Error: {r.get('error')}")

    def _start_selected_tunnel(self) -> None:
        tid = self._get_selected_tunnel()
        if not tid:
            return
        def _work():
            core.start_tunnel(tid)
            self._q.put({"_action": "refresh"})
        threading.Thread(target=_work, daemon=True).start()

    def _stop_selected_tunnel(self) -> None:
        tid = self._get_selected_tunnel()
        if not tid:
            return
        def _work():
            core.stop_tunnel(tid)
            self._q.put({"_action": "refresh"})
        threading.Thread(target=_work, daemon=True).start()

    def _remove_selected_tunnel(self) -> None:
        tid = self._get_selected_tunnel()
        if not tid:
            return
        from tkinter import messagebox
        if messagebox.askyesno("Eliminar tunnel", f"Eliminar tunnel '{tid}'?"):
            r = core.remove_tunnel(tid)
            if r.get("ok"):
                self._refresh()
            else:
                messagebox.showerror("Tunnel", f"Error: {r.get('error')}")

    # -- VPS actions ----------------------------------------------------------

    def _get_selected_vps(self) -> str | None:
        sel = self.vps_tree.selection()
        if not sel:
            from tkinter import messagebox
            messagebox.showwarning("VPS", "Selecciona un VPS primero")
            return None
        return str(self.vps_tree.item(sel[0])["values"][0])

    def _add_vps_dialog(self) -> None:
        """Dialogo para agregar VPS con todos los campos."""
        def _validate(data):
            if not data.get("id", "").strip():
                raise ValueError("El ID es obligatorio")
            if not data.get("host", "").strip():
                raise ValueError("El host es obligatorio")

        fields = [
            ("id", "ID del VPS", "entry"),
            ("host", "Host / IP", "entry"),
            ("user", "Usuario SSH", "entry"),
            ("port", "Puerto SSH", "int"),
            ("identity_file", "Clave SSH (key file)", "file"),
            ("password", "Contrasena SSH", "password"),
        ]
        dlg = _FormDialog(self.root, "Nuevo VPS", fields, validate=_validate, size=(450, 380))
        dlg._vars["user"].set("debian")
        dlg._vars["port"].set(22)

        self.root.wait_window(dlg)
        if not dlg.result:
            return
        data = dlg.result
        r = core.add_vps(
            vps_id=data["id"].strip(),
            host=data["host"].strip(),
            user=data.get("user", "").strip(),
            port=int(data.get("port", 22) or 22),
            identity_file=data.get("identity_file", "").strip(),
            password=data.get("password", "").strip(),
        )
        from tkinter import messagebox
        if r.get("ok"):
            messagebox.showinfo("VPS", f"VPS '{data['id']}' creado")
            self._refresh()
        else:
            messagebox.showerror("VPS", f"Error: {r.get('error')}")

    def _edit_vps_selected(self) -> None:
        """Editar VPS existente."""
        vps_id = self._get_selected_vps()
        if not vps_id:
            return
        vps = next((v for v in core.vps_list() if v.get("id") == vps_id), None)
        if not vps:
            from tkinter import messagebox
            messagebox.showerror("VPS", f"VPS '{vps_id}' no encontrado")
            return

        def _validate(data):
            if not data.get("host", "").strip():
                raise ValueError("El host es obligatorio")

        fields = [
            ("host", "Host / IP", "entry"),
            ("user", "Usuario SSH", "entry"),
            ("port", "Puerto SSH", "int"),
            ("identity_file", "Clave SSH (key file)", "file"),
            ("password", "Contrasena SSH", "password"),
        ]
        dlg = _FormDialog(self.root, f"Editar VPS: {vps_id}", fields, validate=_validate, size=(450, 350))
        dlg._vars["host"].set(vps.get("host", ""))
        dlg._vars["user"].set(vps.get("user", ""))
        dlg._vars["port"].set(vps.get("port", 22))
        dlg._vars["identity_file"].set(vps.get("identity_file", ""))
        dlg._vars["password"].set(vps.get("password", ""))

        self.root.wait_window(dlg)
        if not dlg.result:
            return
        data = dlg.result
        # Remove old and add new
        core.remove_vps(vps_id)
        r = core.add_vps(
            vps_id=vps_id,
            host=data["host"].strip(),
            user=data.get("user", "").strip(),
            port=int(data.get("port", 22) or 22),
            identity_file=data.get("identity_file", "").strip(),
            password=data.get("password", "").strip(),
        )
        from tkinter import messagebox
        if r.get("ok"):
            messagebox.showinfo("VPS", f"VPS '{vps_id}' actualizado")
            self._refresh()
        else:
            messagebox.showerror("VPS", f"Error: {r.get('error')}")

    def _remove_vps_selected(self) -> None:
        vps_id = self._get_selected_vps()
        if not vps_id:
            return
        from tkinter import messagebox
        if messagebox.askyesno("Eliminar VPS", f"Eliminar VPS '{vps_id}'?"):
            r = core.remove_vps(vps_id)
            if r.get("ok"):
                self._refresh()
            else:
                messagebox.showerror("VPS", f"Error: {r.get('error')}")

    # -- Forward actions ------------------------------------------------------

    def _get_selected_forward(self) -> str | None:
        sel = self.fwd_tree.selection()
        if not sel:
            from tkinter import messagebox
            messagebox.showwarning("Forwards", "Selecciona un forward primero")
            return None
        return str(self.fwd_tree.item(sel[0])["values"][0])

    def _add_forward_dialog(self) -> None:
        """Dialogo para agregar forward."""
        distros = core.distros()
        distro_names = [d["name"] for d in distros]

        def _validate(data):
            if not data.get("id", "").strip():
                raise ValueError("El ID es obligatorio")
            if not data.get("listen_port", 0):
                raise ValueError("El puerto listen es obligatorio")
            if not data.get("wsl_port", 0):
                raise ValueError("El puerto WSL es obligatorio")
            if not data.get("distro", "").strip():
                raise ValueError("La distro es obligatoria")

        fields = [
            ("id", "ID del forward", "entry"),
            ("listen_port", "Puerto listen (Windows)", "int"),
            ("distro", "Distro WSL", "combo"),
            ("wsl_port", "Puerto WSL", "int"),
            ("protocol", "Protocolo", "combo"),
        ]
        dlg = _FormDialog(self.root, "Nuevo Forward", fields, validate=_validate, size=(420, 350))
        dlg.set_combo_values("distro", distro_names)
        dlg.set_combo_values("protocol", ["tcp", "udp"])

        self.root.wait_window(dlg)
        if not dlg.result:
            return
        data = dlg.result
        r = core.add_forward(
            fwd_id=data["id"].strip(),
            listen_port=int(data["listen_port"]),
            wsl_distro=data["distro"].strip(),
            wsl_port=int(data["wsl_port"]),
            protocol=data.get("protocol", "tcp") or "tcp",
        )
        from tkinter import messagebox
        if r.get("ok"):
            messagebox.showinfo("Forward", f"Forward '{data['id']}' creado")
            self._refresh()
        else:
            messagebox.showerror("Forward", f"Error: {r.get('error')}")

    def _remove_selected_forward(self) -> None:
        fwd_id = self._get_selected_forward()
        if not fwd_id:
            return
        from tkinter import messagebox
        if messagebox.askyesno("Eliminar forward", f"Eliminar forward '{fwd_id}'?"):
            r = core.remove_forward(fwd_id)
            if r.get("ok"):
                self._refresh()
            else:
                messagebox.showerror("Forward", f"Error: {r.get('error')}")

    def _apply_forwards(self) -> None:
        def _work():
            core.apply_forwards()
            self._q.put({"_action": "refresh"})
        threading.Thread(target=_work, daemon=True).start()

    def _clear_forwards(self) -> None:
        from tkinter import messagebox
        if messagebox.askyesno("Limpiar forwards", "Eliminar TODOS los forwards de netsh?"):
            def _work():
                core.clear_forwards()
                self._q.put({"_action": "refresh"})
            threading.Thread(target=_work, daemon=True).start()

    # -- Logs -----------------------------------------------------------------

    def _refresh_logs(self) -> None:
        try:
            from wsl_port.vendor.port_forwarder.utils.path import logs_dir
            log_file = logs_dir() / "port-forwarder.log"
            if log_file.exists():
                text = log_file.read_text(encoding="utf-8", errors="replace")
                lines = text.splitlines()[-200:]
                self.log_text.config(state="normal")
                self.log_text.delete("1.0", "end")
                self.log_text.insert("1.0", "\n".join(lines))
                self.log_text.config(state="disabled")
        except Exception:
            pass

    # -- datos / refresco ---------------------------------------------------------

    def _work(self):
        try:
            return core.status()
        except Exception as e:
            return {"error": str(e)}

    def _refresh(self) -> None:
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self) -> None:
        try:
            self._q.put(self._work())
        except Exception as e:
            self._q.put({"error": str(e)})

    def _poll(self) -> None:
        try:
            self._apply()
        except Exception:
            pass
        self.root.after(200, self._poll)

    def _schedule_refresh(self) -> None:
        self._refresh()
        self.root.after(15000, self._schedule_refresh)

    def _apply(self) -> None:
        while True:
            try:
                st = self._q.get_nowait()
            except queue.Empty:
                return
            if "_action" in st:
                if st["_action"] == "refresh":
                    self._refresh()
                continue
            if "error" in st:
                self.status_var.set(f"error: {st['error']}")
                continue
            up = sum(1 for d in st["distros"] if d.get("running"))
            tun_ok = sum(1 for t in st["tunnels"] if t.get("state") == "running")
            self.header_status.configure(
                text=f"distros {up}/{len(st['distros'])} · tuneles {tun_ok}/{len(st['tunnels'])}"
                     + (" · MANTENIMIENTO" if st["maintenance"] else ""))

            self._fill(self.distro_tree, [
                [d.get("name", "?"), d.get("state", "?"), d.get("ip") or "-",
                 str(d.get("version", "?"))]
                for d in st["distros"]
            ])
            self._fill(self.tun_tree, [
                [t.get("id", "?"), t.get("type", "ssh"), t.get("vps_id", "?"),
                 t.get("local", "?"), ", ".join(t.get("remote") or []),
                 t.get("state", "?"), self._fmt_traffic(t.get("traffic"))]
                for t in st["tunnels"]
            ])
            self._fill(self.vps_tree, [
                [v.get("id", "?"), v.get("host", "?"), v.get("user", "?"),
                 str(v.get("port", 22)),
                 "key" if v.get("identity_file") else ("pass" if v.get("password") else "-")]
                for v in st["vps"]
            ])
            self._fill(self.fwd_tree, [
                [f.get("id", "?"), str(f.get("listen_port", "?")), f.get("wsl_distro", "?"),
                 str(f.get("wsl_port", "?")), f.get("protocol", "?"), f.get("state", "?")]
                for f in st["forwards"]
            ])
            self.publish_tab.refresh_options()
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            self.status_var.set(f"actualizado {ts} · supervisor {'ON' if st['supervisor_running'] else 'OFF'}")

    def _fill(self, tree, rows) -> None:
        tree.delete(*tree.get_children())
        for r in rows:
            tree.insert("", "end", values=r)

    def _fmt_traffic(self, tf) -> str:
        if not tf:
            return "-"
        return (f"rx {_fmt_bytes(tf.get('rx_bytes',0))} tx {_fmt_bytes(tf.get('tx_bytes',0))}"
                f" {_fmt_bytes(tf.get('rx_rate_bps',0))}/s {_fmt_bytes(tf.get('tx_rate_bps',0))}/s")


def run() -> None:
    if not _single_instance():
        return
    win = MainWindow()
    win.root.mainloop()


_MUTEX = None


def _single_instance() -> bool:
    """Evita abrir dos ventanas de wsl-port a la vez."""
    import ctypes

    global _MUTEX
    _MUTEX = ctypes.windll.kernel32.CreateMutexW(None, False, "wsl-port-unicidad")
    return ctypes.windll.kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS
