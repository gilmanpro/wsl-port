"""Forwarding config types: dataclasses for Forward, Tunnel, Vps, Bind, etc.

Estos tipos son compartidos por todos los providers de port-forwarding.
Adaptados desde port-forwarder-app/src/core/config.py para la app unificada.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class HealthCheck:
    enabled: bool = True
    fail_count_before_pause: int = 3


@dataclass
class ForwardSchedule:
    days: list[str] = field(default_factory=list)
    start: str | None = None
    end: str | None = None


@dataclass
class Forward:
    id: str
    listen_port: int
    listen_address: str = "0.0.0.0"
    wsl_distro: str = ""
    wsl_port: int = 0
    protocol: str = "tcp"
    auto_apply: bool = True
    health_check: HealthCheck = field(default_factory=HealthCheck)
    schedule: ForwardSchedule | None = None

    @property
    def firewall_name(self) -> str:
        return f"WSL-Fwd-{self.listen_port}"


@dataclass
class Vps:
    id: str
    host: str = ""
    user: str = ""
    port: int = 22
    identity_file: str = ""
    secret_ref: str | None = None


@dataclass
class Bind:
    host: str = "127.0.0.1"
    port: int = 0


@dataclass
class TunnelHealthGate:
    enabled: bool = True


@dataclass
class Tunnel:
    id: str
    type: str = "ssh"  # ssh | tailscale | cloudflare
    enabled: bool = True
    vps_id: str = ""
    local_bind: Bind = field(default_factory=Bind)
    remote_binds: list[Bind] = field(default_factory=list)
    keepalive_interval: int = 30
    keepalive_count: int = 3
    auto_start: bool = True
    health_gate: TunnelHealthGate = field(default_factory=TunnelHealthGate)
    jump: str | None = None  # multi-hop
    local_url: str = ""  # tailscale/cloudflare: URL del servicio local
    funnel: bool = False  # tailscale funnel

    @property
    def ssh_dest(self) -> str:
        """Destino local del tunnel: host:port del servicio."""
        return f"{self.local_bind.host}:{self.local_bind.port}"


@dataclass
class ForwardingAlerts:
    tunnel_down_minutes: int = 2
    forward_fail_count: int = 3
    vps_latency_ms: int = 500
    check_interval_seconds: int = 15


@dataclass
class Maintenance:
    active: bool = False
    start: str | None = None
    end: str | None = None


@dataclass
class ForwardingUi:
    supervisor_interval_seconds: int = 10


@dataclass
class ForwardingAppConfig:
    """Config subset for port-forwarding features."""
    forwards: list[Forward] = field(default_factory=list)
    tunnels: list[Tunnel] = field(default_factory=list)
    vps_list: list[Vps] = field(default_factory=list)
    alerts: ForwardingAlerts = field(default_factory=ForwardingAlerts)
    ui: ForwardingUi = field(default_factory=ForwardingUi)
    maintenance: Maintenance = field(default_factory=Maintenance)


class ForwardConfigStore:
    """Minimal config store for the forwarding supervisor.

    Wraps the wsl-manager-gui ConfigStore, extending it with forwarding
    fields loaded from a separate JSON section or file.
    """

    def __init__(self) -> None:
        self.cfg = ForwardingAppConfig()

    def get_vps(self, vps_id: str) -> Vps | None:
        return next((v for v in self.cfg.vps_list if v.id == vps_id), None)

    def get_forward(self, fwd_id: str) -> Forward | None:
        return next((f for f in self.cfg.forwards if f.id == fwd_id), None)

    def get_tunnel(self, tun_id: str) -> Tunnel | None:
        return next((t for t in self.cfg.tunnels if t.id == tun_id), None)
