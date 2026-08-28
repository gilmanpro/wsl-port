"""Comandos CLI de tunnels (port-forwarding SSH remoto).

Gestiona la seccion forwarding.tunnels del config.json. Los comandos
start/stop togglean el campo enabled de cada tunnel.
"""
from __future__ import annotations

from typing import Optional

import typer

from src.core.config import TunnelCfg

app = typer.Typer(help="Gestion de tunnels SSH remotos")


# ── helpers ────────────────────────────────────────────────────────────────

def _get_tunnels(ctx: typer.Context):
    return ctx.obj.config.forwarding.tunnels


def _save_config(ctx: typer.Context) -> None:
    ctx.obj.store.save(ctx.obj.config)


def _find_tunnel(ctx: typer.Context, name: str) -> TunnelCfg | None:
    return next((t for t in _get_tunnels(ctx) if t.name == name), None)


# ── list ───────────────────────────────────────────────────────────────────

@app.command("list")
def list_tunnels(
    ctx: typer.Context,
    json_out: bool = typer.Option(False, "--json", help="salida JSON"),
) -> None:
    """Lista tunnels configurados."""
    tunnels = _get_tunnels(ctx)
    if json_out:
        ctx.obj.emit_json([t.model_dump() for t in tunnels])
        return
    if not tunnels:
        typer.echo("no hay tunnels configurados")
        return
    typer.echo(f"{'Nombre':<20} {'Remoto':<24} {'Local':<10} {'Usuario':<12} {'Estado'}")
    typer.echo("-" * 76)
    for t in tunnels:
        estado = "activo" if t.enabled else "inactivo"
        remoto = f"{t.remote_host}:{t.remote_port}"
        typer.echo(f"{t.name:<20} {remoto:<24} :{t.local_port:<9} {t.ssh_user:<12} {estado}")


# ── add ────────────────────────────────────────────────────────────────────

@app.command("add")
def add_tunnel(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="nombre identificador"),
    remote_host: str = typer.Option(..., "--remote-host", help="host remoto"),
    remote_port: int = typer.Option(22, "--remote-port", help="puerto SSH remoto"),
    local_port: int = typer.Option(2222, "--local-port", help="puerto local de escucha"),
    ssh_user: str = typer.Option("", "--ssh-user", help="usuario SSH"),
    ssh_host: str = typer.Option("", "--ssh-host", help="host SSH alternativo"),
    auto_reconnect: bool = typer.Option(True, "--auto-reconnect/--no-auto-reconnect",
                                         help="reconexion automatica"),
) -> None:
    """Agrega un nuevo tunnel SSH."""
    if _find_tunnel(ctx, name):
        typer.echo(f"error: tunnel '{name}' ya existe", err=True)
        raise typer.Exit(code=1)
    tun = TunnelCfg(
        name=name,
        remote_host=remote_host,
        remote_port=remote_port,
        local_port=local_port,
        ssh_user=ssh_user,
        ssh_host=ssh_host,
        auto_reconnect=auto_reconnect,
    )
    _get_tunnels(ctx).append(tun)
    _save_config(ctx)
    typer.echo(f"tunnel '{name}' agregado (:{local_port} -> {remote_host}:{remote_port})")


# ── remove ─────────────────────────────────────────────────────────────────

@app.command("remove")
def remove_tunnel(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="nombre del tunnel"),
) -> None:
    """Elimina un tunnel."""
    tun = _find_tunnel(ctx, name)
    if not tun:
        typer.echo(f"error: tunnel '{name}' no existe", err=True)
        raise typer.Exit(code=1)
    _get_tunnels(ctx).remove(tun)
    _save_config(ctx)
    typer.echo(f"tunnel '{name}' eliminado")


# ── start ──────────────────────────────────────────────────────────────────

@app.command("start")
def start_tunnel(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="nombre del tunnel"),
) -> None:
    """Activa un tunnel."""
    tun = _find_tunnel(ctx, name)
    if not tun:
        typer.echo(f"error: tunnel '{name}' no existe", err=True)
        raise typer.Exit(code=1)
    if tun.enabled:
        typer.echo(f"tunnel '{name}' ya esta activo")
        return
    tun.enabled = True
    _save_config(ctx)
    typer.echo(f"tunnel '{name}' activado")


# ── stop ───────────────────────────────────────────────────────────────────

@app.command("stop")
def stop_tunnel(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="nombre del tunnel"),
) -> None:
    """Desactiva un tunnel."""
    tun = _find_tunnel(ctx, name)
    if not tun:
        typer.echo(f"error: tunnel '{name}' no existe", err=True)
        raise typer.Exit(code=1)
    if not tun.enabled:
        typer.echo(f"tunnel '{name}' ya esta inactivo")
        return
    tun.enabled = False
    _save_config(ctx)
    typer.echo(f"tunnel '{name}' desactivado")
