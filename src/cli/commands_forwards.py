"""Comandos CLI de forwards (port-forwarding Windows -> WSL).

Gestiona la seccion forwarding del config.json. Los comandos
start/stop togglean el campo enabled de cada forward.
"""
from __future__ import annotations

from typing import Optional

import typer

from src.core.config import ForwardItem

app = typer.Typer(help="Gestion de forwards Windows -> WSL")


# ── helpers ────────────────────────────────────────────────────────────────

def _get_forwards(ctx: typer.Context):
    return ctx.obj.config.forwarding.forwards


def _save_config(ctx: typer.Context) -> None:
    ctx.obj.store.save(ctx.obj.config)


def _find_forward(ctx: typer.Context, name: str) -> ForwardItem | None:
    return next((f for f in _get_forwards(ctx) if f.name == name), None)


# ── list ───────────────────────────────────────────────────────────────────

@app.command("list")
def list_forwards(
    ctx: typer.Context,
    json_out: bool = typer.Option(False, "--json", help="salida JSON"),
) -> None:
    """Lista forwards configurados."""
    forwards = _get_forwards(ctx)
    if json_out:
        ctx.obj.emit_json([f.model_dump() for f in forwards])
        return
    if not forwards:
        typer.echo("no hay forwards configurados")
        return
    typer.echo(f"{'Nombre':<20} {'Local':<10} {'WSL':<10} {'IP':<16} {'Estado'}")
    typer.echo("-" * 64)
    for f in forwards:
        estado = "activo" if f.enabled else "inactivo"
        typer.echo(f"{f.name:<20} :{f.local_port:<9} :{f.wsl_port:<9} {f.wsl_ip:<16} {estado}")


# ── add ────────────────────────────────────────────────────────────────────

@app.command("add")
def add_forward(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="nombre identificador"),
    local_port: int = typer.Option(..., "--local-port", help="puerto en Windows"),
    wsl_port: int = typer.Option(..., "--wsl-port", help="puerto en WSL"),
    wsl_ip: str = typer.Option("127.0.0.1", "--wsl-ip", help="IP de la distro WSL"),
) -> None:
    """Agrega un nuevo forward."""
    if _find_forward(ctx, name):
        typer.echo(f"error: forward '{name}' ya existe", err=True)
        raise typer.Exit(code=1)
    fwd = ForwardItem(name=name, local_port=local_port, wsl_port=wsl_port, wsl_ip=wsl_ip)
    _get_forwards(ctx).append(fwd)
    _save_config(ctx)
    typer.echo(f"forward '{name}' agregado (:{local_port} -> {wsl_ip}:{wsl_port})")


# ── remove ─────────────────────────────────────────────────────────────────

@app.command("remove")
def remove_forward(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="nombre del forward"),
) -> None:
    """Elimina un forward."""
    fwd = _find_forward(ctx, name)
    if not fwd:
        typer.echo(f"error: forward '{name}' no existe", err=True)
        raise typer.Exit(code=1)
    _get_forwards(ctx).remove(fwd)
    _save_config(ctx)
    typer.echo(f"forward '{name}' eliminado")


# ── start ──────────────────────────────────────────────────────────────────

@app.command("start")
def start_forward(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="nombre del forward"),
) -> None:
    """Activa un forward."""
    fwd = _find_forward(ctx, name)
    if not fwd:
        typer.echo(f"error: forward '{name}' no existe", err=True)
        raise typer.Exit(code=1)
    if fwd.enabled:
        typer.echo(f"forward '{name}' ya esta activo")
        return
    fwd.enabled = True
    _save_config(ctx)
    typer.echo(f"forward '{name}' activado")


# ── stop ───────────────────────────────────────────────────────────────────

@app.command("stop")
def stop_forward(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="nombre del forward"),
) -> None:
    """Desactiva un forward."""
    fwd = _find_forward(ctx, name)
    if not fwd:
        typer.echo(f"error: forward '{name}' no existe", err=True)
        raise typer.Exit(code=1)
    if not fwd.enabled:
        typer.echo(f"forward '{name}' ya esta inactivo")
        return
    fwd.enabled = False
    _save_config(ctx)
    typer.echo(f"forward '{name}' desactivado")
