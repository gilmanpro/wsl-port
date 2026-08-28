"""SshTunnelProvider: tunnels SSH reversos hacia VPS.

Comando:
  ssh -i <identity> -N -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \\
      -o ExitOnForwardFailure=yes -R 0.0.0.0:80:127.0.0.1:3000 \\
      -R 0.0.0.0:443:127.0.0.1:3000 user@vps

Adaptado desde port-forwarder-app/src/providers/ssh_tunnel_provider.py
para la app unificada wsl-manager-gui.
"""

from __future__ import annotations

import json as _json
import os
import re
import signal
import socket
import subprocess
import time
from pathlib import Path
from typing import Any

from src.core.forward_config import Tunnel, Vps
from src.utils import subprocess_forwarding as sp

_SSH_CMD_PATTERN = re.compile(r"-R\s+\S+:\d+:\S+:\d+")


class SshTunnelError(Exception):
    pass


class SshTunnelProvider:
    def __init__(
        self,
        ssh_exe: str | None = None,
        pid_dir: str | Path | None = None,
        log_dir: str | Path | None = None,
    ) -> None:
        self.ssh_exe = ssh_exe or r"C:\Windows\System32\OpenSSH\ssh.exe"
        from src.utils import forward_paths as paths

        self.pid_dir = Path(pid_dir) if pid_dir else paths.data_dir() / "tunnels"
        self.pid_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir = Path(log_dir) if log_dir else paths.logs_dir()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._procs: dict[str, subprocess.Popen] = {}

    # -- construccion del comando ---------------------------------------------

    def build_command(self, tunnel: Tunnel, vps: Vps | None = None) -> list[str]:
        if tunnel.type != "ssh":
            raise SshTunnelError(
                f"tunnel '{tunnel.id}': tipo '{tunnel.type}' no soportado (solo ssh)"
            )
        if vps is None:
            raise SshTunnelError(f"tunnel '{tunnel.id}': VPS desconocido")

        cmd = [
            self.ssh_exe,
            "-i", vps.identity_file or os.path.expanduser("~/.ssh/id_ed25519"),
            "-N",
            "-o", f"ServerAliveInterval={tunnel.keepalive_interval}",
            "-o", f"ServerAliveCountMax={tunnel.keepalive_count}",
            "-o", "ExitOnForwardFailure=yes",
            "-o", "StrictHostKeyChecking=accept-new",
            "-o", "ConnectTimeout=10",
        ]
        if tunnel.jump:  # multi-hop
            cmd += ["-o", f"ProxyJump={tunnel.jump}"]
        for b in tunnel.remote_binds:
            cmd += ["-R", f"{b.host}:{b.port}:{tunnel.ssh_dest}"]
        cmd += [f"{vps.user}@{vps.host}", "-p", str(vps.port)]
        return cmd

    # -- ciclo de vida --------------------------------------------------------

    def _pidfile(self, tunnel_id: str) -> Path:
        return self.pid_dir / f"{tunnel_id}.pid"

    def _logfile(self, tunnel_id: str) -> Path:
        return self.log_dir / f"tunnel-{tunnel_id}.log"

    def start(self, tunnel: Tunnel, vps: Vps | None = None) -> subprocess.Popen:
        cmd = self.build_command(tunnel, vps)
        logf = open(self._logfile(tunnel.id), "ab", buffering=0)
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=logf,
                stderr=logf,
                stdin=subprocess.DEVNULL,
                creationflags=sp.CREATE_NO_WINDOW,
            )
        except OSError as e:
            logf.close()
            raise SshTunnelError(f"no se pudo lanzar ssh: {e}") from e
        self._procs[tunnel.id] = proc
        self._pidfile(tunnel.id).write_text(str(proc.pid), encoding="utf-8")
        return proc

    def stop(self, tunnel: Tunnel) -> None:
        proc = self._procs.pop(tunnel.id, None)
        pid = self._read_pid(tunnel.id)
        if proc is not None and proc.poll() is None:
            self._kill(proc)
        elif pid:
            # Proceso huerfano (supervisor reiniciado): matar por PID.
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
        # Fallback: matar cualquier ssh con este patron -R (duplicados).
        self._kill_by_pattern(tunnel)
        self._pidfile(tunnel.id).unlink(missing_ok=True)

    def _kill(self, proc: subprocess.Popen) -> None:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except (subprocess.TimeoutExpired, OSError):
            try:
                proc.kill()
            except OSError:
                pass

    def _read_pid(self, tunnel_id: str) -> int | None:
        pf = self._pidfile(tunnel_id)
        if not pf.exists():
            return None
        try:
            return int(pf.read_text(encoding="utf-8").strip())
        except ValueError:
            return None

    def _kill_by_pattern(self, tunnel: Tunnel) -> None:
        """Mata procesos ssh.exe cuya linea de comandos contiene -R de este
        tunnel (destino local + uno de los puertos remotos)."""
        try:
            proc = sp.run(
                ["powershell.exe", "-NoProfile", "-Command",
                 "Get-CimInstance Win32_Process -Filter \"Name='ssh.exe'\" | "
                 "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"],
                timeout=30.0,
                check=False,
            )
        except OSError:
            return
        if proc.returncode != 0 or not proc.stdout.strip():
            return

        try:
            data = _json.loads(proc.stdout)
        except _json.JSONDecodeError:
            return
        items = data if isinstance(data, list) else [data]
        targets = {b.port for b in tunnel.remote_binds}
        for item in items:
            cl = str(item.get("CommandLine") or "")
            pid = item.get("ProcessId")
            if "-R " not in cl or not pid:
                continue
            if any(f":{p}:" in cl for p in targets) and \
               f":{tunnel.local_bind.port}:" in cl:
                try:
                    os.kill(int(pid), signal.SIGTERM)
                except (OSError, ValueError):
                    pass

    # -- estado ---------------------------------------------------------------

    def is_alive(self, tunnel: Tunnel) -> bool:
        """Proceso vivo (+ health gate del servicio local)."""
        proc = self._procs.get(tunnel.id)
        if proc is not None:
            if proc.poll() is None:
                return self._gate_ok(tunnel)
            self._procs.pop(tunnel.id, None)
            return False
        pid = self._read_pid(tunnel.id)
        if pid is None:
            return False
        alive = self._pid_alive(pid)
        if alive:
            return self._gate_ok(tunnel)
        return False

    def _pid_alive(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def _gate_ok(self, tunnel: Tunnel) -> bool:
        """Health gate: test TCP al local_bind; sin servicio no cuenta vivo."""
        if not tunnel.health_gate.enabled:
            return True
        try:
            with socket.create_connection(
                (tunnel.local_bind.host, tunnel.local_bind.port), timeout=2.0
            ):
                return True
        except OSError:
            return False

    def restart(self, tunnel: Tunnel, vps: Vps | None = None) -> subprocess.Popen:
        self.stop(tunnel)
        time.sleep(0.5)
        return self.start(tunnel, vps)

    def latency(self, tunnel: Tunnel, vps: Vps | None = None) -> float | None:
        """Latencia SSH al VPS: tiempo de handshake con -o BatchMode."""
        try:
            t0 = time.monotonic()
            sp.run(
                self.build_command(tunnel, vps)
                + ["-o", "BatchMode=yes", "-o", "ExitOnForwardFailure=no",
                   "true"],
                timeout=15.0,
                check=False,
            )
            return round((time.monotonic() - t0) * 1000, 1)
        except (OSError, subprocess.TimeoutExpired):
            return None
