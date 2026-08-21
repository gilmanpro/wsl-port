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
# Se delega con pythonw -m (nunca con los launchers de consola del venv):
# pythonw no tiene consola, asi que ni el CLI ni sus hijos pueden abrir terminal.
WSL_PY = WSL_REPO / ".venv" / "Scripts" / "pythonw.exe"
PF_PY = PF_REPO / ".venv" / "Scripts" / "pythonw.exe"

TIMEOUT = 120

# Oculta la consola de los CLIs delegados (refuerzo por si el venv falta).
CREATE_NO_WINDOW = 0x08000000


def run_wsl(args: list[str], timeout: int = TIMEOUT) -> subprocess.CompletedProcess:
    """Ejecuta el CLI de WSL Manager (pythonw -m src.cli <args>) sin ventanas."""
    return subprocess.run(
        [str(WSL_PY), "-m", "src.cli", *args], cwd=str(WSL_REPO),
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=timeout,
        creationflags=CREATE_NO_WINDOW,
    )


def run_pf(args: list[str], timeout: int = TIMEOUT) -> subprocess.CompletedProcess:
    """Ejecuta el CLI de Port Forwarding (pythonw -m src.cli <args>) sin ventanas."""
    return subprocess.run(
        [str(PF_PY), "-m", "src.cli", *args], cwd=str(PF_REPO),
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=timeout,
        creationflags=CREATE_NO_WINDOW,
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