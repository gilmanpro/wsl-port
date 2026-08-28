"""Helpers de subprocess para providers de port-forwarding.

Funciones necesarias por los providers (netsh, ssh, tailscale, cloudflare).
Adaptadas desde port-forwarder-app/src/utils/subprocess_async.py.

Diferencias con subprocess_async.py de wsl-manager-gui:
- run() devuelve CompletedProcess (no CommandResult) para compatibilidad
  con los providers de port-forwarder-app.
- Incluye run_powershell() e is_admin() para operaciones de firewall/netsh.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import Sequence

CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

POWERSHELL_EXE = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"


def _creation_flags() -> int:
    return CREATE_NO_WINDOW


def run(
    args: Sequence[str],
    timeout: float = 30.0,
    check: bool = True,
    input_text: str | None = None,
    env: dict | None = None,
) -> subprocess.CompletedProcess:
    """Ejecuta un comando sin ventana; lanza CalledProcessError si check=True.

    Devuelve CompletedProcess con texto decodificado (utf-8 con fallback).
    """
    proc = subprocess.run(
        list(args),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        creationflags=_creation_flags(),
        input=input_text,
        env=env,
    )
    if check and proc.returncode != 0:
        raise subprocess.CalledProcessError(
            proc.returncode, list(args), proc.stdout, proc.stderr
        )
    return proc


def run_powershell(
    script: str,
    timeout: float = 60.0,
    check: bool = True,
    elevate: bool = False,
) -> subprocess.CompletedProcess:
    """Ejecuta un script PowerShell.

    elevate=True lanza con -Verb RunAs (UAC). Solo debe usarse para
    netsh/firewall (UAC selectivo).
    """
    if elevate:
        ps = (
            f"Start-Process -FilePath '{POWERSHELL_EXE}' -Verb RunAs "
            f"-ArgumentList '-NoProfile','-ExecutionPolicy','Bypass',"
            f"'-EncodedCommand','{_b64(script)}' -Wait"
        )
        args = [POWERSHELL_EXE, "-NoProfile", "-NonInteractive", "-Command", ps]
        proc = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout + 30,
            creationflags=_creation_flags(),
        )
        return proc
    args = [POWERSHELL_EXE, "-NoProfile", "-NonInteractive", "-Command", script]
    return run(args, timeout=timeout, check=check)


def _b64(text: str) -> str:
    import base64
    return base64.b64encode(text.encode("utf-16-le")).decode("ascii")


def is_admin() -> bool:
    """True si el proceso actual tiene privilegios de administrador."""
    if sys.platform != "win32":
        try:
            return os.geteuid() == 0  # type: ignore[attr-defined]
        except AttributeError:
            return False
    try:
        return run(
            [POWERSHELL_EXE, "-NoProfile", "-Command",
             "([Security.Principal.WindowsPrincipal]"
             "[Security.Principal.WindowsIdentity]::GetCurrent()"
             ").IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)"],
            check=False,
        ).stdout.strip() == "True"
    except Exception:
        return False
