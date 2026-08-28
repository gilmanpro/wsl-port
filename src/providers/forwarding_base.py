"""Tipos base y Protocol para providers de port-forwarding.

PortEntry + Protocolos (NetshProvider, WslIpProvider, SshTunnelProvider)
adaptados desde port-forwarder-app/src/providers/base.py.

CommandResult ya existe en src.providers.base — re-exportado para conveniencia.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from src.core.forward_config import Forward
from src.providers.base import CommandResult  # noqa: F401 - re-export


@dataclass
class PortEntry:
    """Entrada del mapa de puertos: estado real de un listen port."""
    listen_address: str
    listen_port: int
    connect_address: str
    connect_port: int
    kind: str = "portproxy"
    declared: bool = False
    forward_id: str | None = None
    state: str = "unknown"  # ok | broken | extra | paused

    def as_dict(self) -> dict[str, Any]:
        return {
            "listen_address": self.listen_address,
            "listen_port": self.listen_port,
            "connect_address": self.connect_address,
            "connect_port": self.connect_port,
            "kind": self.kind,
            "declared": self.declared,
            "forward_id": self.forward_id,
            "state": self.state,
        }


class NetshProvider(Protocol):
    def add_forward(self, forward: Forward, ip: str) -> CommandResult: ...
    def remove_forward(self, forward: Forward) -> CommandResult: ...
    def list_forwards(self) -> list[Forward]: ...
    def clear_all(self) -> list[CommandResult]: ...
    def detect_conflicts(self, port: int) -> list[int]: ...
    def test_connection(self, port: int, timeout: float = 3.0) -> bool: ...
    def port_map(self) -> list[PortEntry]: ...


class WslIpProvider(Protocol):
    def get_ip(self, distro: str) -> str | None: ...
    def get_all_ips(self) -> dict[str, str | None]: ...


class SshTunnelProvider(Protocol):
    def start(self, tunnel: Any) -> Any: ...
    def stop(self, tunnel: Any) -> None: ...
    def is_alive(self, tunnel: Any) -> bool: ...
    def restart(self, tunnel: Any) -> Any: ...
    def build_command(self, tunnel: Any) -> list[str]: ...
