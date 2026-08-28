"""Tests del panel web local (M7, P2) con TestClient y providers mockeados."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from src.core.config import ConfigStore
from src.core.event_bus import EventBus
from src.core.metrics_store import MetricsStore
from src.providers.base import CommandResult, Distro, DistroMetrics
from src.web.web_app import create_web_app


def _ctx(tmp_path):
    store = ConfigStore(tmp_path / "config.json")
    cfg = store.load()
    wsl = MagicMock()
    wsl.list_distros.return_value = [Distro(name="ubuntu-dev", state="Running", version=2)]
    wsl.get_ip.return_value = "172.18.0.2"
    wsl.metrics.return_value = DistroMetrics(name="ubuntu-dev", running=True, ip="172.18.0.2", ram_total_mb=8192, ram_used_mb=2048, ram_percent=25.0)
    wsl.start.return_value = CommandResult(ok=True)
    wsl.stop.return_value = CommandResult(ok=True)
    resources = MagicMock()
    resources.get_metrics.return_value = [wsl.metrics.return_value]
    ms = MetricsStore(tmp_path / "m.db")
    bus = EventBus()
    return SimpleNamespace(store=store, config=cfg, metrics=ms, bus=bus, wsl=wsl, resources=resources)


def _authed_client(tmp_path):
    """Create a TestClient with a valid session cookie."""
    app = create_web_app(_ctx(tmp_path))
    token = app.state.web_token
    client = TestClient(app)
    # Authenticate by POSTing to /login, then carry the cookie
    r = client.post("/login", data={"token": token}, follow_redirects=False)
    # After login, cookies should be set on the client
    assert client.cookies.get("session") == token, "Login did not set session cookie"
    return client


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------

def test_login_page_unauthenticated(tmp_path):
    """GET /login should be accessible without auth."""
    client = TestClient(create_web_app(_ctx(tmp_path)))
    r = client.get("/login")
    assert r.status_code == 200
    assert "token de acceso" in r.text


def test_login_redirects_root_unauthenticated(tmp_path):
    """GET / should redirect to /login when not authenticated."""
    client = TestClient(create_web_app(_ctx(tmp_path)))
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 302
    assert "/login" in r.headers["location"]


def test_api_returns_401_without_session(tmp_path):
    """API endpoints should return 401 without session cookie."""
    client = TestClient(create_web_app(_ctx(tmp_path)))
    r = client.get("/api/status")
    assert r.status_code == 401


def test_login_correct_token_sets_cookie(tmp_path):
    """POST /login with correct token sets session cookie and redirects."""
    app = create_web_app(_ctx(tmp_path))
    token = app.state.web_token
    client = TestClient(app)
    r = client.post("/login", data={"token": token}, follow_redirects=False)
    assert r.status_code == 302
    assert client.cookies.get("session") == token


def test_login_wrong_token_shows_error(tmp_path):
    """POST /login with wrong token shows error message."""
    client = TestClient(create_web_app(_ctx(tmp_path)))
    r = client.post("/login", data={"token": "wrong-token"})
    assert r.status_code == 200
    assert "Token incorrecto" in r.text


# ---------------------------------------------------------------------------
# Authenticated endpoint tests
# ---------------------------------------------------------------------------

def test_index_html(tmp_path):
    client = _authed_client(tmp_path)
    r = client.get("/")
    assert r.status_code == 200
    assert "WSL Manager" in r.text
    assert "/api/status" in r.text


def test_api_status(tmp_path):
    client = _authed_client(tmp_path)
    r = client.get("/api/status")
    assert r.status_code == 200
    data = r.json()
    assert data["distros"][0]["name"] == "ubuntu-dev"
    assert data["distros"][0]["running"] is True
    assert data["distros"][0]["ram_percent"] == 25.0


def test_api_metrics(tmp_path):
    client = _authed_client(tmp_path)
    r = client.get("/api/metrics")
    assert r.status_code == 200
    assert r.json()["metrics"][0]["ram_used_mb"] == 2048


def test_api_actions(tmp_path):
    client = _authed_client(tmp_path)
    assert client.post("/api/distros/ubuntu-dev/start").status_code == 200
    assert client.post("/api/distros/ubuntu-dev/stop").status_code == 200
    assert client.post("/api/distros/ubuntu-dev/restart").status_code == 200
    assert client.post("/api/shutdown").status_code == 200


def test_api_alerts_and_events(tmp_path):
    ctx = _ctx(tmp_path)
    ctx.metrics.log_event("distro_start", "ubuntu-dev", "iniciada")
    ctx.metrics.add_alert("memory", "RAM al 90%", "warning", "ubuntu-dev")
    app = create_web_app(ctx)
    token = app.state.web_token
    client = TestClient(app)
    client.post("/login", data={"token": token}, follow_redirects=False)
    assert client.get("/api/alerts").json()["alerts"][0]["tipo"] == "memory"
    assert client.get("/api/events").json()["events"][0]["type"] == "distro_start"


def test_web_token_exposed_on_app_state(tmp_path):
    """The generated token should be stored on app.state.web_token."""
    app = create_web_app(_ctx(tmp_path))
    assert hasattr(app.state, "web_token")
    assert len(app.state.web_token) > 10
