"""Pestana 'Publicar en Internet': asistente distro WSL -> tunel al VPS."""
from __future__ import annotations

import tkinter as tk
import webbrowser
from tkinter import messagebox

import ttkbootstrap as ttk

from .. import core


class PublishTab(ttk.Frame):
    def __init__(self, master) -> None:
        super().__init__(master)
        self._build()

    def _build(self) -> None:
        form = ttk.Frame(self, padding=12)
        form.pack(fill="x")

        ttk.Label(form, text="Publicar en Internet", style="Header.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))
        ttk.Label(form, text=(
            "Publica un servicio que corre dentro de una distro WSL usando el "
            "tunel SSH de tu VPS. Ej.: servicio web en el puerto 9000 de "
            "Debian -> http://TU-VPS:18097"),
            style="Muted.TLabel", wraplength=640).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 10))

        self.distro_var = tk.StringVar()
        ttk.Label(form, text="Distro WSL:").grid(row=2, column=0, sticky="w", pady=3)
        self.distro_cb = ttk.Combobox(form, textvariable=self.distro_var, width=20, state="readonly")
        self.distro_cb.grid(row=2, column=1, sticky="w", padx=6, pady=3)

        self.wsl_port_var = tk.StringVar(value="9000")
        ttk.Label(form, text="Puerto del servicio (en WSL):").grid(row=3, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=self.wsl_port_var, width=10).grid(row=3, column=1, sticky="w", padx=6, pady=3)

        self.vps_var = tk.StringVar()
        ttk.Label(form, text="VPS:").grid(row=4, column=0, sticky="w", pady=3)
        self.vps_cb = ttk.Combobox(form, textvariable=self.vps_var, width=20, state="readonly")
        self.vps_cb.grid(row=4, column=1, sticky="w", padx=6, pady=3)

        self.public_port_var = tk.StringVar(value="18097")
        ttk.Label(form, text="Puerto publico (en el VPS):").grid(row=5, column=0, sticky="w", pady=3)
        ttk.Entry(form, textvariable=self.public_port_var, width=10).grid(row=5, column=1, sticky="w", padx=6, pady=3)

        btns = ttk.Frame(form)
        btns.grid(row=6, column=0, columnspan=3, sticky="w", pady=8)
        ttk.Button(btns, text="Publicar", bootstyle="success", command=self._publish).pack(side="left", padx=2)
        ttk.Button(btns, text="Detener publicacion", bootstyle="danger", command=self._unpublish).pack(side="left", padx=2)
        ttk.Button(btns, text="Abrir en navegador", bootstyle="info", command=self._open).pack(side="left", padx=2)

        self.result_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.result_var, style="Muted.TLabel", wraplength=640,
                  justify="left").pack(anchor="w", padx=12)

    def refresh_options(self) -> None:
        """Actualizar listas de distros y VPS."""
        try:
            names = [d.get("name") for d in core.distros()]
            self.distro_cb["values"] = names
            if not self.distro_var.get() and names:
                self.distro_var.set(names[0])
        except Exception:
            pass
        try:
            vps = [v.get("id") for v in core.vps_list()]
            self.vps_cb["values"] = vps
            if not self.vps_var.get() and vps:
                self.vps_var.set(vps[0])
        except Exception:
            pass

    def _values(self) -> tuple | None:
        try:
            wsl_port = int(self.wsl_port_var.get())
            public_port = int(self.public_port_var.get())
        except ValueError:
            messagebox.showerror("wsl-port", "Puertos invalidos")
            return None
        return self.distro_var.get().strip(), wsl_port, self.vps_var.get().strip(), public_port

    def _publish(self) -> None:
        v = self._values()
        if not v:
            return
        distro, wsl_port, vps_id, public_port = v
        try:
            r = core.publish(distro, wsl_port, vps_id, public_port)
        except (ValueError, RuntimeError) as e:
            messagebox.showerror("Publicar", str(e))
            return
        self.result_var.set(
            f"Publicado: {r['public_url']}\n"
            f"Tunnel '{r['tunnel_id']}' corriendo (local {r['local']} -> VPS {r['vps_id']})."
        )
        messagebox.showinfo("Publicar", f"Servicio publicado:\n{r['public_url']}")
        self.event_generate("<<Published>>")

    def _unpublish(self) -> None:
        v = self._values()
        if not v:
            return
        distro, wsl_port, *_ = v
        tid = core.tunnel_id_for(distro, wsl_port)
        if messagebox.askyesno("Detener publicacion", f"Eliminar el tunnel '{tid}'?"):
            if core.unpublish(tid):
                self.result_var.set(f"Tunnel '{tid}' eliminado.")
            else:
                messagebox.showerror("Detener publicacion", f"No se pudo eliminar '{tid}'")

    def _open(self) -> None:
        v = self._values()
        if not v:
            return
        distro, wsl_port, vps_id, public_port = v
        vps = next((x for x in core.vps_list() if x.get("id") == vps_id), {})
        webbrowser.open(f"http://{vps.get('host', '127.0.0.1')}:{public_port}")
