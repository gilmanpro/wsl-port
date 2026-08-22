"""Tests del flujo 'Publicar en Internet' de wsl-port."""
from __future__ import annotations

from unittest import mock

import pytest

from wsl_port import core


def test_tunnel_id_sanitiza():
    assert core.tunnel_id_for("Debian", 9000) == "pub-debian-9000"
    assert core.tunnel_id_for("ubuntu dev", 80) == "pub-ubuntu-dev-80"


def test_check_local_ok_y_falla():
    with mock.patch("socket.create_connection") as cc:
        cc.return_value.__enter__ = lambda s: s
        assert core.check_local(9000)
        cc.side_effect = OSError("no")
        assert not core.check_local(9000)


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
    added = []

    def fake_add_tunnel(tun_id, vps_id, local_host, local_port, remote_host="0.0.0.0", remote_port=80, tunnel_type="ssh"):
        added.append({"id": tun_id, "vps_id": vps_id, "local_host": local_host,
                      "local_port": local_port, "remote_host": remote_host,
                      "remote_port": remote_port})
        return {"ok": True}

    def fake_start_tunnel(tun_id):
        return {"ok": True}

    monkeypatch.setattr("wsl_port.core.add_tunnel", fake_add_tunnel)
    monkeypatch.setattr("wsl_port.core.start_tunnel", fake_start_tunnel)
    return added


def test_publish_crea_y_arranca_tunel(env, monkeypatch):
    monkeypatch.setattr("wsl_port.core.check_local", lambda p, host="127.0.0.1", timeout=5.0: True)
    r = core.publish("Debian", 9000, "vps1", 18097)
    assert r["tunnel_id"] == "pub-debian-9000"
    assert r["public_url"] == "http://VPS_IP_REDACTED:18097"
    assert len(env) == 1
    assert env[0]["local_port"] == 9000
    assert env[0]["remote_port"] == 18097


def test_publish_distro_inexistente(env, monkeypatch):
    monkeypatch.setattr("wsl_port.core.check_local", lambda *a, **k: True)
    with pytest.raises(ValueError, match="no encontrada"):
        core.publish("NoExiste", 9000, "vps1", 18097)


def test_publish_vps_inexistente(env, monkeypatch):
    monkeypatch.setattr("wsl_port.core.check_local", lambda *a, **k: True)
    with pytest.raises(ValueError, match="VPS"):
        core.publish("Debian", 9000, "vps-zzz", 18097)


def test_publish_sin_servicio_local(env, monkeypatch):
    monkeypatch.setattr("wsl_port.core.check_local", lambda *a, **k: False)
    with pytest.raises(ValueError, match="no hay servicio"):
        core.publish("Debian", 9000, "vps1", 18097)


def test_unpublish(env):
    monkeypatch_calls = []

    def fake_stop(tid):
        monkeypatch_calls.append(("stop", tid))
        return {"ok": True}

    def fake_remove(tid):
        monkeypatch_calls.append(("remove", tid))
        return {"ok": True}

    with mock.patch("wsl_port.core.stop_tunnel", fake_stop), \
         mock.patch("wsl_port.core.remove_tunnel", fake_remove):
        assert core.unpublish("pub-debian-9000")
        assert ("stop", "pub-debian-9000") in monkeypatch_calls
        assert ("remove", "pub-debian-9000") in monkeypatch_calls
