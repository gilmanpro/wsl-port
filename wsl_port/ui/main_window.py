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
    return f"{n:.1f} {u}"


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
        self.root.geometry("1060x720")
        self.root.minsize(900, 560)
        self._q: queue.Queue = queue.Queue()
        self._build()
        self._refresh()
        self.root.after(200, self._poll)
        self.root.after(15000, self._schedule_refresh)

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
                   command=lambda: self._wsl(["start", "--all"])).pack(side="left", padx=2)
        ttk.Button(d_bar, text="Apagar todas", bootstyle="danger",
                   command=lambda: self._wsl(["stop-all"])).pack(side="left", padx=2)
        self.distro_tree = _make_tree(d_tab, ["Distro", "Estado", "IP", "RAM %"], [160, 90, 150, 90])

        # -- pestana Publicar ----------------------------------------------------
        self.publish_tab = PublishTab(nb)
        nb.add(self.publish_tab, text="Publicar en Internet")

        # -- pestana Tunnels / VPS -----------------------------------------------
        t_tab = ttk.Frame(nb)
        nb.add(t_tab, text="Tunnels / VPS")
        self.tun_tree = _make_tree(t_tab, ["ID", "VPS", "Local", "Remoto", "Estado", "Tráfico"],
                                   [140, 110, 130, 160, 90, 190])
        self.vps_tree = _make_tree(t_tab, ["VPS", "Host", "Usuario", "Puerto"], [140, 200, 120, 80])

        # -- pestana Forwards ----------------------------------------------------
        f_tab = ttk.Frame(nb)
        nb.add(f_tab, text="Forwards")
        self.fwd_tree = _make_tree(f_tab, ["ID", "Listen", "Distro", "WSL Port", "IP", "Estado"],
                                   [140, 90, 140, 90, 130, 90])

        # -- barra inferior ------------------------------------------------------
        ttk.Separator(self.root).pack(fill="x")
        bar = ttk.Frame(self.root, padding=(16, 6))
        bar.pack(fill="x", side="bottom")
        self.status_var = tk.StringVar(value="cargando...")
        ttk.Label(bar, textvariable=self.status_var, style="Muted.TLabel").pack(side="left")
        ttk.Button(bar, text="Panel web WSL (8790)", bootstyle="secondary",
                   command=lambda: webbrowser.open("http://127.0.0.1:8790")).pack(side="right", padx=2)
        ttk.Button(bar, text="Panel web PF (8794)", bootstyle="secondary",
                   command=lambda: webbrowser.open("http://127.0.0.1:8794")).pack(side="right", padx=2)

    # -- datos / refresco ---------------------------------------------------------

    def _wsl(self, args: list[str]) -> None:
        core.run_wsl(args)
        self._refresh()

    def _work(self):
        try:
            return core.status()
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}

    def _refresh(self) -> None:
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self) -> None:
        # El hilo de fondo SOLO publica en la cola; el hilo principal de
        # tkinter consume (_poll -> _apply), sin tocar widgets desde aqui.
        try:
            self._q.put(self._work())
        except Exception as e:  # noqa: BLE001
            self._q.put({"error": str(e)})

    def _poll(self) -> None:
        try:
            self._apply()
        except Exception:  # noqa: BLE001 - nunca romper el loop de la UI
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
            if "error" in st:
                self.status_var.set(f"error: {st['error']}")
                continue
            up = sum(1 for d in st["distros"] if d.get("running"))
            tun_ok = sum(1 for t in st["tunnels"] if t.get("state") == "running")
            self.header_status.configure(
                text=f"distros {up}/{len(st['distros'])} · túneles {tun_ok}/{len(st['tunnels'])}"
                     + (" · MANTENIMIENTO" if st["maintenance"] else ""))

            self._fill(self.distro_tree, [
                [d.get("name", "?"), d.get("state", "?"), d.get("ip") or "-",
                 f"{d.get('ram_percent') or '-'}"]
                for d in st["distros"]
            ])
            self._fill(self.tun_tree, [
                [t.get("id", "?"), t.get("vps_id", "?"), t.get("local", "?"),
                 ", ".join(t.get("remote") or []), t.get("state", "?"),
                 self._fmt_traffic(t.get("traffic"))]
                for t in st["tunnels"]
            ])
            self._fill(self.vps_tree, [
                [v.get("id", "?"), v.get("host", "?"), v.get("user", "?"),
                 str(v.get("port", 22))]
                for v in st["vps"]
            ])
            self._fill(self.fwd_tree, [
                [f.get("id", "?"), str(f.get("listen_port", "?")), f.get("wsl_distro", "?"),
                 str(f.get("wsl_port", "?")), f.get("ip") or "-", f.get("state", "?")]
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
        return (f"rx {_fmt_bytes(tf['rx_bytes'])} tx {_fmt_bytes(tf['tx_bytes'])}"
                f" ↓{_fmt_bytes(tf['rx_rate_bps'])}/s ↑{_fmt_bytes(tf['tx_rate_bps'])}/s")


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