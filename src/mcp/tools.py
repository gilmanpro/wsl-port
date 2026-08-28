"""Tools MCP mapeadas al catalogo (seccion 21.4): mismas operaciones que CLI/GUI.

El paquete 'mcp' se importa perezosamente: si no esta instalado, las tools
siguen listandose via get_tool_defs() pero serve() falla con mensaje claro.
"""
from __future__ import annotations

from src.cli.common import CliContext
from src.core.config import GlobalLimits
from src.core.profiles import ProfileService
from src.core.scheduler import Scheduler
from src.core.watcher import Watcher

# Tools que requieren autenticacion cuando mcp.token_required=True.
# Estas ejecutan acciones de escritura/destro sobre el sistema.
SENSITIVE_TOOLS: frozenset[str] = frozenset({
    "start",
    "stop",
    "restart",
    "shutdown_all",
    "snapshot",
    "clone",
    "set_global_limits",
    "schedule_add",
    "profile_apply",
    "run_command",
    "forward_add",
    "forward_remove",
    "forward_start",
    "forward_stop",
    "tunnel_add",
    "tunnel_remove",
    "tunnel_start",
    "tunnel_stop",
    "vps_add",
    "vps_remove",
    "vps_connect",
    "vps_disconnect",
})


def get_tool_defs() -> list[dict]:
    return [
        {"name": "list_distros", "description": "Lista distros con estado, version e IP", "inputSchema": {"type": "object", "properties": {}}},
        {"name": "start", "description": "Inicia una distro", "inputSchema": {"type": "object", "properties": {"distro": {"type": "string"}}, "required": ["distro"]}},
        {"name": "stop", "description": "Detiene una distro", "inputSchema": {"type": "object", "properties": {"distro": {"type": "string"}}, "required": ["distro"]}},
        {"name": "restart", "description": "Reinicia una distro", "inputSchema": {"type": "object", "properties": {"distro": {"type": "string"}}, "required": ["distro"]}},
        {"name": "shutdown_all", "description": "Apaga todas las distros", "inputSchema": {"type": "object", "properties": {}}},
        {"name": "get_ips", "description": "IPs de todas las distros", "inputSchema": {"type": "object", "properties": {}}},
        {"name": "snapshot", "description": "Snapshot de una distro", "inputSchema": {"type": "object", "properties": {"distro": {"type": "string"}}, "required": ["distro"]}},
        {"name": "clone", "description": "Clona una distro", "inputSchema": {"type": "object", "properties": {"distro": {"type": "string"}, "new_name": {"type": "string"}}, "required": ["distro", "new_name"]}},
        {"name": "set_global_limits", "description": "Limites globales (memory_gb, processors, swap_gb)", "inputSchema": {"type": "object", "properties": {"memory_gb": {"type": "number"}, "processors": {"type": "integer"}, "swap_gb": {"type": "number"}}}},
        {"name": "get_metrics", "description": "Metricas de RAM/CPU por distro", "inputSchema": {"type": "object", "properties": {"distro": {"type": "string"}}}},
        {"name": "status", "description": "Estado global (distros + alertas)", "inputSchema": {"type": "object", "properties": {}}},
        {"name": "schedule_add", "description": "Programa una tarea", "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}, "type": {"type": "string"}, "distro": {"type": "string"}, "time": {"type": "string"}, "days": {"type": "string"}}, "required": ["name", "type"]}},
        {"name": "profile_apply", "description": "Aplica un perfil", "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
        {"name": "run_command", "description": "Ejecuta un comando en una distro", "inputSchema": {"type": "object", "properties": {"distro": {"type": "string"}, "cmd": {"type": "string"}}, "required": ["distro", "cmd"]}},
        {"name": "doctor", "description": "Diagnostico del entorno WSL", "inputSchema": {"type": "object", "properties": {}}},
        # --- forwards ---
        {"name": "list_forwards", "description": "Lista port-forwards activos", "inputSchema": {"type": "object", "properties": {}}},
        {"name": "forward_add", "description": "Agrega un forward Windows->WSL", "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}, "local_port": {"type": "integer"}, "wsl_port": {"type": "integer"}, "wsl_ip": {"type": "string"}, "enabled": {"type": "boolean"}}, "required": ["name", "local_port", "wsl_port"]}},
        {"name": "forward_remove", "description": "Elimina un forward", "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
        {"name": "forward_start", "description": "Activa un forward (netsh portproxy)", "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
        {"name": "forward_stop", "description": "Desactiva un forward", "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
        # --- tunnels ---
        {"name": "list_tunnels", "description": "Lista tunnels SSH activos", "inputSchema": {"type": "object", "properties": {}}},
        {"name": "tunnel_add", "description": "Agrega un tunnel SSH", "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}, "remote_host": {"type": "string"}, "remote_port": {"type": "integer"}, "local_port": {"type": "integer"}, "ssh_user": {"type": "string"}, "ssh_host": {"type": "string"}, "auto_reconnect": {"type": "boolean"}}, "required": ["name", "remote_host"]}},
        {"name": "tunnel_remove", "description": "Elimina un tunnel", "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
        {"name": "tunnel_start", "description": "Inicia un tunnel SSH", "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
        {"name": "tunnel_stop", "description": "Detiene un tunnel SSH", "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
        # --- vps / publish ---
        {"name": "list_vps", "description": "Lista VPS configurados para publicar", "inputSchema": {"type": "object", "properties": {}}},
        {"name": "vps_add", "description": "Agrega un VPS para publicar servicios", "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}, "host": {"type": "string"}, "user": {"type": "string"}, "port": {"type": "integer"}, "identity_file": {"type": "string"}}, "required": ["id", "host"]}},
        {"name": "vps_remove", "description": "Elimina un VPS configurado", "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
        {"name": "vps_connect", "description": "Abre un tunnel SSH al VPS", "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}, "name": {"type": "string"}, "remote_port": {"type": "integer"}, "local_port": {"type": "integer"}}, "required": ["id"]}},
        {"name": "vps_disconnect", "description": "Cierra todos los tunnels de un VPS", "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
    ]


class McpTools:
    def __init__(self, ctx: CliContext) -> None:
        self.ctx = ctx

    def call(self, name: str, arguments: dict | None = None) -> dict:
        ctx = self.ctx
        args = arguments or {}
        fn = getattr(self, f"tool_{name}", None)
        if fn is None:
            return {"error": f"tool desconocida: {name}"}
        try:
            return fn(**args)
        except TypeError as e:
            return {"error": f"argumentos invalidos: {e}"}
        except Exception as e:  # noqa: BLE001
            return {"error": str(e)}

    # --- tools ---------------------------------------------------------------

    def tool_list_distros(self) -> dict:
        distros = self.ctx.wsl.list_distros()
        for d in distros:
            if d.state == "Running":
                d.ip = self.ctx.wsl.get_ip(d.name)
        return {"distros": [d.to_dict() for d in distros]}

    def tool_start(self, distro: str) -> dict:
        r = self.ctx.wsl.start(distro)
        self.ctx.metrics.log_event("mcp_start", distro, "iniciada via MCP")
        return {"ok": r.ok, "error": r.error or None}

    def tool_stop(self, distro: str) -> dict:
        r = self.ctx.wsl.stop(distro)
        return {"ok": r.ok, "error": r.error or None}

    def tool_restart(self, distro: str) -> dict:
        r = self.ctx.wsl.restart(distro)
        return {"ok": r.ok, "error": r.error or None}

    def tool_shutdown_all(self) -> dict:
        r = self.ctx.wsl.shutdown_all()
        return {"ok": r.ok, "error": r.error or None}

    def tool_get_ips(self) -> dict:
        return {"ips": self.ctx.wsl.get_all_ips()}

    def tool_snapshot(self, distro: str) -> dict:
        try:
            path = self.ctx.wsl.snapshot(distro, self.ctx.config.snapshots.retention_days, self.ctx.config.snapshots.target_dir)
        except RuntimeError as e:
            return {"ok": False, "error": str(e)}
        size = path.stat().st_size if path.exists() else 0
        self.ctx.metrics.record_snapshot(distro, str(path), size)
        return {"ok": True, "path": str(path), "size_bytes": size}

    def tool_clone(self, distro: str, new_name: str) -> dict:
        r = self.ctx.wsl.clone(distro, new_name)
        return {"ok": r.ok, "error": r.error or None}

    def tool_set_global_limits(self, memory_gb: float | None = None, processors: int | None = None, swap_gb: float | None = None) -> dict:
        limits = GlobalLimits(memory_gb=memory_gb, processors=processors, swap_gb=swap_gb)
        r = self.ctx.resources.set_global_limits(limits)
        return {"ok": r.ok, "error": r.error or None, "note": "requiere wsl --shutdown"}

    def tool_get_metrics(self, distro: str | None = None) -> dict:
        return {"metrics": [m.to_dict() for m in self.ctx.resources.get_metrics(distro)]}

    def tool_status(self) -> dict:
        return Watcher(self.ctx.store, self.ctx.metrics, self.ctx.bus, self.ctx.wsl).snapshot_state()

    def tool_schedule_add(self, name: str, type: str, distro: str | None = None, time: str = "09:00", days: str = "mon,tue,wed,thu,fri") -> dict:
        import uuid

        from src.core.config import ScheduleAction, ScheduleSpec, ScheduleTask

        task = ScheduleTask(
            id=f"tarea-{uuid.uuid4().hex[:8]}",
            name=name,
            action=ScheduleAction(type=type, distro=distro),  # type: ignore[arg-type]
            schedule=ScheduleSpec(days=[d.strip() for d in days.split(",")], time=time),
        )
        Scheduler(self.ctx.store, self.ctx.metrics, self.ctx.bus, self.ctx.wsl).add_task(task)
        return {"ok": True, "id": task.id}

    def tool_profile_apply(self, name: str) -> dict:
        try:
            ok = ProfileService(self.ctx.store, self.ctx.wsl).apply(name)
        except KeyError as e:
            return {"ok": False, "error": str(e)}
        return {"ok": ok}

    def tool_run_command(self, distro: str, cmd: str) -> dict:
        r = self.ctx.wsl.run_command(distro, cmd)
        return {"ok": r.ok, "output": r.output, "error": r.error or None}

    def tool_doctor(self) -> dict:
        ctx = self.ctx
        checks = []
        v = ctx.wsl.version()
        checks.append({"check": "wsl.exe", "ok": v.ok, "detail": v.output.strip()[:80] or v.error})
        try:
            distros = ctx.wsl.list_distros()
            checks.append({"check": "distros", "ok": True, "detail": f"{len(distros)} distro(s)"})
        except Exception as e:  # noqa: BLE001
            checks.append({"check": "distros", "ok": False, "detail": str(e)})
        return {"ok": all(c["ok"] for c in checks), "checks": checks}

    # --- forwards tools -----------------------------------------------------

    def tool_list_forwards(self) -> dict:
        return {"forwards": self.ctx.forwarding.list_forwards()}

    def tool_forward_add(self, name: str, local_port: int, wsl_port: int, wsl_ip: str = "127.0.0.1", enabled: bool = True) -> dict:
        from src.core.config import ForwardItem
        fwd = ForwardItem(name=name, local_port=local_port, wsl_port=wsl_port, wsl_ip=wsl_ip, enabled=enabled)
        return self.ctx.forwarding.add_forward(fwd)

    def tool_forward_remove(self, name: str) -> dict:
        return self.ctx.forwarding.remove_forward(name)

    def tool_forward_start(self, name: str) -> dict:
        return self.ctx.forwarding.start_forward(name)

    def tool_forward_stop(self, name: str) -> dict:
        return self.ctx.forwarding.stop_forward(name)

    # --- tunnels tools ------------------------------------------------------

    def tool_list_tunnels(self) -> dict:
        return {"tunnels": self.ctx.forwarding.list_tunnels()}

    def tool_tunnel_add(self, name: str, remote_host: str, remote_port: int = 22, local_port: int = 2222, ssh_user: str = "", ssh_host: str = "", auto_reconnect: bool = True) -> dict:
        from src.core.config import TunnelCfg
        tun = TunnelCfg(name=name, remote_host=remote_host, remote_port=remote_port, local_port=local_port, ssh_user=ssh_user, ssh_host=ssh_host, auto_reconnect=auto_reconnect)
        return self.ctx.forwarding.add_tunnel(tun)

    def tool_tunnel_remove(self, name: str) -> dict:
        return self.ctx.forwarding.remove_tunnel(name)

    def tool_tunnel_start(self, name: str) -> dict:
        return self.ctx.forwarding.start_tunnel(name)

    def tool_tunnel_stop(self, name: str) -> dict:
        return self.ctx.forwarding.stop_tunnel(name)

    # --- vps / publish tools ------------------------------------------------

    def tool_list_vps(self) -> dict:
        vps_list = self.ctx.store.get().publish.vps_list
        return {"vps": [v.model_dump() for v in vps_list]}

    def tool_vps_add(self, id: str, host: str, user: str = "root", port: int = 22, identity_file: str = "") -> dict:
        from src.core.config import VpsCfg
        vps = VpsCfg(id=id, host=host, user=user, port=port, identity_file=identity_file)
        try:
            self.ctx.store.add_vps(vps)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True, "id": vps.id}

    def tool_vps_remove(self, id: str) -> dict:
        try:
            self.ctx.store.remove_vps(id)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True, "id": id}

    def tool_vps_connect(self, id: str, name: str | None = None, remote_port: int = 80, local_port: int = 8080) -> dict:
        vps = self.ctx.store.get_vps(id)
        if not vps:
            return {"ok": False, "error": f"vps '{id}' no existe"}
        from src.core.config import TunnelCfg
        tun_name = name or f"pub-{id}"
        tun = TunnelCfg(
            name=tun_name,
            remote_host=vps.host,
            remote_port=remote_port,
            local_port=local_port,
            ssh_user=vps.user,
            ssh_host=vps.host,
            auto_reconnect=True,
            enabled=True,
        )
        r = self.ctx.forwarding.add_tunnel(tun)
        if not r.get("ok"):
            return r
        r2 = self.ctx.forwarding.start_tunnel(tun_name)
        return {"ok": r2.get("ok", False), "tunnel": tun_name, "vps": id, "error": r2.get("error")}

    def tool_vps_disconnect(self, id: str) -> dict:
        vps = self.ctx.store.get_vps(id)
        if not vps:
            return {"ok": False, "error": f"vps '{id}' no existe"}
        cfg = self.ctx.store.get()
        closed = 0
        for t in cfg.forwarding.tunnels:
            if (t.ssh_host == vps.host or t.remote_host == vps.host) and t.enabled:
                r = self.ctx.forwarding.stop_tunnel(t.name)
                if r.get("ok"):
                    closed += 1
        return {"ok": True, "closed": closed, "vps": id}
