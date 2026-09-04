"""Tests: fix metrics en import, terminal WSL por WebSocket y tunnel add/edit
con todas las opciones."""
from __future__ import annotations

import base64
import json
import os
import socket
import struct
import subprocess
import threading
import time
import urllib.error
import urllib.request

import pytest

from wsl_port import core
from wsl_port.vendor.port_forwarder.api.service import AppService


@pytest.fixture
def isolated_config(monkeypatch, tmp_path):
    from wsl_port.vendor.port_forwarder.core.config import ConfigStore
    store = ConfigStore(path=str(tmp_path / "config.json"))
    monkeypatch.setattr(core, "_pf_store", store)
    return store


@pytest.fixture
def mock_wsl_healthy(monkeypatch):
    monkeypatch.setattr(core, "wsl_health_check", lambda force=False: True)
    return monkeypatch


@pytest.fixture
def panel(mock_wsl_healthy, isolated_config):
    from wsl_port.vendor.port_forwarder.core.supervisor import Supervisor
    sup = Supervisor(isolated_config)
    p = WebPanel(sup, port=0, bind="127.0.0.1", token="test-token")
    p.start()
    base = f"http://127.0.0.1:{p.port}"
    for _ in range(50):
        try:
            urllib.request.urlopen(base + "/", timeout=1)
            break
        except Exception:
            time.sleep(0.1)
    yield p, base
    p.stop()


from wsl_port.vendor.port_forwarder.web.server import WebPanel  # noqa: E402


def _http_post_raw(url, body: bytes, ctype: str, token=None, timeout=15):
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", ctype)
    from urllib.parse import urlparse as _up; _p = _up(url); req.add_header("Origin", f"{_p.scheme}://{_p.netloc}")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


# ---------------------------------------------------------------- import fix


def test_distro_import_uses_panel_metrics(panel, isolated_config, monkeypatch):
    """Regresion: /api/v1/distro/import debe registrar el evento via
    self.panel.metrics (no self.metrics del handler -> AttributeError)."""
    _, base = panel

    calls = []

    def fake_run(args, **kwargs):
        calls.append(list(args))
        m = type("R", (), {})()
        m.returncode = 0
        m.stdout = b""
        m.stderr = b""
        return m

    monkeypatch.setattr(subprocess, "run", fake_run)

    boundary = "----wbtest"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="name"\r\n\r\nimportada-x\r\n'
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="install_dir"\r\n\r\n\r\n'
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="x.tar"\r\n\r\n'
        "TARDATA\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")
    status, raw = _http_post_raw(
        base + "/api/v1/distro/import", body,
        f"multipart/form-data; boundary={boundary}", token="test-token")
    assert status == 200
    data = json.loads(raw)
    assert data["ok"] is True, data
    assert any("import" in " ".join(c) for c in calls)
    events = panel[0].metrics.list_events(limit=10)
    assert any(e["type"] == "web_distro_import" for e in events)


# ---------------------------------------------------------------- WS helpers


class WsClient:
    def __init__(self, port: int, token: str = "test-token"):
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=5)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (
            f"GET /ws?token={token} HTTP/1.1\r\n"
            "Host: 127.0.0.1\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        ).encode()
        self.sock.sendall(req)
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise RuntimeError("handshake cerrado")
            buf += chunk
        head, rest = buf.split(b"\r\n\r\n", 1)
        assert b"101" in head.split(b"\r\n", 1)[0], head
        self._buf = rest

    def _recv_exact(self, n):
        while len(self._buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise RuntimeError("conexion cerrada")
            self._buf += chunk
        out, self._buf = self._buf[:n], self._buf[n:]
        return out

    def send_json(self, obj):
        data = json.dumps(obj).encode("utf-8")
        if len(data) > 125:
            raise ValueError("frame test demasiado largo")
        frame = bytearray([0x81, 0x80 | len(data)])  # bit mask, key = 0
        frame.extend(b"\x00\x00\x00\x00")
        frame.extend(data)
        self.sock.sendall(bytes(frame))

    def next_json(self, timeout=10.0):
        self.sock.settimeout(timeout)
        while True:
            header = self._recv_exact(2)
            opcode = header[0] & 0x0F
            length = header[1] & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._recv_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._recv_exact(8))[0]
            payload = self._recv_exact(length) if length else b""
            if opcode != 0x1:
                continue
            try:
                return json.loads(payload.decode("utf-8"))
            except ValueError:
                continue

    def wait_for(self, pred, timeout=30.0):
        deadline = time.time() + timeout
        seen = []
        while time.time() < deadline:
            try:
                msg = self.next_json(timeout=max(0.5, deadline - time.time()))
            except (RuntimeError, socket.timeout, TimeoutError):
                break
            seen.append(msg)
            if pred(msg):
                return msg
        raise AssertionError(f"no llego mensaje esperado; vistos: {seen[:6]}")

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


# ---------------------------------------------------------------- terminal


_distros = []


def _real_distros():
    global _distros
    if not _distros:
        try:
            p = subprocess.run(["wsl.exe", "--list", "--quiet"],
                               capture_output=True, timeout=10)
            out = WebPanel._decode_wsl(p.stdout)
            _distros = [x.strip() for x in out.splitlines() if x.strip()]
        except Exception:
            _distros = []
    return _distros


@pytest.mark.skipif(not _real_distros(), reason="sin WSL real")
def test_ws_terminal_roundtrip(panel):
    p, _ = panel
    distro = _real_distros()[0]
    ws = WsClient(p.port)
    try:
        ws.wait_for(lambda m: m.get("type") == "state", timeout=15)
        ws.send_json({"type": "term_start", "distro": distro})
        st = ws.wait_for(lambda m: m.get("type") == "term_status"
                         and m.get("state") == "running", timeout=60)
        assert st["distro"] == distro
        # la terminal debe abrir en el home de la distro, no en /mnt/c/...
        assert (st.get("cwd") or "").startswith("/")
        assert not (st.get("cwd") or "").lower().startswith("/mnt/c")
        ws.send_json({"type": "term_cmd", "cmd": "echo hola-terminal-test"})
        ws.wait_for(lambda m: m.get("type") == "term_out"
                    and "hola-terminal-test" in (m.get("data") or ""),
                    timeout=30)
        ex = ws.wait_for(lambda m: m.get("type") == "term_exit", timeout=30)
        assert ex["code"] == 0
        ws.send_json({"type": "term_cmd", "cmd": "false"})
        ex = ws.wait_for(lambda m: m.get("type") == "term_exit", timeout=30)
        assert ex["code"] == 1
        ws.send_json({"type": "term_stop"})
        ws.wait_for(lambda m: m.get("type") == "term_status"
                    and m.get("state") == "closed", timeout=15)
    finally:
        ws.close()


def test_ws_terminal_requires_start(panel):
    p, _ = panel
    ws = WsClient(p.port)
    try:
        ws.wait_for(lambda m: m.get("type") == "state", timeout=15)
        ws.send_json({"type": "term_cmd", "cmd": "echo x"})
        st = ws.wait_for(lambda m: m.get("type") == "term_status", timeout=10)
        assert st["state"] == "closed"
        ws.send_json({"type": "term_start", "distro": ""})
        st = ws.wait_for(lambda m: m.get("type") == "term_status"
                         and m.get("state") == "error", timeout=10)
        assert "distro" in st["message"]
    finally:
        ws.close()


# ---------------------------------------------------------------- tunnel


def _http_post(url, payload, token="test-token"):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 method="POST")
    req.add_header("Content-Type", "application/json")
    from urllib.parse import urlparse as _up; _p = _up(url); req.add_header("Origin", f"{_p.scheme}://{_p.netloc}")
    req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def test_tunnel_add_edit_all_options(panel, isolated_config):
    _, base = panel
    _http_post(base + "/api/v1/vps/add",
               {"id": "vpm", "host": "1.2.3.4", "user": "root", "port": 22})
    r = _http_post(base + "/api/v1/tunnels/add", {
        "id": "tun-modal", "vps_id": "vpm", "type": "ssh",
        "local": "127.0.0.1:9001", "remotes": ["0.0.0.0:19001", "0.0.0.0:19002"],
        "auto_start": False, "enabled": False, "health_gate": False,
        "keepalive_interval": 15, "keepalive_count": 4,
    })
    assert r["ok"] is True, r
    t = isolated_config.get_tunnel("tun-modal")
    assert t is not None
    assert t.enabled is False and t.auto_start is False
    assert t.health_gate.enabled is False
    assert t.keepalive_interval == 15 and t.keepalive_count == 4
    assert [f"{b.host}:{b.port}" for b in t.remote_binds] == \
        ["0.0.0.0:19001", "0.0.0.0:19002"]
    # edit con remotes como string (compat) + nueva lista
    r = _http_post(base + "/api/v1/tunnels/tun-modal/edit", {
        "vps_id": "vpm", "local": "127.0.0.1:9002",
        "remotes": "0.0.0.0:19003, 0.0.0.0:19004",
        "enabled": True, "keepalive_interval": 20, "keepalive_count": 5,
    })
    assert r["ok"] is True, r
    t = isolated_config.get_tunnel("tun-modal")
    assert t.enabled is True
    assert t.local_bind.port == 9002
    assert [f"{b.host}:{b.port}" for b in t.remote_binds] == \
        ["0.0.0.0:19003", "0.0.0.0:19004"]
    assert t.keepalive_interval == 20 and t.keepalive_count == 5
    # state expone todas las opciones para el modal de edicion
    req = urllib.request.Request(base + "/api/v1/state")
    req.add_header("Authorization", "Bearer test-token")
    with urllib.request.urlopen(req, timeout=15) as resp:
        st = json.loads(resp.read())
    tun = next(x for x in st["status"]["tunnels"] if x["id"] == "tun-modal")
    assert tun["enabled"] is True
    assert tun["keepalive_interval"] == 20
    assert tun["health_gate"] is False


def test_mcp_tools_have_wsl_exec():
    svc = AppService.__new__(AppService)  # sin supervisor real
    from wsl_port.vendor.port_forwarder.mcp.server import build_tools
    names = [t["name"] for t in build_tools(svc)]
    assert "wsl_exec" in names and "wsl_distros" in names


# ------------------------------------------------------ diagnostico de tunel


def _mk_tunnel(id_="tun-d", vps_id="noexiste"):
    from wsl_port.vendor.port_forwarder.core.config import Bind, Tunnel
    return Tunnel(id=id_, vps_id=vps_id,
                  local_bind=Bind(host="127.0.0.1", port=9999),
                  remote_binds=[Bind(host="0.0.0.0", port=19999)],
                  auto_start=True)


def test_classify_error_patterns():
    from wsl_port.vendor.port_forwarder.providers.ssh_tunnel_provider import SshTunnelProvider
    p = SshTunnelProvider.__new__(SshTunnelProvider)
    assert "autenticacion SSH rechazada" in p.classify_error(
        "git@vps: Permission denied (publickey,password).")
    assert p.classify_error(
        "ssh: connect to host 1.2.3.4 port 22: Connection refused"
    ).startswith("el VPS rechazo")
    assert "timeout" in p.classify_error(
        "ssh: connect to host vps.example port 22: Connection timed out")
    assert p.classify_error(
        "bind [127.0.0.1]:18097: Address already in use") \
        .startswith("el puerto remoto")
    assert "GatewayPorts" in p.classify_error(
        "Warning: remote port forwarding failed for listen port 18097")
    assert p.classify_error("algun texto inocuo") == ""


def test_failure_reason_from_log(tmp_path):
    from wsl_port.vendor.port_forwarder.providers.ssh_tunnel_provider import SshTunnelProvider
    p = SshTunnelProvider(pid_dir=tmp_path / "pid", log_dir=tmp_path / "logs")
    t = _mk_tunnel()
    (tmp_path / "logs" / "tunnel-tun-d.log").write_text(
        "OpenSSH_9.6p1 Connecting to vps port 22.\r\n"
        "git@vps: Permission denied (publickey).\r\n", encoding="utf-8")
    r = p.failure_reason(t)
    assert r and "autenticacion SSH rechazada" in r


def test_supervisor_records_reason_and_status(isolated_config):
    from wsl_port.vendor.port_forwarder.core.supervisor import Supervisor
    from wsl_port.vendor.port_forwarder.core.config import Vps
    # vps_id 'noexiste' es a proposito: el supervisor debe reportarlo como razon
    sup = Supervisor(isolated_config)
    cfg = isolated_config.cfg
    cfg.tunnels.append(_mk_tunnel())
    # caso 1: VPS inexistente -> razon sin tocar is_alive
    summary = {"tunnels": {}}
    sup._check_tunnels(isolated_config.cfg, summary)
    assert sup.tunnel_reason["tun-d"] == (
        "VPS 'noexiste' no existe en la configuracion")
    status = sup.status()
    tun = next(x for x in status["tunnels"] if x["id"] == "tun-d")
    assert tun["state"] != "running"
    assert tun["error"] == sup.tunnel_reason["tun-d"]
    # caso 2: VPS existe pero ssh cae -> start falla; el siguiente ciclo
    # (en backoff) conserva la razon del provider
    from wsl_port.vendor.port_forwarder.core.config import Vps
    sup.store.cfg.vps_list.append(Vps(id="noexiste", host="1.2.3.4", user="root"))
    sup.ssh.failure_reason = lambda t: "VPS inalcanzable (timeout de conexion)"
    sup.ssh.is_alive = lambda t: False
    sup.ssh._gate_ok = lambda t: True

    def _boom(*a, **k):
        raise RuntimeError("lanzamiento de ssh rechazado")
    sup.ssh.start = _boom
    sup._check_tunnels(isolated_config.cfg, {"tunnels": {}})
    assert sup.tunnel_reason["tun-d"] == "lanzamiento de ssh rechazado"
    sup._check_tunnels(isolated_config.cfg, {"tunnels": {}})  # backoff: no reintenta
    assert sup.tunnel_reason["tun-d"] == "VPS inalcanzable (timeout de conexion)"


def test_panel_diag_and_log_endpoints(panel, isolated_config, monkeypatch):
    _, base = panel
    p = panel[0]
    from wsl_port.vendor.port_forwarder.core.config import Vps
    p.supervisor.store.add_vps(Vps(id="vps-x", host="1.2.3.4", user="root"))
    p.supervisor.store.add_tunnel(_mk_tunnel(vps_id="vps-x"))
    monkeypatch.setattr(type(p.supervisor.ssh), "is_alive",
                        lambda self, t: False)
    monkeypatch.setattr(type(p.supervisor.ssh), "_gate_ok",
                        lambda self, t: True)
    monkeypatch.setattr(type(p.supervisor.ssh), "failure_reason",
                        lambda self, t: "el VPS rechazo la conexion (puerto SSH cerrado o firewall)")
    req = urllib.request.Request(base + "/api/v1/tunnels/tun-d/diag")
    req.add_header("Authorization", "Bearer test-token")
    with urllib.request.urlopen(req, timeout=10) as resp:
        d = json.loads(resp.read())
    assert d["ok"] is True and d["alive"] is False
    assert "rechazo la conexion" in d["reason"]
    assert d["vps_exists"] is True
    req = urllib.request.Request(base + "/api/v1/tunnels/tun-d/log")
    req.add_header("Authorization", "Bearer test-token")
    with urllib.request.urlopen(req, timeout=10) as resp:
        l = json.loads(resp.read())
    assert l["ok"] is True
    assert "log" in l


# ------------------------------------------------- MCP transporte HTTP (8796)


def _mcp_http_post(url, obj, token=None, timeout=10):
    data = json.dumps(obj).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    if token:
        req.add_header('Authorization', f'Bearer {token}')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def test_mcp_http_transport_auth_and_tools(isolated_config):
    from wsl_port.vendor.port_forwarder.api.service import AppService
    from wsl_port.vendor.port_forwarder.mcp.server import McpHttpServer
    svc = AppService(isolated_config)
    srv = McpHttpServer(service=svc, host='127.0.0.1', port=0, token='tok123')
    srv.start()
    try:
        url = f'http://127.0.0.1:{srv.port}/mcp'
        # sin token -> 401
        code, _ = _mcp_http_post(url, {'jsonrpc': '2.0', 'id': 1,
                                       'method': 'tools/list'})
        assert code == 401
        # con token -> lista de tools incluye las de terminal WSL
        code, resp = _mcp_http_post(url, {'jsonrpc': '2.0', 'id': 1,
                                          'method': 'tools/list'}, token='tok123')
        assert code == 200
        names = [t['name'] for t in resp['result']['tools']]
        assert 'wsl_exec' in names and 'wsl_distros' in names
        # initialize handshake
        code, resp = _mcp_http_post(url, {'jsonrpc': '2.0', 'id': 2,
                                          'method': 'initialize',
                                          'params': {}}, token='tok123')
        assert code == 200 and 'protocolVersion' in resp['result']
        # health publico sin auth
        with urllib.request.urlopen(f'http://127.0.0.1:{srv.port}/health',
                                    timeout=10) as r:
            h = json.loads(r.read())
        assert h['ok'] is True and h['tools'] >= 30
    finally:
        srv.stop()


def test_supervisor_autostarts_mcp_http(isolated_config):
    from wsl_port.vendor.port_forwarder.core.supervisor import Supervisor
    sup = Supervisor(isolated_config)
    mcp = isolated_config.cfg.mcp
    mcp.enabled = True
    mcp.transport = 'http'
    mcp.port = 0          # efimero en tests
    mcp.token_required = False
    mcp.token = ''
    try:
        sup._sync_mcp_http()
        assert sup._mcp_http is not None and sup._mcp_http.running
        with urllib.request.urlopen(
                f'http://127.0.0.1:{sup._mcp_http.port}/health', timeout=10) as r:
            assert json.loads(r.read())['ok'] is True
        # deshabilitar -> se detiene solo
        mcp.enabled = False
        sup._sync_mcp_http()
        assert sup._mcp_http is None
    finally:
        if sup._mcp_http is not None:
            sup._mcp_http.stop()


# --------------------------- sincronizacion Ajustes MCP <-> tunel mcp-to-vps


def test_mcp_settings_syncs_tunnel(panel, isolated_config, monkeypatch):
    _, base = panel
    p = panel[0]
    from wsl_port.vendor.port_forwarder.core.config import Vps
    p.supervisor.store.add_vps(Vps(id="vps-canada", host="1.2.3.4", user="root"))
    started, stopped = [], []
    monkeypatch.setattr(type(p.supervisor.ssh), "start",
        lambda self, t, v=None: started.append(
            (t.local_bind.port, t.remote_binds[0].port, t.vps_id)))
    monkeypatch.setattr(type(p.supervisor.ssh), "stop",
        lambda self, t: stopped.append(t.id))
    monkeypatch.setattr(type(p.supervisor.ssh), "is_alive", lambda self, t: False)
    monkeypatch.setattr(type(p.supervisor), "_sync_mcp_http", lambda self: None)

    def settings(**over):
        body = {"enabled": True, "transport": "http", "port": 8796,
                "token_required": True, "token": "tok",
                "vps_export_enabled": True,
                "vps_target_host": "vps-canada",
                "vps_target_port": 55872}
        body.update(over)
        return _http_post(base + "/api/v1/mcp/settings", body)

    r = settings()
    assert r["ok"], r
    t = isolated_config.get_tunnel("mcp-to-vps")
    assert t is not None
    assert t.local_bind.port == 8796 and t.remote_binds[0].port == 55872
    assert t.vps_id == "vps-canada" and t.auto_start and t.health_gate.enabled
    assert started[-1] == (8796, 55872, "vps-canada")

    # cambiar puerto MCP -> el tunel se actualiza y se detiene el proceso viejo
    r = settings(port=9999)
    assert r["ok"], r
    t = isolated_config.get_tunnel("mcp-to-vps")
    assert t.local_bind.port == 9999
    assert "mcp-to-vps" in stopped
    assert started[-1] == (9999, 55872, "vps-canada")

    # 'Aplicar' no duplica ni reinicia si ya esta igual y vivo
    monkeypatch.setattr(type(p.supervisor.ssh), "is_alive", lambda self, t: True)
    before_start = len(started)
    r = _http_post(base + "/api/v1/mcp/apply", {})
    assert r["ok"] and r["tunnel"] == "mcp-to-vps"
    assert len(started) == before_start

    # desactivar export -> tunel detenido y eliminado
    r = settings(vps_export_enabled=False)
    assert r["ok"], r
    assert isolated_config.get_tunnel("mcp-to-vps") is None
    assert stopped.count("mcp-to-vps") >= 2

    # VPS inexistente -> error claro, no rompe nada
    r = settings(vps_export_enabled=True, vps_target_host="no-existe")
    assert r["ok"] is False and "no existe" in (r.get("error") or "")
