"""Flujo 'Publicar en Internet': un servicio de una distro WSL -> tunel SSH
al VPS, publicado en Internet con un solo paso."""
from __future__ import annotations

import re
import socket

from . import core


def tunnel_id(distro: str, wsl_port: int) -> str:
    base = f"pub-{distro}-{wsl_port}"
    return re.sub(r"[^A-Za-z0-9_-]", "-", base).lower()


def check_local(wsl_port: int, host: str = "127.0.0.1", timeout: float = 5.0) -> bool:
    """Comprueba que el servicio de WSL responde en 127.0.0.1:<puerto>
    (espejo de localhost de WSL2)."""
    try:
        with socket.create_connection((host, int(wsl_port)), timeout=timeout):
            return True
    except OSError:
        return False


def publish(
    distro: str,
    wsl_port: int,
    vps_id: str,
    public_port: int,
    bind: str = "0.0.0.0",
    start: bool = True,
) -> dict:
    """Publica el servicio de la distro en Internet via el VPS.

    - Verifica que la distro existe, el VPS esta registrado y el servicio
      local responde (localhost mirroring de WSL2).
    - Crea el tunel (si no existe) y lo arranca.
    - Devuelve {tunnel_id, local, public_url, vps_id}.
    """
    names = {d.get("name") for d in core.distros()}
    if distro not in names:
        raise ValueError(f"distro WSL '{distro}' no encontrada")
    vps_ids = {v.get("id") for v in core.vps_list()}
    if vps_id not in vps_ids:
        raise ValueError(
            f"VPS '{vps_id}' no registrado (ventana -> Tunnels -> Servidores VPS)"
        )
    if not check_local(int(wsl_port)):
        raise ValueError(
            f"no hay servicio en 127.0.0.1:{wsl_port} "
            "(revisa que escuche en 0.0.0.0 dentro de la distro WSL)"
        )

    tid = tunnel_id(distro, wsl_port)
    existing = [t for t in core.tunnels() if t.get("id") == tid]
    if not existing:
        r = core.run_pf([
            "tunnels", "add",
            "--id", tid,
            "--vps", vps_id,
            "--local", f"127.0.0.1:{wsl_port}",
            "--remote", f"{bind}:{public_port}",
        ])
        if r.returncode != 0:
            raise RuntimeError(r.stderr.strip() or r.stdout.strip() or "tunnels add fallo")
    if start:
        r = core.run_pf(["tunnels", "start", tid])
        if r.returncode != 0:
            raise RuntimeError(r.stderr.strip() or r.stdout.strip() or "tunnels start fallo")

    vps = next((v for v in core.vps_list() if v.get("id") == vps_id), {})
    public_url = f"http://{vps.get('host', '?' )}:{public_port}"
    return {
        "tunnel_id": tid,
        "local": f"127.0.0.1:{wsl_port}",
        "public_url": public_url,
        "vps_id": vps_id,
    }


def unpublish(tunnel_id: str) -> bool:
    """Detiene y elimina un tunel publicado por esta app."""
    r = core.run_pf(["tunnels", "remove", tunnel_id])
    return r.returncode == 0