"""ResourceProvider: limites globales (.wslconfig), por distro (systemd,
experimental) y metricas (R1-R8).
"""
from __future__ import annotations

import json
import re
import shlex
from pathlib import Path
from typing import Optional

from src.core.config import ConfigStore, GlobalLimits, PerDistroLimits
from src.providers.base import CommandResult, DistroMetrics
from src.providers.wsl_config_provider import WslConfigProvider
from src.providers.wsl_provider import WslProvider
from src.utils.subprocess_async import run

_WSL_CONFIG_SECTION = "wsl2"


class ResourceProvider:
    def __init__(self, config_store: ConfigStore, wsl_provider: WslProvider | None = None) -> None:
        self._store = config_store
        self._wsl = wsl_provider or WslProvider(config_store)
        self._cfg_file = WslConfigProvider()

    # -- limites globales (R1) ---------------------------------------------------

    def get_global_limits(self) -> GlobalLimits:
        return self._store.get().resources.global_limits

    def set_global_limits(self, limits: GlobalLimits) -> CommandResult:
        """Escribe [wsl2] en .wslconfig con backup + validacion; persiste en config.json."""
        sections = self._cfg_file.read_wslconfig()
        section = dict(sections.get(_WSL_CONFIG_SECTION, {}))
        mapping = {
            "memory_gb": "memory",
            "processors": "processors",
            "swap_gb": "swap",
            "auto_memory_reclaim": "autoMemoryReclaim",
            "sparse_vhd": "sparseVhd",
        }
        values = limits.model_dump(exclude_none=True)

        def gb(v: float) -> str:
            return str(int(v)) if float(v).is_integer() else str(v)

        if "memory_gb" in values:
            section["memory"] = f"{gb(values['memory_gb'])}GB"
        if "processors" in values:
            section["processors"] = str(values["processors"])
        if "swap_gb" in values:
            section["swap"] = f"{gb(values['swap_gb'])}GB"
        if "auto_memory_reclaim" in values:
            section["autoMemoryReclaim"] = values["auto_memory_reclaim"]
        if "sparse_vhd" in values:
            section["sparseVhd"] = "true" if values["sparse_vhd"] else "false"
        sections[_WSL_CONFIG_SECTION] = section

        r = self._cfg_file.write_wslconfig(sections)
        if not r.ok:
            return r

        cfg = self._store.get()
        cfg.resources.global_limits = limits
        self._store.save(cfg)
        return CommandResult(ok=True, output="limites globales aplicados (requieren wsl --shutdown)")

    # -- validaciones de seguridad (prevención de command injection) ---------------

    @staticmethod
    def _validate_service_name(name: str) -> bool:
        """Valida que el nombre de servicio systemd sea seguro."""
        return bool(re.fullmatch(r"[a-zA-Z0-9._-]+", name))

    @staticmethod
    def _validate_memory_max(val: str) -> bool:
        """Valida que memory_max sea un valor seguro para systemd (ej. '4G', '512M', '90%')."""
        return bool(re.fullmatch(r"\d+[GMK]?", val)) or bool(re.fullmatch(r"\d+(\.\d+)?%", val))

    @staticmethod
    def _validate_cpu_quota(val: str) -> bool:
        """Valida que cpu_quota sea un porcentaje seguro (ej. '200%')."""
        return bool(re.fullmatch(r"\d+%", val))

    @staticmethod
    def _validate_tasks_max(val: int) -> bool:
        """Valida que tasks_max sea un entero positivo."""
        return isinstance(val, int) and val > 0

    @staticmethod
    def _validate_distro_name(distro: str) -> bool:
        """Valida que el nombre de distro sea seguro para usar en comandos."""
        return bool(re.fullmatch(r"[a-zA-Z0-9._-]+", distro))

    def _validate_distro_exists(self, distro: str) -> CommandResult | None:
        """Valida que la distro exista en la lista real de WSL. Devuelve None si OK."""
        try:
            installed = [d.name for d in self._wsl.list_distros()]
        except Exception:
            # Si no se puede obtener la lista, no bloquear pero registrar
            return None
        if distro not in installed:
            return CommandResult(
                ok=False,
                error=f"distro '{distro}' no existe. Distros disponibles: {', '.join(installed) or '(ninguna)'}",
            )
        return None

    # -- limites por distro (R4, experimental via systemd) -------------------------

    def _wsl_root(self, distro: str, cmd: str) -> CommandResult:
        """Valida que la distro exista antes de ejecutar comandos como root."""
        validation = self._validate_distro_exists(distro)
        if validation is not None:
            return validation
        return run(["wsl.exe", "-d", distro, "-u", "root", "--", "sh", "-lc", cmd], timeout=60)

    def get_distro_limits(self, distro: str) -> Optional[PerDistroLimits]:
        for item in self._store.get().resources.per_distro:
            if item.distro == distro:
                return item
        return None

    def set_distro_limits(self, limits: PerDistroLimits) -> CommandResult:
        """Escribe drop-ins de systemd en la distro (scope all/user/service)."""
        if not limits.enabled:
            return self.clear_distro_limits(limits.distro)

        # --- Validación del nombre de distro (formato) ---
        if not self._validate_distro_name(limits.distro):
            raise ValueError(f"Nombre de distro inválido: {limits.distro!r}")

        # --- Validación de que la distro existe en WSL ---
        exists_err = self._validate_distro_exists(limits.distro)
        if exists_err is not None:
            return exists_err

        # --- Validación del nombre de servicio (si aplica) ---
        if limits.scope == "service" and limits.service:
            if not self._validate_service_name(limits.service):
                raise ValueError(f"Nombre de servicio inválido: {limits.service!r}")

        mem = limits.memory_max
        quota = limits.cpu_quota
        tasks = limits.tasks_max

        # --- Validación de campos de resource limits ---
        if mem is not None and not self._validate_memory_max(mem):
            raise ValueError(f"memory_max inválido: {mem!r} (usar formato como '4G', '512M', '90%')")
        if quota is not None and not self._validate_cpu_quota(quota):
            raise ValueError(f"cpu_quota inválido: {quota!r} (usar formato como '200%')")
        if tasks is not None and not self._validate_tasks_max(tasks):
            raise ValueError(f"tasks_max inválido: {tasks!r} (debe ser entero positivo)")

        # --- Construcción del comando con shlex.quote() ---
        if limits.scope == "service" and limits.service:
            svc = limits.service.replace(".service", "")
            path = f"/etc/systemd/system/{svc}.service.d/99-wsl-manager.conf"
            body = "[Service]\n"
            if mem:
                body += f"MemoryMax={mem}\n"
            if quota:
                body += f"CPUQuota={quota}\n"
            if tasks:
                body += f"TasksMax={tasks}\n"
            cmd = f"mkdir -p /etc/systemd/system/{svc}.service.d && printf '%s' {shlex.quote(body)} > {path} && systemctl daemon-reload"
        elif limits.scope == "user":
            path = "/etc/systemd/user.conf.d/99-wsl-manager.conf"
            body = "[Manager]\n"
            if mem:
                body += f"DefaultMemoryMax={mem}\n"
            if tasks:
                body += f"DefaultTasksMax={tasks}\n"
            cmd = f"mkdir -p /etc/systemd/user.conf.d && printf '%s' {shlex.quote(body)} > {path} && systemctl daemon-reload"
        else:  # all
            path = "/etc/systemd/system.conf.d/99-wsl-manager.conf"
            body = "[Manager]\n"
            if mem:
                body += f"DefaultMemoryMax={mem}\n"
            if quota:
                body += f"DefaultCPUQuotaSec={quota}\n"
            if tasks:
                body += f"DefaultTasksMax={tasks}\n"
            cmd = f"mkdir -p /etc/systemd/system.conf.d && printf '%s' {shlex.quote(body)} > {path} && systemctl daemon-reload"

        r = self._wsl_root(limits.distro, cmd)
        if not r.ok:
            # No persistir un limite que no se pudo aplicar
            return CommandResult(ok=False, error=f"no se pudo aplicar en la distro: {r.error.strip() or r.output.strip()}")

        cfg = self._store.get()
        existing = [i for i in cfg.resources.per_distro if i.distro != limits.distro]
        existing.append(limits)
        cfg.resources.per_distro = existing
        self._store.save(cfg)
        return CommandResult(ok=True, output=f"limites de '{limits.distro}' aplicados via systemd")

    @staticmethod
    def _quote(text: str) -> str:
        """Delega a shlex.quote para quoting seguro de strings en shell."""
        return shlex.quote(text)

    def clear_distro_limits(self, distro: str) -> CommandResult:
        # --- Validación de que la distro existe en WSL ---
        exists_err = self._validate_distro_exists(distro)
        if exists_err is not None:
            return exists_err

        cfg = self._store.get()
        cfg.resources.per_distro = [i for i in cfg.resources.per_distro if i.distro != distro]
        self._store.save(cfg)
        # Quita los drop-ins si existen (ignora errores)
        cmds = [
            "rm -rf /etc/systemd/system.conf.d/99-wsl-manager.conf",
            "rm -rf /etc/systemd/user.conf.d/99-wsl-manager.conf",
        ]
        for c in cmds:
            self._wsl_root(distro, c)
        return CommandResult(ok=True, output=f"limites de '{distro}' eliminados")

    # -- metricas (R3) -------------------------------------------------------------

    def get_metrics(self, distro: str | None = None) -> list[DistroMetrics]:
        names = [distro] if distro else [d.name for d in self._wsl.list_distros()]
        return [m for m in (self._wsl.metrics(n) for n in names) if m is not None]

    # -- recomendador (R8, P2) -------------------------------------------------------

    def recommend_limits(self, ram_gb: float, cpus: int) -> dict:
        """Sugerencia basica: mitad de la RAM del host como tope de VM."""
        suggested_memory = max(2.0, round(ram_gb / 2, 1))
        return {
            "memory_gb": suggested_memory,
            "processors": max(1, cpus // 2),
            "note": "sugerencia: 50% de la RAM del host; ajustar segun uso real",
        }
