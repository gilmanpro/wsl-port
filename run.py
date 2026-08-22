"""Punto de entrada principal de wsl-port.

Soporte:
- Modo GUI (ventana con pestanas)
- Modo headless/background (pythonw, sin consola)
- Auto-start en Windows (Registro HKCU\Run)
"""
from __future__ import annotations

import sys
import argparse
import logging
import json
from pathlib import Path


def _setup_logging(level: str = "INFO") -> None:
    from wsl_port.vendor.port_forwarder.core.logger import setup_logging
    setup_logging(level=level, console=True)


def run_gui(minimized: bool = False, tray_only: bool = False) -> None:
    """Ejecutar con interfaz grafica."""
    try:
        from wsl_port.ui.main_window import run
        run()
    except ImportError as e:
        print(f"GUI no disponible (faltan dependencias): {e}")
        print("Instala: pip install ttkbootstrap pystray Pillow winotify")
        print("Usa 'wsl-port status' como alternativa CLI.")
        sys.exit(1)


def run_headless() -> None:
    """Ejecutar en segundo plano (sin ventana)."""
    from wsl_port import core
    print("Iniciando wsl-port en modo headless...")
    try:
        core.supervisor_run_forever()
    except KeyboardInterrupt:
        print("\nApagando wsl-port...")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="wsl-port",
                                description="WSL Manager + Port Forwarding integrados")
    p.add_argument("--headless", action="store_true", help="Modo headless (sin ventana)")
    p.add_argument("--minimized", action="store_true", help="Minimizado a la bandeja")
    p.add_argument("--tray-only", action="store_true", help="Solo bandeja del sistema")
    p.add_argument("--validate-config", action="store_true", help="Validar config y salir")
    p.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO")

    args = p.parse_args(argv)

    _setup_logging(args.log_level)

    if args.validate_config:
        from wsl_port import core
        r = core.config_validate()
        print(r.get("message", r.get("error", "ok")))
        return 0 if r.get("ok") else 1

    if args.headless:
        run_headless()
    else:
        run_gui(args.minimized, args.tray_only)

    return 0


if __name__ == "__main__":
    sys.exit(main())
