"""Tests del flujo 'Publicar en Internet' de wsl-port."""
from __future__ import annotations

from unittest import mock

import pytest

from wsl_port import publish as pub


def _proc(stdout: str = "", code: int = 0):
    p = mock.Mock()
    p.stdout = stdout
    p.stderr = ""
    p.returncode = code
    return p


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setattr(
        "wsl_port.core.distros",
        lambda: [{"name": "Debian", "state": "Running", "running": True, "ip": "172.26.159.208"}],
    )
    monkeypatch.setattr(
        "wsl_port.core.vps_list",
        lambda: [{"id": "vps1", "host": "VPS_IP_REDACTED", "user": "debian", "port": 10000}],
    )
    monkeypatch.setattr("wsl_port.core.tunnels", lambda: [])
    calls: list[list[str]] = []

    def fake_run_pf(args, timeout=120):
        calls.append(list(args))
        return _proc(stdout="{}")

    monkeypatch.setattr("wsl_port.core.run_pf", fake_run_pf)
    return calls


def test_tunnel_id_sanitiza():
    assert pub.tunnel_id("Debian", 9000) == "pub-debian-9000"
    assert pub.tunnel_id("ubuntu dev", 80) == "pub-ubuntu-dev-80"


def test_check_local_ok_y_falla():
    import socket

    with mock.patch("socket.create_connection") as cc:
        cc.return_value.__enter__ = lambda s: s
        assert pub.check_local(9000)
        cc.side_effect = OSError("no")
        assert not pub.check_local(9000)


def test_publish_crea_y_arranca_tunel(env, monkeypatch):
    monkeypatch.setattr("wsl_port.publish.check_local", lambda p, host="127.0.0.1", timeout=5.0: True)
    r = pub.publish("Debian", 9000, "vps1", 18097)
    assert r["tunnel_id"] == "pub-debian-9000"
    assert r["public_url"] == "http://VPS_IP_REDACTED:18097"
    add = [c for c in env if c[0] == "tunnels" and c[1] == "add"]
    start = [c for c in env if c[0] == "tunnels" and c[1] == "start"]
    assert add and "--local" in add[0] and "127.0.0.1:9000" in add[0]
    assert "--remote" in add[0] and "0.0.0.0:18097" in add[0]
    assert start and start[0][2] == "pub-debian-9000"


def test_publish_distro_inexistente(env, monkeypatch):
    monkeypatch.setattr("wsl_port.publish.check_local", lambda *a, **k: True)
    with pytest.raises(ValueError, match="no encontrada"):
        pub.publish("NoExiste", 9000, "vps1", 18097)


def test_publish_vps_inexistente(env, monkeypatch):
    monkeypatch.setattr("wsl_port.publish.check_local", lambda *a, **k: True)
    with pytest.raises(ValueError, match="VPS"):
        pub.publish("Debian", 9000, "vps-zzz", 18097)


def test_publish_sin_servicio_local(env, monkeypatch):
    monkeypatch.setattr("wsl_port.publish.check_local", lambda *a, **k: False)
    with pytest.raises(ValueError, match="no hay servicio"):
        pub.publish("Debian", 9000, "vps1", 18097)


def test_unpublish(env):
    assert pub.unpublish("pub-debian-9000")
    assert env[-1][:2] == ["tunnels", "remove"]