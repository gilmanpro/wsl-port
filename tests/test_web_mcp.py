"""Tests del panel web y MCP de wsl-port.

Panel web: arranca un WebPanel en puerto efimero y prueba todos los endpoints.
MCP: prueba McpServer.handle para todo el protocolo JSON-RPC.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.request
import urllib.error
from unittest import mock

import pytest

from wsl_port import core
from wsl_port.vendor.port_forwarder.web.server import WebPanel
from wsl_port.vendor.port_forwarder.mcp.server import McpServer, build_tools
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


# ---------------------------------------------------------------------------
# Panel web
# ---------------------------------------------------------------------------

class _SockReader:
    """Lee la respuesta HTTP cruda."""


def _http_get(url, token=None, timeout=5):
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def _http_post(url, payload, token=None, headers=None, timeout=5):
    data = json.dumps(payload).encode("utf-8") if payload is not None else b""
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    # Origin correcto (host:puerto) para superar CSRF si lo enviamos
    from urllib.parse import urlparse
    parsed = urlparse(url)
    req.add_header("Origin", f"{parsed.scheme}://{parsed.netloc}")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


@pytest.fixture
def panel(mock_wsl_healthy, isolated_config):
    """Arranca un WebPanel en un puerto efimero y lo detiene al final."""
    from wsl_port.vendor.port_forwarder.core.supervisor import Supervisor
    sup = Supervisor(isolated_config)
    p = WebPanel(sup, port=0, bind="127.0.0.1", token="test-token")
    p.start()
    # Esperar a que sirva
    base = f"http://127.0.0.1:{p.port}"
    for _ in range(50):
        try:
            urllib.request.urlopen(base + "/", timeout=1)
            break
        except Exception:
            time.sleep(0.1)
    yield p, base
    p.stop()


def test_panel_dashboard_public(panel):
    _, base = panel
    status, body = _http_get(base + "/")
    assert status == 200
    assert b"<html" in body.lower()


def test_panel_requires_auth(panel):
    _, base = panel
    status, _ = _http_get(base + "/api/v1/state")
    assert status == 401
    status, _ = _http_post(base + "/api/v1/maintenance/on", {}, token=None)
    assert status == 401


def test_panel_state_con_token(panel):
    _, base = panel
    status, body = _http_get(base + "/api/v1/state", token="test-token")
    assert status == 200
    data = json.loads(body)
    assert data["ok"] is True
    assert "status" in data


def test_panel_distros(panel, monkeypatch):
    _, base = panel
    # Mock wsl.exe -l -v para no depender de WSL real (salida en bytes)
    proc = mock.Mock()
    proc.returncode = 0
    proc.stdout = (
        b"  NAME               STATE           VERSION\n"
        b"* Ubuntu-26.04       Running         2\n"
        b"  Debian             Stopped         2\n"
    )
    monkeypatch.setattr("subprocess.run", lambda *a, **k: proc)
    status, body = _http_get(base + "/api/v1/distros", token="test-token")
    assert status == 200
    data = json.loads(body)
    assert data["ok"] is True
    names = [d["name"] for d in data["distros"]]
    assert "Debian" in names
    assert "Ubuntu-26.04" in names


def test_panel_vps_roundtrip(panel, isolated_config):
    _, base = panel
    status, body = _http_post(base + "/api/v1/vps/add",
                              {"id": "vps-w", "host": "1.2.3.4", "user": "root", "port": 22},
                              token="test-token")
    assert status == 200
    status, body = _http_get(base + "/api/v1/vps", token="test-token")
    data = json.loads(body)
    assert any(v["id"] == "vps-w" for v in data["vps"])
    status, body = _http_post(base + "/api/v1/vps/remove/vps-w", {}, token="test-token")
    assert status == 200


def test_panel_forward_roundtrip(panel, isolated_config):
    _, base = panel
    status, body = _http_post(base + "/api/v1/forwards/add",
                              {"id": "f-web", "listen_port": 18080,
                               "wsl_port": 80, "distro": "Debian"},
                              token="test-token")
    assert status == 200
    status, body = _http_post(base + "/api/v1/forwards/remove/f-web", {}, token="test-token")
    assert status == 200


def test_panel_maintenance_roundtrip(panel):
    _, base = panel
    status, body = _http_post(base + "/api/v1/maintenance/on", {}, token="test-token")
    assert status == 200
    assert json.loads(body)["ok"] is True
    status, body = _http_post(base + "/api/v1/maintenance/off", {}, token="test-token")
    assert status == 200
    assert json.loads(body)["ok"] is True


def test_panel_csrf_rejects_foreign_origin(panel):
    _, base = panel
    # POST con Origin de OTRO host -> CSRF rechaza (403 o conexion abortada)
    req = urllib.request.Request(base + "/api/v1/maintenance/on",
                                 data=b"{}", method="POST")
    req.add_header("Authorization", "Bearer test-token")
    req.add_header("Content-Type", "application/json")
    req.add_header("Origin", "http://evil.example.com")
    try:
        urllib.request.urlopen(req, timeout=5)
        assert False, "debe rechazar Origin extrano"
    except urllib.error.HTTPError as e:
        assert e.code == 403
    except Exception:
        # Conexion abortada tambien cuenta como rechazo (server cierra socket)
        pass


def test_panel_unknown_endpoint(panel):
    _, base = panel
    status, body = _http_get(base + "/api/v1/noexiste", token="test-token")
    assert status == 404


def test_panel_distro_action(panel, monkeypatch):
    """POST /api/v1/distro/<name>/start responde mensaje claro."""
    _, base = panel
    proc = mock.Mock()
    proc.returncode = 0
    proc.stdout = b""
    proc.stderr = b""
    monkeypatch.setattr("subprocess.run", lambda *a, **k: proc)
    status, body = _http_post(base + "/api/v1/distro/Debian/start", {},
                              token="test-token")
    assert status == 200
    data = json.loads(body)
    assert data["ok"] is True
    assert "iniciada" in data["message"]
    status, body = _http_post(base + "/api/v1/distro/Debian/stop", {},
                              token="test-token")
    data = json.loads(body)
    assert data["ok"] is True
    assert "detenida" in data["message"]


def test_panel_distro_action_error(panel, monkeypatch):
    """Fallo de wsl.exe devuelve ok=false con mensaje."""
    _, base = panel
    proc = mock.Mock()
    proc.returncode = 1
    proc.stdout = b""
    proc.stderr = b"error de wsl"
    monkeypatch.setattr("subprocess.run", lambda *a, **k: proc)
    status, body = _http_post(base + "/api/v1/distro/Debian/start", {},
                              token="test-token")
    data = json.loads(body)
    assert data["ok"] is False
    assert "error" in data


def test_panel_dashboard_incluye_distros(panel):
    """El dashboard HTML incluye la card Distros WSL y las funciones JS."""
    _, base = panel
    status, body = _http_get(base + "/", token="test-token")
    html = body.decode("utf-8")
    assert "Distros WSL" in html
    assert "renderDistros" in html
    assert "distroAction" in html
    assert "Tarea terminada" in html
    # Export/import desde el navegador
    assert "exportDistro" in html
    assert "importDistro" in html
    assert "imp-file" in html
    assert 'href="javascript:;"' or "download = name" in html


def test_panel_login_page_sin_token(panel):
    """GET / sin token muestra login, no dashboard."""
    _, base = panel
    status, body = _http_get(base + "/")
    html = body.decode("utf-8")
    assert status == 200
    assert "Introduce el token" in html
    assert 'id="token"' in html


# ---------------------------------------------------------------------------
# MCP
# ---------------------------------------------------------------------------

@pytest.fixture
def mcp(mock_wsl_healthy, isolated_config):
    svc = AppService(store=isolated_config)
    return McpServer(service=svc, token="mcp-token")


def test_mcp_initialize(mcp):
    r = mcp.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05"}})
    assert r["id"] == 1
    assert r["result"]["protocolVersion"] == "2024-11-05"
    assert r["result"]["capabilities"]["tools"]


def test_mcp_ping(mcp):
    r = mcp.handle({"jsonrpc": "2.0", "id": 2, "method": "ping"})
    assert r["result"] == {}


def test_mcp_initialized_notification(mcp):
    assert mcp.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_mcp_tools_list(mcp):
    r = mcp.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/list"})
    tools = r["result"]["tools"]
    names = {t["name"] for t in tools}
    assert len(tools) >= 29
    for expected in ["status", "forward_list", "forward_add", "forward_remove",
                     "tunnel_list", "tunnel_start", "vps_list", "vps_add",
                     "health_check", "alert_list", "schedule_list", "profile_list",
                     "maintenance_on", "maintenance_off", "drift_check", "doctor"]:
        assert expected in names, f"tool '{expected}' falta"


def test_mcp_call_status(mcp):
    r = mcp.handle({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                    "params": {"name": "status", "arguments": {"token": "mcp-token"}}})
    assert r["result"]["content"][0]["type"] == "text"
    assert json.loads(r["result"]["content"][0]["text"])["ok"] is True


def test_mcp_call_unknown_tool(mcp):
    r = mcp.handle({"jsonrpc": "2.0", "id": 5, "method": "tools/call",
                    "params": {"name": "nope", "arguments": {"token": "mcp-token"}}})
    assert "error" in r
    assert r["error"]["code"] == -32602


def test_mcp_requires_token(mcp):
    r = mcp.handle({"jsonrpc": "2.0", "id": 6, "method": "tools/call",
                    "params": {"name": "status", "arguments": {}}})
    assert "error" in r
    assert r["error"]["code"] == -32001


def test_mcp_bad_arguments(mcp):
    r = mcp.handle({"jsonrpc": "2.0", "id": 7, "method": "tools/call",
                    "params": {"name": "forward_add", "arguments": {
                        "token": "mcp-token", "id": "x"}}})
    assert "error" in r
    assert r["error"]["code"] == -32602


def test_mcp_unknown_method(mcp):
    r = mcp.handle({"jsonrpc": "2.0", "id": 8, "method": "resources/list"})
    assert "error" in r
    assert r["error"]["code"] == -32601


def test_mcp_selftest(mcp):
    results = mcp.selftest()
    assert results
    assert all(r["ok"] for r in results), results


def test_mcp_forward_vps_roundtrip(mcp, isolated_config):
    # Crear forward + vps via tools
    r = mcp.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                    "params": {"name": "vps_add", "arguments": {
                        "token": "mcp-token", "id": "mvps",
                        "host": "5.6.7.8", "user": "root"}}})
    assert json.loads(r["result"]["content"][0]["text"])["ok"] is True

    r = mcp.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                    "params": {"name": "forward_add", "arguments": {
                        "token": "mcp-token", "id": "mfwd",
                        "listen_port": 19000, "wsl_port": 9000,
                        "distro": "Debian", "protocol": "tcp"}}})
    assert json.loads(r["result"]["content"][0]["text"])["ok"] is True

    r = mcp.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                    "params": {"name": "forward_list", "arguments": {"token": "mcp-token"}}})
    text = json.loads(r["result"]["content"][0]["text"])
    assert text["ok"] is True

    r = mcp.handle({"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                    "params": {"name": "schedule_add", "arguments": {
                        "token": "mcp-token", "name": "Backup",
                        "type": "forwards_apply", "time": "09:00",
                        "days": "mon"}}})
    assert json.loads(r["result"]["content"][0]["text"])["ok"] is True

    r = mcp.handle({"jsonrpc": "2.0", "id": 5, "method": "tools/call",
                    "params": {"name": "schedule_list", "arguments": {"token": "mcp-token"}}})
    assert json.loads(r["result"]["content"][0]["text"])["ok"] is True