"""Ventana integrada de wsl-port: distros WSL + tunnels/forwards + publicar."""
from __future__ import annotations

import datetime
import queue
import threading
import tkinter as tk
import webbrowser
from tkinter import ttk as _ttk

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


class MainWindow:
    def __init__(self) -> None:
        self.root = ttk.Window(themename="darkly", title="wsl-port — WSL + Port Forwarding")
        self.root.geometry("1100x750")
        self.root.minsize(900, 560)
        self._q: queue.Queue = queue.Queue()
        self._build()
        self._refresh()
        self.root.after(200, self._poll)
        self.root.after(15000, self._schedule_refresh)
        # Ensure window is visible and focused
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
        nb.add(d_tab, text="Distros WSL")
        d_bar = ttk.Frame(d_tab)
        d_bar.pack(fill="x", padx=6, pady=6)
        ttk.Button(d_bar, text="Refrescar", bootstyle="success",
                   command=self._refresh).pack(side="left", padx=2)
        ttk.Button(d_bar, text="Iniciar todas", bootstyle="info",
                   command=self._start_all_distros).pack(side="left", padx=2)
        ttk.Button(d_bar, text="Apagar todas", bootstyle="danger",
                   command=self._shutdown_all_distros).pack(side="left", padx=2)
        self.distro_tree = _make_tree(d_tab, ["Distro", "Estado", "IP", "Version"],
                                      [180, 100, 160, 80])

        # -- pestana Publicar ----------------------------------------------------
        self.publish_tab = PublishTab(nb)
        nb.add(self.publish_tab, text="Publicar en Internet")

        # -- pestana Tunnels / VPS -----------------------------------------------
        t_tab = ttk.Frame(nb)
        nb.add(t_tab, text="Tunnels / VPS")
        tun_bar = ttk.Frame(t_tab)
        tun_bar.pack(fill="x", padx=6, pady=6)
        ttk.Button(tun_bar, text="Refrescar", bootstyle="success",
                   command=self._refresh).pack(side="left", padx=2)
        self.tun_tree = _make_tree(t_tab, ["ID", "Tipo", "VPS", "Local", "Remoto", "Estado", "Trafico"],
                                   [140, 70, 120, 130, 160, 80, 200])
        ttk.Separator(t_tab).pack(fill="x", padx=6, pady=4)
        ttk.Label(t_tab, text="Servidores VPS", style="Header.TLabel").pack(anchor="w", padx=6)
        vps_bar = ttk.Frame(t_tab)
        vps_bar.pack(fill="x", padx=6, pady=4)
        ttk.Button(vps_bar, text="Nuevo VPS...", bootstyle="info",
                   command=self._add_vps_dialog).pack(side="left", padx=2)
        ttk.Button(vps_bar, text="Eliminar VPS", bootstyle="danger",
                   command=self._remove_vps_selected).pack(side="left", padx=2)
        self.vps_tree = _make_tree(t_tab, ["VPS", "Host", "Usuario", "Puerto"],
                                   [150, 220, 130, 80])

        # -- pestana Forwards ----------------------------------------------------
        f_tab = ttk.Frame(nb)
        nb.add(f_tab, text="Forwards")
        fwd_bar = ttk.Frame(f_tab)
        fwd_bar.pack(fill="x", padx=6, pady=6)
        ttk.Button(fwd_bar, text="Refrescar", bootstyle="success",
                   command=self._refresh).pack(side="left", padx=2)
        ttk.Button(fwd_bar, text="Reaplicar todos", bootstyle="info",
                   command=self._apply_forwards).pack(side="left", padx=2)
        ttk.Button(fwd_bar, text="Limpiar todos", bootstyle="danger",
                   command=self._clear_forwards).pack(side="left", padx=2)
        self.fwd_tree = _make_tree(f_tab, ["ID", "Listen", "Distro", "WSL Port", "Proto", "Estado"],
                                   [150, 90, 150, 90, 70, 100])

        # -- pestana Logs --------------------------------------------------------
        l_tab = ttk.Frame(nb)
        nb.add(l_tab, text="Logs")
        self.log_text = tk.Text(l_tab, font=("Consolas", 9), bg="#17191d", fg="#c9d1d9",
                                state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=6, pady=6)
        ttk.Button(l_tab, text="Refrescar logs", bootstyle="success",
                   command=self._refresh_logs).pack(anchor="w", padx=6, pady=(0, 6))

        # -- pestana Ajustes -----------------------------------------------------
        settings_tab = ttk.Frame(nb)
        nb.add(settings_tab, text="Ajustes")
        self._build_settings_tab(settings_tab)

        # -- barra inferior ------------------------------------------------------
        ttk.Separator(self.root).pack(fill="x")
        bar = ttk.Frame(self.root, padding=(16, 6))
        bar.pack(fill="x", side="bottom")
        self.status_var = tk.StringVar(value="cargando...")
        ttk.Label(bar, textvariable=self.status_var, style="Muted.TLabel").pack(side="left")

    def _build_settings_tab(self, parent) -> None:
        """Pestana de ajustes."""
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
        """Guardar ajustes desde la pestana."""
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

    # -- acciones --------------------------------------------------------------

    def _start_all_distros(self) -> None:
        def _work():
            for d in core.distros():
                if not d.get("running"):
                    core.start_distro(d["name"])
            self._q.put({"_action": "refresh"})
        threading.Thread(target=_work, daemon=True).start()

    def _shutdown_all_distros(self) -> None:
        def _work():
            core.shutdown_all()
            self._q.put({"_action": "refresh"})
        threading.Thread(target=_work, daemon=True).start()

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

    def _add_vps_dialog(self) -> None:
        """Dialogo para agregar VPS."""
        from tkinter import simpledialog, messagebox
        vps_id = simpledialog.askstring("Nuevo VPS", "ID del VPS:")
        if not vps_id:
            return
        host = simpledialog.askstring("Nuevo VPS", "Host del VPS:")
        if not host:
            return
        user = simpledialog.askstring("Nuevo VPS", "Usuario SSH:", initialvalue="debian")
        port = simpledialog.askinteger("Nuevo VPS", "Puerto SSH:", initialvalue=22)
        r = core.add_vps(vps_id, host, user or "", port or 22)
        if r.get("ok"):
            messagebox.showinfo("VPS", f"VPS '{vps_id}' creado")
            self._refresh()
        else:
            messagebox.showerror("VPS", f"Error: {r.get('error')}")

    def _remove_vps_selected(self) -> None:
        from tkinter import messagebox
        sel = self.vps_tree.selection()
        if not sel:
            messagebox.showwarning("VPS", "Selecciona un VPS primero")
            return
        vps_id = self.vps_tree.item(sel[0])["values"][0]
        if messagebox.askyesno("Eliminar VPS", f"Eliminar VPS '{vps_id}'?"):
            r = core.remove_vps(str(vps_id))
            if r.get("ok"):
                self._refresh()
            else:
                messagebox.showerror("VPS", f"Error: {r.get('error')}")

    def _refresh_logs(self) -> None:
        """Cargar ultimas lineas del log."""
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
                 str(v.get("port", 22))]
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
