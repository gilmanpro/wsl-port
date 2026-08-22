"""Flujo 'Publicar en Internet': servicio WSL -> tunnel SSH -> VPS.

Usa core.py directamente (sin subprocess delegation).
"""
from __future__ import annotations

from . import core


def tunnel_id(distro: str, wsl_port: int) -> str:
    return core.tunnel_id_for(distro, wsl_port)


def check_local(wsl_port: int, host: str = "127.0.0.1", timeout: float = 5.0) -> bool:
    return core.check_local(wsl_port, host, timeout)


def publish(distro: str, wsl_port: int, vps_id: str, public_port: int,
            bind: str = "0.0.0.0", start: bool = True) -> dict:
    """Publica el servicio de la distro en Internet via el VPS."""
    return core.publish(distro, wsl_port, vps_id, public_port, bind, start)


def unpublish(tunnel_id: str) -> bool:
    """Detiene y elimina un tunnel publicado."""
    return core.unpublish(tunnel_id)
