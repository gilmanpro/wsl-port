"""ForwardingService: gestiona port-forwards (netsh) y tunnels (ssh).

Capa operativa compartida por GUI, API, MCP y panel web.
Cada forward/tunnel tiene un estado runtime que se actualiza con auto-refresh.
"""
from __future__ import annotations

import logging
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from src.core.config import AppConfig, ConfigStore, ForwardItem, TunnelCfg

log = logging.getLogger("wslmanager.forwarding")


# --------------------------------------------------------------------------
# Runtime state
# --------------------------------------------------------------------------

@dataclass
class ForwardState:
    """Estado runtime de un forward."""
    name: str
    local_port: int
    wsl_port: int
    wsl_ip: str
    enabled: bool
    active: bool = False
    last_error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "local_port": self.local_port,
            "wsl_port": self.wsl_port,
            "wsl_ip": self.wsl_ip,
            "enabled": self.enabled,
            "active": self.active,
            "last_error": self.last_error,
        }


@dataclass
class TunnelState:
    """Estado runtime de un tunnel."""
    name: str
    remote_host: str
    remote_port: int
    local_port: int
    ssh_user: str
    ssh_host: str
    auto_reconnect: bool
    enabled: bool
    active: bool = False
    pid: int | None = None
    last_error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "remote_host": self.remote_host,
            "remote_port": self.remote_port,
            "local_port": self.local_port,
            "ssh_user": self.ssh_user,
            "ssh_host": self.ssh_host,
            "auto_reconnect": self.auto_reconnect,
            "enabled": self.enabled,
            "active": self.active,
            "pid": self.pid,
            "last_error": self.last_error,
        }


# --------------------------------------------------------------------------
# Service
# --------------------------------------------------------------------------

class ForwardingService:
    """Gestiona forwards (netsh portproxy) y tunnels (ssh -L)."""

    def __init__(self, store: ConfigStore, config: AppConfig) -> None:
        self.store = store
        self.config = config
        self._forward_states: dict[str, ForwardState] = {}
        self._tunnel_states: dict[str, TunnelCfg] = {}
        self._tunnel_procs: dict[str, subprocess.Popen] = {}
        self._lock = threading.Lock()
        self._refresh_interval = 5
        self._refreshing = False

    # -- config sync --------------------------------------------------------

    def _sync_forwards(self) -> None:
        """Sincroniza estados desde config."""
        for fwd in self.config.forwarding.forwards:
            if fwd.name not in self._forward_states:
                self._forward_states[fwd.name] = ForwardState(
                    name=fwd.name,
                    local_port=fwd.local_port,
                    wsl_port=fwd.wsl_port,
                    wsl_ip=fwd.wsl_ip,
                    enabled=fwd.enabled,
                )
            else:
                st = self._forward_states[fwd.name]
                st.local_port = fwd.local_port
                st.wsl_port = fwd.wsl_port
                st.wsl_ip = fwd.wsl_ip
                st.enabled = fwd.enabled

    def _sync_tunnels(self) -> None:
        """Sincroniza estados desde config."""
        for tun in self.config.forwarding.tunnels:
            if tun.name not in self._tunnel_states:
                self._tunnel_states[tun.name] = tun

    # -- forwards ----------------------------------------------------------

    def list_forwards(self) -> list[dict[str, Any]]:
        with self._lock:
            self._sync_forwards()
            return [s.to_dict() for s in self._forward_states.values()]

    def add_forward(self, fwd: ForwardItem) -> dict[str, Any]:
        """Agrega un forward a la config y lo activa."""
        with self._lock:
            # Check duplicate
            for existing in self.config.forwarding.forwards:
                if existing.name == fwd.name:
                    return {"ok": False, "error": f"forward '{fwd.name}' ya existe"}
            self.config.forwarding.forwards.append(fwd)
            self.store.save(self.config)
            self._sync_forwards()
            if fwd.enabled:
                return self._apply_forward(fwd)
            return {"ok": True, "message": f"forward '{fwd.name}' agregado"}

    def remove_forward(self, name: str) -> dict[str, Any]:
        """Elimina un forward de la config y lo desactiva."""
        with self._lock:
            found = None
            for f in self.config.forwarding.forwards:
                if f.name == name:
                    found = f
                    break
            if not found:
                return {"ok": False, "error": f"forward '{name}' no existe"}
            # Remove netsh rule
            self._remove_netsh_rule(found.local_port)
            self.config.forwarding.forwards = [
                f for f in self.config.forwarding.forwards if f.name != name
            ]
            self.store.save(self.config)
            self._forward_states.pop(name, None)
            return {"ok": True, "message": f"forward '{name}' eliminado"}

    def start_forward(self, name: str) -> dict[str, Any]:
        """Activa un forward (aplica regla netsh)."""
        with self._lock:
            fwd = self._find_forward(name)
            if not fwd:
                return {"ok": False, "error": f"forward '{name}' no existe"}
            return self._apply_forward(fwd)

    def stop_forward(self, name: str) -> dict[str, Any]:
        """Desactiva un forward (elimina regla netsh)."""
        with self._lock:
            fwd = self._find_forward(name)
            if not fwd:
                return {"ok": False, "error": f"forward '{name}' no existe"}
            self._remove_netsh_rule(fwd.local_port)
            if name in self._forward_states:
                self._forward_states[name].active = False
                self._forward_states[name].last_error = ""
            return {"ok": True, "message": f"forward '{name}' detenido"}

    def _find_forward(self, name: str) -> ForwardItem | None:
        for f in self.config.forwarding.forwards:
            if f.name == name:
                return f
        return None

    def _apply_forward(self, fwd: ForwardItem) -> dict[str, Any]:
        """Aplica una regla netsh portproxy para un forward."""
        try:
            # Remove existing rule first
            self._remove_netsh_rule(fwd.local_port)

            cmd = [
                "netsh", "interface", "portproxy", "add", "v4tov4",
                f"listenport={fwd.local_port}",
                f"listenaddress=0.0.0.0",
                f"connectport={fwd.wsl_port}",
                f"connectaddress={fwd.wsl_ip}",
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=15
            )
            if result.returncode != 0:
                err = result.stderr.strip() or result.stdout.strip()
                if name := fwd.name:
                    if name in self._forward_states:
                        self._forward_states[name].last_error = err
                return {"ok": False, "error": err or "netsh falló"}

            if fwd.name in self._forward_states:
                self._forward_states[fwd.name].active = True
                self._forward_states[fwd.name].last_error = ""
            return {"ok": True, "message": f"forward '{fwd.name}' activado"}
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "timeout aplicando forward"}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}

    def _remove_netsh_rule(self, port: int) -> None:
        """Elimina una regla netsh portproxy."""
        try:
            subprocess.run(
                [
                    "netsh", "interface", "portproxy", "delete", "v4tov4",
                    f"listenport={port}", f"listenaddress=0.0.0.0",
                ],
                capture_output=True, text=True, timeout=10,
            )
        except Exception:  # noqa: BLE001
            pass

    # -- tunnels -----------------------------------------------------------

    def list_tunnels(self) -> list[dict[str, Any]]:
        with self._lock:
            self._sync_tunnels()
            result = []
            for name, tun in self._tunnel_states.items():
                active = name in self._tunnel_procs and self._tunnel_procs[name].poll() is None
                result.append({
                    "name": name,
                    "remote_host": tun.remote_host,
                    "remote_port": tun.remote_port,
                    "local_port": tun.local_port,
                    "ssh_user": tun.ssh_user,
                    "ssh_host": tun.ssh_host,
                    "auto_reconnect": tun.auto_reconnect,
                    "enabled": tun.enabled,
                    "active": active,
                })
            return result

    def add_tunnel(self, tun: TunnelCfg) -> dict[str, Any]:
        """Agrega un tunnel a la config."""
        with self._lock:
            for existing in self.config.forwarding.tunnels:
                if existing.name == tun.name:
                    return {"ok": False, "error": f"tunnel '{tun.name}' ya existe"}
            self.config.forwarding.tunnels.append(tun)
            self.store.save(self.config)
            self._sync_tunnels()
            return {"ok": True, "message": f"tunnel '{tun.name}' agregado"}

    def remove_tunnel(self, name: str) -> dict[str, Any]:
        """Elimina un tunnel de la config y lo detiene."""
        with self._lock:
            self._stop_tunnel_process(name)
            self.config.forwarding.tunnels = [
                t for t in self.config.forwarding.tunnels if t.name != name
            ]
            self.store.save(self.config)
            self._tunnel_states.pop(name, None)
            return {"ok": True, "message": f"tunnel '{name}' eliminado"}

    def start_tunnel(self, name: str) -> dict[str, Any]:
        """Inicia un tunnel SSH."""
        with self._lock:
            tun = self._find_tunnel(name)
            if not tun:
                return {"ok": False, "error": f"tunnel '{name}' no existe"}
            if name in self._tunnel_procs:
                proc = self._tunnel_procs[name]
                if proc.poll() is None:
                    return {"ok": True, "message": f"tunnel '{name}' ya activo"}

            ssh_host = tun.ssh_host or tun.remote_host
            ssh_user = tun.ssh_user or "root"
            target = f"{ssh_user}@{ssh_host}"

            cmd = [
                "ssh", "-N", "-L",
                f"{tun.local_port}:{tun.remote_host}:{tun.remote_port}",
                target,
            ]
            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self._tunnel_procs[name] = proc
                return {"ok": True, "message": f"tunnel '{name}' iniciado (pid={proc.pid})"}
            except FileNotFoundError:
                return {"ok": False, "error": "ssh.exe no encontrado en PATH"}
            except Exception as e:  # noqa: BLE001
                return {"ok": False, "error": str(e)}

    def stop_tunnel(self, name: str) -> dict[str, Any]:
        """Detiene un tunnel SSH."""
        with self._lock:
            self._stop_tunnel_process(name)
            return {"ok": True, "message": f"tunnel '{name}' detenido"}

    def _find_tunnel(self, name: str) -> TunnelCfg | None:
        for t in self.config.forwarding.tunnels:
            if t.name == name:
                return t
        return None

    def _stop_tunnel_process(self, name: str) -> None:
        proc = self._tunnel_procs.pop(name, None)
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:  # noqa: BLE001
                try:
                    proc.kill()
                except Exception:  # noqa: BLE001
                    pass

    # -- bulk operations ---------------------------------------------------

    def apply_all_forwards(self) -> dict[str, Any]:
        """Aplica todos los forwards habilitados."""
        with self._lock:
            results = []
            for fwd in self.config.forwarding.forwards:
                if fwd.enabled:
                    r = self._apply_forward(fwd)
                    results.append({"name": fwd.name, **r})
            ok_count = sum(1 for r in results if r.get("ok"))
            return {"ok": True, "applied": ok_count, "total": len(results), "results": results}

    def clear_all_forwards(self) -> dict[str, Any]:
        """Limpia todas las reglas netsh de forwards."""
        with self._lock:
            count = 0
            for fwd in self.config.forwarding.forwards:
                self._remove_netsh_rule(fwd.local_port)
                if fwd.name in self._forward_states:
                    self._forward_states[fwd.name].active = False
                count += 1
            return {"ok": True, "cleared": count}

    def status(self) -> dict[str, Any]:
        """Estado completo de forwards y tunnels."""
        with self._lock:
            self._sync_forwards()
            self._sync_tunnels()
            return {
                "forwards": [s.to_dict() for s in self._forward_states.values()],
                "tunnels": self.list_tunnels(),
            }
