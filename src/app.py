"""Entry point de la app: single instance + tray + ventana + workers.

Flags (seccion 12.4): --minimized, --tray-only, --validate-config,
--autostart-distro <name> --delay <N> (invocado desde HKCU Run).
"""
from __future__ import annotations

import argparse
import sys
import threading
import time
from pathlib import Path

# Permite 'python src/app.py' desde cualquier cwd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.config import ConfigError, ConfigStore
from src.core.event_bus import EventBus
from src.core.logger import get_logger, setup_logging
from src.core.metrics_store import MetricsStore
from src.core.power_events import PowerWatcher
from src.core.scheduler import Scheduler
from src.core.watcher import Watcher

log = get_logger("app")


def _single_instance() -> bool:
    """Mutex global: si otra instancia corre, sale."""
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        mutex = kernel32.CreateMutexW(None, False, "WSLManager-SingleInstance")
        return kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS
    except Exception:  # pragma: no cover
        return True


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="wsl-manager", description="WSL Manager (GUI)")
    p.add_argument("--minimized", action="store_true", help="arranca directo a tray")
    p.add_argument("--tray-only", action="store_true", help="solo tray, sin ventana")
    p.add_argument("--validate-config", action="store_true", help="valida config.json y sale")
    p.add_argument("--autostart-distro", help="distro a arrancar con retraso (HKCU Run)")
    p.add_argument("--delay", type=int, default=0, help="segundos de espera antes del arranque")
    p.add_argument("--log-level", default="INFO")
    return p.parse_args()


def _handle_autostart(args: argparse.Namespace) -> None:
    if not args.autostart_distro:
        return
    if args.delay > 0:
        time.sleep(args.delay)
    from src.providers.wsl_provider import WslProvider

    store = ConfigStore()
    WslProvider(store).start(args.autostart_distro)
    log.info("autostart: %s iniciada (delay %ss)", args.autostart_distro, args.delay)


def main() -> None:
    args = _parse_args()
    setup_logging(args.log_level)

    # Modo autostart: arranca la distro y termina (sin GUI)
    _handle_autostart(args)
    if args.autostart_distro:
        log.info("modo autostart completado")
        sys.exit(0)

    store = ConfigStore()
    try:
        store.load()
    except ConfigError as e:
        log.error("config invalida: %s", e)
        print(f"[wsl-manager] {e}", file=sys.stderr)
        print("[wsl-manager] modo seguro: corrige o borra el config.json", file=sys.stderr)
        sys.exit(3)

    if args.validate_config:
        print("config valida")
        sys.exit(0)

    if not _single_instance():
        log.warning("otra instancia de WSL Manager ya esta corriendo")
        sys.exit(0)

    cfg = store.get()
    ctx = _build_ctx(store, cfg)
    _start_services(ctx)
    _apply_boot(ctx)

    # GUI (opcional para entornos sin display)
    from src.gui.tray import TrayApp
    from src.gui.window import MainWindow

    try:
        window = MainWindow(ctx, theme=cfg.ui.theme)
    except Exception:  # noqa: BLE001 - sin display
        log.exception("GUI no disponible; corriendo headless")
        _run_headless(ctx)
        return

    tray = TrayApp(ctx, window)
    tray.start()
    if not args.minimized:
        window.show()
    window.root.protocol(
        "WM_DELETE_WINDOW",
        lambda: window.hide() if cfg.ui.close_to_tray else window.close(),
    )

    # API REST opcional (P1)
    _start_api(ctx)

    # Panel web local opcional (M7, P2)
    _start_web_panel(ctx)

    # Refresh periodico del tray (estado dinamico)
    def _refresh_loop() -> None:
        while True:
            time.sleep(cfg.ui.refresh_interval_seconds * 5)
            try:
                tray.update()
                window.refresh_dashboard()
            except Exception:  # noqa: BLE001
                break

    threading.Thread(target=_refresh_loop, daemon=True).start()
    window.run()


def _build_ctx(store, cfg):
    from types import SimpleNamespace

    from src.providers.autostart_provider import AutoStartProvider
    from src.providers.resource_provider import ResourceProvider
    from src.providers.wsl_provider import WslProvider

    bus = EventBus()
    metrics = MetricsStore()
    wsl = WslProvider(store, cfg.windows.wsl_exe)
    return SimpleNamespace(
        store=store,
        config=cfg,
        bus=bus,
        metrics=metrics,
        wsl=wsl,
        resources=ResourceProvider(store, wsl),
        autostart=AutoStartProvider(),
    )


def _start_services(ctx) -> None:
    watcher = Watcher(ctx.store, ctx.metrics, ctx.bus, ctx.wsl)
    scheduler = Scheduler(ctx.store, ctx.metrics, ctx.bus, ctx.wsl)
    power = PowerWatcher(ctx.store, ctx.metrics, ctx.bus)
    watcher.start()
    scheduler.start()
    power.start()
    ctx.watcher = watcher
    ctx.scheduler = scheduler


def _apply_boot(ctx) -> None:
    """Aplica config al inicio (seccion 12.2): autoarranque de distros + limites."""
    cfg = ctx.config
    to_start = [i for i in cfg.distros.instances if i.auto_start]
    if cfg.distros.defaults.auto_start and not to_start:
        to_start = [i for i in cfg.distros.instances]
    for inst in to_start:
        if inst.delay_s:
            threading.Timer(inst.delay_s, lambda n=inst.name: ctx.wsl.start(n)).start()
        else:
            ctx.wsl.start(inst.name)
    if to_start:
        log.info("autoarranque: %s", ", ".join(i.name for i in to_start))


def _start_api(ctx) -> None:
    cfg = ctx.config
    if not cfg.api.enabled:
        return
    import threading

    def _run() -> None:
        import uvicorn

        from src.api.server import create_app

        try:
            uvicorn.run(create_app(ctx), host=cfg.api.host, port=cfg.api.port, log_level="warning", server_header=False)
        except Exception:  # noqa: BLE001
            log.exception("API REST fallo al iniciar")

    threading.Thread(target=_run, daemon=True).start()
    log.info("API REST en http://%s:%s", cfg.api.host, cfg.api.port)


def _start_web_panel(ctx) -> None:
    cfg = ctx.config
    if not cfg.ui.web_panel_enabled:
        return

    def _run() -> None:
        import uvicorn

        from src.web.web_app import create_web_app

        try:
            uvicorn.run(create_web_app(ctx), host="127.0.0.1", port=8790, log_level="warning", server_header=False)
        except Exception:  # noqa: BLE001
            log.exception("panel web fallo al iniciar")

    threading.Thread(target=_run, daemon=True).start()
    log.info("panel web en http://127.0.0.1:8790")


def _run_headless(ctx) -> None:
    log.info("modo headless: watcher + scheduler activos (Ctrl+C para salir)")
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
