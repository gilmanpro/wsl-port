"""Comandos CLI de VPS (Publicar a Internet).

Gestiona la seccion publish.vps_list del config.json.
Permite listar, agregar y eliminar VPS configurados para publicar servicios.
"""
from __future__ import annotations

from typing import Optional

import typer

from src.core.config import VpsCfg

app = typer.Typer(help="Gestion de VPS para publicar servicios a Internet")


# ── helpers ────────────────────────────────────────────────────────────────

def _get_vps_list(ctx: typer.Context):
    return ctx.obj.store.get().publish.vps_list


def _save_config(ctx: typer.Context) -> None:
    ctx.obj.store.save(ctx.obj.config)


def _find_vps(ctx: typer.Context, vps_id: str) -> VpsCfg | None:
    return next((v for v in _get_vps_list(ctx) if v.id == vps_id), None)


# ── list ───────────────────────────────────────────────────────────────────

@app.command("list")
def list_vps(
    ctx: typer.Context,
    json_out: bool = typer.Option(False, "--json", help="salida JSON"),
) -> None:
    """Lista VPS configurados."""
    vps_list = _get_vps_list(ctx)
    if json_out:
        ctx.obj.emit_json([v.model_dump() for v in vps_list])
        return
    if not vps_list:
        typer.echo("no hay VPS configurados")
        return
    typer.echo(f"{'ID':<16} {'Host':<24} {'Usuario':<12} {'Puerto':<8} {'Clave SSH'}")
    typer.echo("-" * 80)
    for v in vps_list:
        ident = v.identity_file or "(default)"
        typer.echo(f"{v.id:<16} {v.host:<24} {v.user:<12} {v.port:<8} {ident}")


# ── add ────────────────────────────────────────────────────────────────────

@app.command("add")
def add_vps(
    ctx: typer.Context,
    vps_id: str = typer.Argument(..., help="ID del VPS (nombre descriptivo)"),
    host: str = typer.Option(..., "--host", help="IP o dominio del VPS"),
    user: str = typer.Option("root", "--user", help="usuario SSH"),
    port: int = typer.Option(22, "--port", help="puerto SSH"),
    identity_file: str = typer.Option("", "--identity-file", help="ruta a clave SSH"),
) -> None:
    """Agrega un VPS para publicar servicios."""
    if _find_vps(ctx, vps_id):
        typer.echo(f"error: VPS '{vps_id}' ya existe", err=True)
        raise typer.Exit(code=1)
    vps = VpsCfg(
        id=vps_id,
        host=host,
        user=user,
        port=port,
        identity_file=identity_file,
    )
    try:
        ctx.obj.store.add_vps(vps)
    except Exception as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"VPS '{vps_id}' agregado ({user}@{host}:{port})")


# ── remove ─────────────────────────────────────────────────────────────────

@app.command("remove")
def remove_vps(
    ctx: typer.Context,
    vps_id: str = typer.Argument(..., help="ID del VPS a eliminar"),
) -> None:
    """Elimina un VPS configurado."""
    vps = _find_vps(ctx, vps_id)
    if not vps:
        typer.echo(f"error: VPS '{vps_id}' no existe", err=True)
        raise typer.Exit(code=1)
    try:
        ctx.obj.store.remove_vps(vps_id)
    except Exception as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"VPS '{vps_id}' eliminado")
