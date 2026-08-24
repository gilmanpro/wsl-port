"""Core integrado de wsl-port.

Usa los providers de ambos vendors directamente (sin subprocess delegation).
- WSL Manager config -> %APPDATA%\\WSLManager\\config.json
- Port Forwarder config -> %APPDATA%\\PortForwarder\\config.json
"""
from __future__ import annotations

import json
import logging
import re
import socket
import threading
import time
from pathlib import Path
from typing import Any

log = logging.getLogger("wsl-port.core")

# ---------------------------------------------------------------------------
# Lazy singletons
# ---------------------------------------------------------------------------

_wsl_store = None
_pf_store = None
_wsl_provider = None
_netsh = None
_wsl_ip = None
_ssh = None
_supervisor = None
_watcher = None
_metrics_pf = None
_metrics_wsl = None


def wsl_store():
    global _wsl_store
    if _wsl_store is None:
        from wsl_port.vendor.wsl_manager.core.config import ConfigStore
        _wsl_store = ConfigStore()
    return _wsl_store


def pf_store():
    global _pf_store
    if _pf_store is None:
        from wsl_port.vendor.port_forwarder.core.config import ConfigStore
        _pf_store = ConfigStore()
    return _pf_store


def wsl_provider():
    global _wsl_provider
    if _wsl_provider is None:
        from wsl_port.vendor.wsl_manager.providers.wsl_provider import WslProvider
        _wsl_provider = WslProvider()
    return _wsl_provider


def netsh():
    global _netsh
    if _netsh is None:
        from wsl_port.vendor.port_forwarder.providers.netsh_provider import NetshProvider
        _netsh = NetshProvider()
    return _netsh


def wsl_ip():
    global _wsl_ip
    if _wsl_ip is None:
        from wsl_port.vendor.port_forwarder.providers.wsl_ip_provider import WslIpProvider
        _wsl_ip = WslIpProvider()
    return _wsl_ip


def ssh_tunnel():
    global _ssh
    if _ssh is None:
        from wsl_port.vendor.port_forwarder.providers.ssh_tunnel_provider import SshTunnelProvider
        _ssh = SshTunnelProvider()
    return _ssh


def metrics_pf():
    global _metrics_pf
    if _metrics_pf is None:
        from wsl_port.vendor.port_forwarder.core.metrics_store import MetricsStore
        _metrics_pf = MetricsStore()
    return _metrics_pf


def metrics_wsl():
    global _metrics_wsl
    if _metrics_wsl is None:
        from wsl_port.vendor.wsl_manager.core.metrics_store import MetricsStore
        _metrics_wsl = MetricsStore()
    return _metrics_wsl


def supervisor():
    global _supervisor
    if _supervisor is None:
        from wsl_port.vendor.port_forwarder.core.supervisor import Supervisor
        _supervisor = Supervisor(
            store=pf_store(),
            netsh=netsh(),
            wsl=wsl_ip(),
            ssh=ssh_tunnel(),
            metrics=metrics_pf(),
        )
        # Add manually stopped tracking
        _supervisor.tunnel_manually_stopped = set()
    return _supervisor


def watcher():
    global _watcher
    if _watcher is None:
        from wsl_port.vendor.wsl_manager.core.watcher import Watcher
        _watcher = Watcher(store=wsl_store())
    return _watcher


# ---------------------------------------------------------------------------
# WSL lifecycle (W1-W7)
# ---------------------------------------------------------------------------

def distros() -> list[dict]:
    """Lista distros WSL con estado, version, IP."""
    try:
        wsl = wsl_provider()
        result = []
        for d in wsl.list_distros():
            entry = {"name": d.name, "state": d.state, "version": d.version,
                     "default": d.default, "ip": None, "running": d.state == "Running"}
            if entry["running"]:
                try:
                    # Use timeout for IP detection to avoid hanging
                    import subprocess
                    proc = subprocess.run(
                        ["wsl.exe", "-d", d.name, "hostname", "-I"],
                        capture_output=True, text=True, timeout=10,
                        creationflags=0x08000000
                    )
                    if proc.returncode == 0:
                        ip = proc.stdout.strip().split()[0] if proc.stdout.strip() else None
                        if ip and not ip.startswith("169.254"):
                            entry["ip"] = ip
                except Exception:
                    pass
            result.append(entry)
        return result
    except Exception as e:
        log.warning("distros() error: %s", e)
        return []


def start_distro(name: str) -> dict:
    try:
        r = wsl_provider().start(name)
        return {"ok": r.ok, "output": r.output, "error": r.error}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def stop_distro(name: str) -> dict:
    try:
        r = wsl_provider().stop(name)
        return {"ok": r.ok, "output": r.output, "error": r.error}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def restart_distro(name: str) -> dict:
    try:
        r = wsl_provider().restart(name)
        return {"ok": r.ok, "output": r.output, "error": r.error}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def shutdown_all() -> dict:
    try:
        r = wsl_provider().shutdown_all()
        return {"ok": r.ok, "output": r.output, "error": r.error}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_ip(name: str) -> str | None:
    try:
        import subprocess
        proc = subprocess.run(
            ["wsl.exe", "-d", name, "hostname", "-I"],
            capture_output=True, text=True, timeout=10,
            creationflags=0x08000000
        )
        if proc.returncode == 0:
            ip = proc.stdout.strip().split()[0] if proc.stdout.strip() else None
            if ip and not ip.startswith("169.254"):
                return ip
        return None
    except Exception:
        return None


def get_all_ips() -> dict[str, str | None]:
    try:
        return wsl_provider().get_all_ips()
    except Exception:
        return {}


def create_distro(name: str, no_launch: bool = True) -> dict:
    """Crear una nueva distro WSL desde el catalogo (wsl --install)."""
    try:
        r = wsl_provider().install_new(name, no_launch=no_launch)
        return {"ok": r.ok, "output": r.output, "error": r.error}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def delete_distro(name: str) -> dict:
    """Eliminar una distro WSL (wsl --unregister)."""
    try:
        from wsl_port.vendor.wsl_manager.utils.subprocess_async import run
        r = run(["wsl.exe", "--unregister", name], timeout=60)
        return {"ok": r.ok, "output": r.output, "error": r.error}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def list_available_distros() -> list[str]:
    """Listar distros disponibles para instalar (wsl --list --online)."""
    try:
        from wsl_port.vendor.wsl_manager.utils.subprocess_async import run
        r = run(["wsl.exe", "--list", "--online"], timeout=30)
        if not r.ok:
            return []
        distros = []
        for line in r.output.splitlines():
            line = line.replace("\x00", "").strip()
            if not line or "NAME" in line.upper() or "---" in line:
                continue
            # Format: "Ubuntu                  Canonical ..."
            parts = line.split()
            if parts:
                distros.append(parts[0])
        return distros
    except Exception:
        return []


def distro_metrics(name: str) -> dict | None:
    try:
        m = wsl_provider().metrics(name)
        if m is None:
            return None
        return {
            "name": m.name, "running": m.running, "ip": m.ip,
            "ram_total_mb": m.ram_total_mb, "ram_used_mb": m.ram_used_mb,
            "ram_percent": m.ram_percent, "cpus": m.cpus, "uptime_s": m.uptime_s,
        }
    except Exception:
        return None


def snapshot(name: str) -> dict:
    try:
        p = wsl_provider().snapshot(name)
        return {"ok": True, "path": str(p)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def clone(name: str, new_name: str) -> dict:
    try:
        r = wsl_provider().clone(name, new_name)
        return {"ok": r.ok, "output": r.output, "error": r.error}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def export_distro(name: str, target: str) -> dict:
    try:
        r = wsl_provider().export(name, target)
        return {"ok": r.ok, "output": r.output, "error": r.error}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def import_distro(source: str, name: str, install_dir: str) -> dict:
    try:
        r = wsl_provider().import_distro(source, name, install_dir)
        return {"ok": r.ok, "output": r.output, "error": r.error}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def run_command(name: str, cmd: str) -> dict:
    try:
        r = wsl_provider().run_command(name, cmd)
        return {"ok": r.ok, "output": r.output, "error": r.error}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Resources / .wslconfig (W5, R1)
# ---------------------------------------------------------------------------

def get_global_limits() -> dict:
    try:
        from wsl_port.vendor.wsl_manager.providers.resource_provider import ResourceProvider
        rp = ResourceProvider(store=wsl_store())
        limits = rp.get_global_limits()
        return {
            "memory_gb": limits.memory_gb, "processors": limits.processors,
            "swap_gb": limits.swap_gb, "auto_memory_reclaim": limits.auto_memory_reclaim,
            "sparse_vhd": limits.sparse_vhd,
        }
    except Exception as e:
        return {"error": str(e)}


def set_global_limits(**kwargs) -> dict:
    try:
        from wsl_port.vendor.wsl_manager.providers.resource_provider import ResourceProvider
        rp = ResourceProvider(store=wsl_store())
        from wsl_port.vendor.wsl_manager.core.config import GlobalLimits
        limits = GlobalLimits(**{k: v for k, v in kwargs.items() if v is not None})
        rp.set_global_limits(limits)
        return {"ok": True, "message": "Limites guardados (requiere wsl --shutdown)"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Autostart (W7)
# ---------------------------------------------------------------------------

def autostart_list() -> list[dict]:
    try:
        from wsl_port.vendor.wsl_manager.providers.autostart_provider import AutoStartProvider
        ap = AutoStartProvider(store=wsl_store())
        return [{"name": a.name, "delay_s": a.delay_s, "enabled": a.enabled}
                for a in ap.list_entries()]
    except Exception as e:
        return []


def autostart_set(name: str, delay: int = 0) -> dict:
    try:
        from wsl_port.vendor.wsl_manager.providers.autostart_provider import AutoStartProvider
        ap = AutoStartProvider(store=wsl_store())
        ap.set_entry(name, delay_s=delay)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def autostart_remove(name: str) -> dict:
    try:
        from wsl_port.vendor.wsl_manager.providers.autostart_provider import AutoStartProvider
        ap = AutoStartProvider(store=wsl_store())
        ap.remove_entry(name)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Forwards (F1-F8, F14)
# ---------------------------------------------------------------------------

def forwards() -> list[dict]:
    """Lista forwards con estado real (drift)."""
    try:
        cfg = pf_store().cfg
        sup = supervisor()
        result = []
        for f in cfg.forwards:
            entry = {
                "id": f.id, "listen_port": f.listen_port,
                "listen_address": f.listen_address,
                "wsl_distro": f.wsl_distro, "wsl_port": f.wsl_port,
                "protocol": f.protocol, "auto_apply": f.auto_apply,
                "state": "unknown", "ip": None,
            }
            # Use supervisor's cached state if running
            if sup.running and f.id in sup.forward_state:
                entry["state"] = sup.forward_state[f.id]
                entry["ip"] = sup.known_ips.get(f.wsl_distro)
            else:
                # Check real state via netsh
                try:
                    existing = netsh().list_forwards()
                    present = [x for x in existing if x.listen_port == f.listen_port]
                    if present:
                        entry["state"] = "ok"
                        entry["ip"] = present[0].connect_address
                    else:
                        entry["state"] = "missing"
                except Exception:
                    pass
            result.append(entry)
        return result
    except Exception as e:
        log.warning("forwards() error: %s", e)
        return []


def add_forward(fwd_id: str, listen_port: int, wsl_distro: str, wsl_port: int,
                protocol: str = "tcp", auto_apply: bool = True,
                listen_address: str = "0.0.0.0") -> dict:
    try:
        from wsl_port.vendor.port_forwarder.core.config import Forward, HealthCheck
        store = pf_store()
        fwd = Forward(
            id=fwd_id, listen_port=listen_port, listen_address=listen_address,
            wsl_distro=wsl_distro, wsl_port=wsl_port, protocol=protocol,
            auto_apply=auto_apply, health_check=HealthCheck(),
        )
        store.add_forward(fwd)
        return {"ok": True, "message": f"Forward '{fwd_id}' creado"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def remove_forward(fwd_id: str) -> dict:
    try:
        store = pf_store()
        store.remove_forward(fwd_id)
        return {"ok": True, "message": f"Forward '{fwd_id}' eliminado"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def apply_forwards() -> dict:
    """Aplica todos los forwards auto_apply."""
    try:
        sup = supervisor()
        summary = sup.run_once()
        return {"ok": True, "summary": summary}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def clear_forwards() -> dict:
    try:
        results = netsh().clear_all()
        return {"ok": True, "message": "Forwards limpiados"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def test_forward(fwd_id: str) -> dict:
    try:
        store = pf_store()
        fwd = store.get_forward(fwd_id)
        if not fwd:
            return {"ok": False, "error": f"Forward '{fwd_id}' no existe"}
        alive = netsh().test_connection(fwd.listen_port, timeout=3.0)
        return {"ok": True, "alive": alive, "port": fwd.listen_port}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def detect_conflicts(port: int) -> dict:
    try:
        pids = netsh().detect_conflicts(port)
        return {"ok": True, "conflicts": pids}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def clone_forward(fwd_id: str, new_id: str, new_port: int | None = None) -> dict:
    try:
        store = pf_store()
        fwd = store.get_forward(fwd_id)
        if not fwd:
            return {"ok": False, "error": f"Forward '{fwd_id}' no existe"}
        from wsl_port.vendor.port_forwarder.core.config import Forward, HealthCheck
        new_fwd = Forward(
            id=new_id, listen_port=new_port or fwd.listen_port + 1,
            listen_address=fwd.listen_address, wsl_distro=fwd.wsl_distro,
            wsl_port=fwd.wsl_port, protocol=fwd.protocol,
            auto_apply=fwd.auto_apply, health_check=HealthCheck(),
        )
        store.add_forward(new_fwd)
        return {"ok": True, "message": f"Forward '{new_id}' clonado"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Tunnels (T1-T10)
# ---------------------------------------------------------------------------

def tunnels() -> list[dict]:
    """Lista tunnels con estado y trafico."""
    try:
        cfg = pf_store().cfg
        sup = supervisor()
        ssh = sup.ssh  # Use supervisor's SSH provider (has cached process state)
        result = []
        for t in cfg.tunnels:
            # Use supervisor's SSH provider to check if alive
            alive = ssh.is_alive(t)
            entry = {
                "id": t.id, "type": t.type, "vps_id": t.vps_id,
                "local": f"{t.local_bind.host}:{t.local_bind.port}",
                "remote": [f"{b.host}:{b.port}" for b in t.remote_binds],
                "auto_start": t.auto_start, "enabled": t.enabled,
                "state": "running" if alive else ("stopped" if not t.enabled else "down"),
                "traffic": None,
            }
            # Traffic snapshot
            if alive and t.type == "ssh":
                try:
                    vps = pf_store().get_vps(t.vps_id)
                    if vps:
                        entry["traffic"] = ssh.traffic_snapshot(t)
                except Exception:
                    pass
            result.append(entry)
        return result
    except Exception as e:
        log.warning("tunnels() error: %s", e)
        return []


def _provider_for(t):
    """Provider segun tipo de tunnel."""
    if t.type == "ssh":
        return ssh_tunnel()
    if t.type == "tailscale":
        from wsl_port.vendor.port_forwarder.providers.tailscale_provider import TailscaleProvider
        return TailscaleProvider()
    if t.type == "cloudflare":
        from wsl_port.vendor.port_forwarder.providers.cloudflare_provider import CloudflareProvider
        return CloudflareProvider()
    return None


def add_tunnel(tun_id: str, vps_id: str, local_host: str, local_port: int,
               remote_host: str = "0.0.0.0", remote_port: int = 80,
               tunnel_type: str = "ssh") -> dict:
    try:
        from wsl_port.vendor.port_forwarder.core.config import (
            Tunnel, Bind, TunnelHealthGate,
        )
        store = pf_store()
        tun = Tunnel(
            id=tun_id, type=tunnel_type, enabled=True, vps_id=vps_id,
            local_bind=Bind(host=local_host, port=local_port),
            remote_binds=[Bind(host=remote_host, port=remote_port)],
            auto_start=True, health_gate=TunnelHealthGate(enabled=True),
        )
        store.add_tunnel(tun)
        return {"ok": True, "message": f"Tunnel '{tun_id}' creado"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def remove_tunnel(tun_id: str) -> dict:
    try:
        store = pf_store()
        tun = store.get_tunnel(tun_id)
        if tun:
            provider = _provider_for(tun)
            if provider and provider.is_alive(tun):
                provider.stop(tun)
        store.remove_tunnel(tun_id)
        return {"ok": True, "message": f"Tunnel '{tun_id}' eliminado"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def start_tunnel(tun_id: str) -> dict:
    try:
        store = pf_store()
        tun = store.get_tunnel(tun_id)
        if not tun:
            return {"ok": False, "error": f"Tunnel '{tun_id}' no existe"}
        # Use supervisor's SSH provider to track the process
        sup = supervisor()
        provider = sup.ssh if tun.type == "ssh" else _provider_for(tun)
        if not provider:
            return {"ok": False, "error": f"Tipo '{tun.type}' no soportado"}
        vps = store.get_vps(tun.vps_id) if tun.type == "ssh" else None
        if tun.type == "ssh":
            provider.start(tun, vps)
        else:
            provider.start(tun)
        # Remove from manually stopped set so supervisor can manage it again
        sup.tunnel_manually_stopped.discard(tun_id)
        return {"ok": True, "message": f"Tunnel '{tun_id}' iniciado"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def stop_tunnel(tun_id: str) -> dict:
    try:
        store = pf_store()
        tun = store.get_tunnel(tun_id)
        if not tun:
            return {"ok": False, "error": f"Tunnel '{tun_id}' no existe"}
        # Use supervisor's SSH provider to stop the process
        sup = supervisor()
        provider = sup.ssh if tun.type == "ssh" else _provider_for(tun)
        if provider:
            provider.stop(tun)
        # Mark as manually stopped so supervisor doesn't restart it
        sup.tunnel_manually_stopped.add(tun_id)
        return {"ok": True, "message": f"Tunnel '{tun_id}' detenido"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def restart_tunnel(tun_id: str) -> dict:
    try:
        store = pf_store()
        tun = store.get_tunnel(tun_id)
        if not tun:
            return {"ok": False, "error": f"Tunnel '{tun_id}' no existe"}
        # Use supervisor's SSH provider to restart the process
        sup = supervisor()
        provider = sup.ssh if tun.type == "ssh" else _provider_for(tun)
        if provider:
            provider.stop(tun)
            import time
            time.sleep(1)
            vps = store.get_vps(tun.vps_id) if tun.type == "ssh" else None
            if tun.type == "ssh":
                provider.start(tun, vps)
            else:
                provider.start(tun)
        return {"ok": True, "message": f"Tunnel '{tun_id}' reiniciado"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def tunnel_latency(tun_id: str) -> dict:
    try:
        store = pf_store()
        tun = store.get_tunnel(tun_id)
        if not tun:
            return {"ok": False, "error": f"Tunnel '{tun_id}' no existe"}
        ssh = ssh_tunnel()
        vps = store.get_vps(tun.vps_id)
        ms = ssh.latency(tun, vps)
        return {"ok": True, "latency_ms": ms}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# VPS (T3)
# ---------------------------------------------------------------------------

def vps_list() -> list[dict]:
    try:
        cfg = pf_store().cfg
        return [{"id": v.id, "host": v.host, "user": v.user, "port": v.port,
                 "identity_file": v.identity_file, "password": v.password} for v in cfg.vps_list]
    except Exception:
        return []


def add_vps(vps_id: str, host: str, user: str, port: int = 22,
            identity_file: str = "", password: str = "") -> dict:
    try:
        from wsl_port.vendor.port_forwarder.core.config import Vps
        store = pf_store()
        vps = Vps(id=vps_id, host=host, user=user, port=port,
                  identity_file=identity_file, password=password)
        store.add_vps(vps)
        return {"ok": True, "message": f"VPS '{vps_id}' creado"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def remove_vps(vps_id: str) -> dict:
    try:
        store = pf_store()
        store.remove_vps(vps_id)
        return {"ok": True, "message": f"VPS '{vps_id}' eliminado"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Health / Alerts (M3-M6)
# ---------------------------------------------------------------------------

def health_check() -> dict:
    try:
        sup = supervisor()
        summary = sup.run_once()
        return {"ok": True, "summary": summary}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def alerts(state: str | None = None) -> list[dict]:
    try:
        m = metrics_pf()
        return [{"id": a.id, "type": a.type, "message": a.message,
                 "severity": a.severity, "state": a.state, "ts": a.ts}
                for a in m.list_alerts(state=state)]
    except Exception:
        return []


def resolve_alert(alert_id: int) -> dict:
    try:
        metrics_pf().resolve_alert(alert_id)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Schedule (A3)
# ---------------------------------------------------------------------------

def schedule_list() -> list[dict]:
    try:
        from wsl_port.vendor.port_forwarder.core.scheduler import Scheduler
        sched = Scheduler(store=pf_store(), supervisor=supervisor(), metrics=metrics_pf())
        return [{"id": t.id, "name": t.name, "action": t.action.type,
                 "schedule": t.schedule, "enabled": t.enabled}
                for t in sched.list_tasks()]
    except Exception:
        return []


def schedule_add(name: str, action_type: str, time_str: str,
                 days: list[str] | None = None, tunnel: str = None,
                 profile: str = None) -> dict:
    try:
        from wsl_port.vendor.port_forwarder.core.scheduler import Scheduler
        from wsl_port.vendor.port_forwarder.core.config import ScheduleItem, ScheduleAction
        sched = Scheduler(store=pf_store(), supervisor=supervisor(), metrics=metrics_pf())
        item = ScheduleItem(
            id=f"tarea-{name.lower().replace(' ', '-')}",
            name=name,
            action=ScheduleAction(type=action_type, tunnel=tunnel, profile=profile),
            schedule={"days": days or ["mon", "tue", "wed", "thu", "fri"], "time": time_str},
        )
        sched.add_task(item)
        return {"ok": True, "message": f"Tarea '{name}' creada"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def schedule_remove(task_id: str) -> dict:
    try:
        from wsl_port.vendor.port_forwarder.core.scheduler import Scheduler
        sched = Scheduler(store=pf_store(), supervisor=supervisor(), metrics=metrics_pf())
        sched.remove_task(task_id)
        return {"ok": True, "message": f"Tarea '{task_id}' eliminada"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Profiles (A2)
# ---------------------------------------------------------------------------

def profile_list() -> list[dict]:
    try:
        from wsl_port.vendor.port_forwarder.core.profiles import Profiles
        profs = Profiles(store=pf_store(), supervisor=supervisor())
        return [{"name": p.name, "description": p.description,
                 "forwards": p.forwards, "tunnels": p.tunnels}
                for p in profs.list()]
    except Exception:
        return []


def profile_apply(name: str) -> dict:
    try:
        from wsl_port.vendor.port_forwarder.core.profiles import Profiles
        profs = Profiles(store=pf_store(), supervisor=supervisor())
        profs.apply(name)
        return {"ok": True, "message": f"Perfil '{name}' aplicado"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def profile_capture(name: str, description: str = "") -> dict:
    try:
        from wsl_port.vendor.port_forwarder.core.profiles import Profiles
        profs = Profiles(store=pf_store(), supervisor=supervisor())
        profs.capture(name, description)
        return {"ok": True, "message": f"Perfil '{name}' capturado"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Maintenance (F15)
# ---------------------------------------------------------------------------

def maintenance_on() -> dict:
    try:
        store = pf_store()
        store.cfg.maintenance.active = True
        store.save()
        return {"ok": True, "message": "Modo mantenimiento activado"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def maintenance_off() -> dict:
    try:
        store = pf_store()
        store.cfg.maintenance.active = False
        store.save()
        return {"ok": True, "message": "Modo mantenimiento desactivado"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def maintenance_status() -> dict:
    try:
        return {"ok": True, "active": pf_store().cfg.maintenance.active}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Drift (F13)
# ---------------------------------------------------------------------------

def drift_check() -> dict:
    try:
        from wsl_port.vendor.port_forwarder.providers.base import PortEntry
        declared = pf_store().cfg.forwards
        entries = netsh().declared_forwards(declared)
        drift = [e.as_dict() for e in entries if e.state != "ok"]
        return {"ok": True, "drift": drift, "total": len(entries)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Doctor (U8)
# ---------------------------------------------------------------------------

def doctor() -> dict:
    """Diagnostico del entorno."""
    checks = []
    # 1. WSL installed
    try:
        wsl = wsl_provider()
        ok = wsl.is_installed()
        checks.append({"check": "wsl_installed", "ok": ok,
                        "message": "WSL instalado" if ok else "WSL NO instalado"})
    except Exception as e:
        checks.append({"check": "wsl_installed", "ok": False, "message": str(e)})

    # 2. Admin rights
    try:
        from wsl_port.vendor.port_forwarder.utils.subprocess_async import is_admin
        ok = is_admin()
        checks.append({"check": "admin", "ok": ok,
                        "message": "Permisos admin" if ok else "Sin permisos admin (forwards requieren UAC)"})
    except Exception:
        checks.append({"check": "admin", "ok": False, "message": "No se pudo verificar admin"})

    # 3. SSH available
    import shutil
    ssh_ok = shutil.which("ssh") is not None
    checks.append({"check": "ssh", "ok": ssh_ok,
                    "message": "ssh.exe encontrado" if ssh_ok else "ssh.exe NO encontrado"})

    # 4. Distro running
    try:
        ds = distros()
        running = [d for d in ds if d.get("running")]
        checks.append({"check": "distro_running", "ok": bool(running),
                        "message": f"{len(running)} distro(s) en marcha"})
    except Exception as e:
        checks.append({"check": "distro_running", "ok": False, "message": str(e)})

    # 5. VPS reachable
    try:
        for v in vps_list():
            ssh = ssh_tunnel()
            # Simple connectivity check
            checks.append({"check": f"vps_{v['id']}", "ok": True,
                            "message": f"VPS '{v['id']}' registrado ({v['host']}:{v['port']})"})
    except Exception:
        pass

    all_ok = all(c["ok"] for c in checks)
    return {"ok": all_ok, "checks": checks}


# ---------------------------------------------------------------------------
# Unified status
# ---------------------------------------------------------------------------

def status() -> dict:
    """Estado integrado: distros WSL + forwards/tunnels/VPS + supervisor."""
    ds = distros()
    fwds = forwards()
    tuns = tunnels()
    vps = vps_list()
    sup = supervisor()
    return {
        "distros": ds,
        "forwards": fwds,
        "tunnels": tuns,
        "vps": vps,
        "supervisor_running": sup.running if hasattr(sup, "running") else False,
        "maintenance": pf_store().cfg.maintenance.active,
        "admin": _is_admin(),
    }


def _is_admin() -> bool:
    try:
        from wsl_port.vendor.port_forwarder.utils.subprocess_async import is_admin
        return is_admin()
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Publish (flujo 1-click)
# ---------------------------------------------------------------------------

def tunnel_id_for(distro: str, wsl_port: int) -> str:
    base = f"pub-{distro}-{wsl_port}"
    return re.sub(r"[^A-Za-z0-9_-]", "-", base).lower()


def check_local(wsl_port: int, host: str = "127.0.0.1", timeout: float = 5.0) -> bool:
    try:
        with socket.create_connection((host, int(wsl_port)), timeout=timeout):
            return True
    except OSError:
        return False


def publish(distro: str, wsl_port: int, vps_id: str, public_port: int,
            bind: str = "0.0.0.0", auto_start: bool = True) -> dict:
    """Publica un servicio WSL en Internet via VPS (1 clic)."""
    names = {d.get("name") for d in distros()}
    if distro not in names:
        raise ValueError(f"distro WSL '{distro}' no encontrada")
    vps_ids = {v.get("id") for v in vps_list()}
    if vps_id not in vps_ids:
        raise ValueError(f"VPS '{vps_id}' no registrado")
    if not check_local(int(wsl_port)):
        raise ValueError(f"no hay servicio en 127.0.0.1:{wsl_port}")

    tid = tunnel_id_for(distro, wsl_port)
    existing = [t for t in tunnels() if t.get("id") == tid]
    if not existing:
        r = add_tunnel(tid, vps_id, "127.0.0.1", wsl_port, bind, public_port)
        if not r.get("ok"):
            raise RuntimeError(r.get("error", "fallo al crear tunnel"))
    if auto_start:
        start_tunnel(tid)

    vps = next((v for v in vps_list() if v.get("id") == vps_id), {})
    public_url = f"http://{vps.get('host', '?')}:{public_port}"
    return {"tunnel_id": tid, "local": f"127.0.0.1:{wsl_port}",
            "public_url": public_url, "vps_id": vps_id}


def unpublish(tun_id: str) -> bool:
    """Detiene y elimina un tunnel publicado."""
    stop_tunnel(tun_id)
    r = remove_tunnel(tun_id)
    return r.get("ok", False)


# ---------------------------------------------------------------------------
# Supervisor control
# ---------------------------------------------------------------------------

def supervisor_start() -> None:
    sup = supervisor()
    if not sup.running:
        sup.start()


def supervisor_stop() -> None:
    sup = supervisor()
    if sup.running:
        sup.stop()


def supervisor_run_forever() -> None:
    """Ejecuta el supervisor en el hilo actual (modo headless)."""
    sup = supervisor()
    sup.run_forever()


# ---------------------------------------------------------------------------
# Config export/import
# ---------------------------------------------------------------------------

def config_export(path: str) -> dict:
    try:
        store = pf_store()
        data = store.as_yaml_safe_json()
        Path(path).write_text(data, encoding="utf-8")
        return {"ok": True, "message": f"Config exportada a {path}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def config_import(path: str) -> dict:
    try:
        from wsl_port.vendor.port_forwarder.core.config import parse_config
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        cfg = parse_config(data)
        store = pf_store()
        store.cfg = cfg
        store.save()
        return {"ok": True, "message": f"Config importada desde {path}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def config_validate() -> dict:
    try:
        store = pf_store()
        from wsl_port.vendor.port_forwarder.core.config import _validate
        _validate(store.cfg)
        return {"ok": True, "message": "Config valida"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Secrets
# ---------------------------------------------------------------------------

def secret_set(ref: str, value: str) -> dict:
    try:
        from wsl_port.vendor.port_forwarder.utils.secrets import SecretsStore
        SecretsStore().set(ref, value)
        return {"ok": True, "message": f"Secreto '{ref}' guardado"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def secret_check(ref: str) -> dict:
    try:
        from wsl_port.vendor.port_forwarder.utils.secrets import SecretsStore
        ok = SecretsStore().check(ref)
        return {"ok": True, "exists": ok}
    except Exception as e:
        return {"ok": False, "error": str(e)}
