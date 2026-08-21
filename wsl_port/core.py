"""Nucleo integrado de wsl-port.

Delega en los CLIs de ambas aplicaciones (wsl-manager y port-forwarder) y
combina sus datos en un estado unico.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
REPOS = BASE.parent
WSL_REPO = REPOS / "wsl-manager-gui"
PF_REPO = REPOS / "port-forwarder-app"
WSL_EXE = WSL_REPO / ".venv" / "Scripts" / "wsl-manager.exe"
PF_EXE = PF_REPO / ".venv" / "Scripts" / "port-forwarder.exe"

TIMEOUT = 120


def run_wsl(args: list[str], timeout: int = TIMEOUT) -> subprocess.CompletedProcess:
    """Ejecuta el CLI de WSL Manager (wsl-manager <args>)."""
    return subprocess.run(
        [str(WSL_EXE), *args], cwd=str(WSL_REPO),
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=timeout,
    )


def run_pf(args: list[str], timeout: int = TIMEOUT) -> subprocess.CompletedProcess:
    """Ejecuta el CLI de Port Forwarding (port-forwarder <args>)."""
    return subprocess.run(
        [str(PF_EXE), *args], cwd=str(PF_REPO),
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=timeout,
    )


def _json(proc: subprocess.CompletedProcess):
    try:
        return json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError):
        return None


def distros() -> list[dict]:
    """Distros WSL: [{name, state, running, version, ...}]."""
    data = _json(run_wsl(["list", "--json"]))
    return data if isinstance(data, list) else []


def pf_status() -> dict:
    """Estado de port-forwarder: {running, forwards, tunnels, ...}."""
    data = _json(run_pf(["status", "--json"]))
    return data if isinstance(data, dict) else {}


def pf_config() -> dict:
    """config.json de Port Forwarding (para VPS y datos locales)."""
    path = Path(os.environ.get("APPDATA", "")) / "PortForwarder" / "config.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def vps_list() -> list[dict]:
    cfg = pf_config()
    return cfg.get("vps_list", []) if isinstance(cfg, dict) else []


def tunnels() -> list[dict]:
    return pf_status().get("tunnels", [])


def forwards() -> list[dict]:
    return pf_status().get("forwards", [])


def status() -> dict:
    """Estado integrado: distros WSL + forwards/tunnels/VPS + supervisor."""
    pf = pf_status()
    return {
        "distros": distros(),
        "forwards": pf.get("forwards", []),
        "tunnels": pf.get("tunnels", []),
        "vps": vps_list(),
        "supervisor_running": bool(pf.get("running")),
        "maintenance": bool(pf.get("maintenance")),
        "admin": bool(pf.get("admin")),
    }