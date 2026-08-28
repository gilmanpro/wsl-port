"""Tests del MetricsStore (SQLite)."""
from __future__ import annotations

from src.core.metrics_store import MetricsStore


def test_insert_and_query(tmp_path):
    m = MetricsStore(tmp_path / "m.db")
    m.log_event("distro_start", "ubuntu-dev", "iniciada")
    m.insert_metric("ubuntu-dev", "Running", 2048, 25.0, "172.18.0.2")
    m.add_alert("memory", "RAM al 90%", "warning", "ubuntu-dev")

    events = m.list_events()
    assert events[0]["type"] == "distro_start"
    assert events[0]["distro"] == "ubuntu-dev"

    metrics = m.list_metrics()
    assert metrics[0]["ram_mb"] == 2048
    assert metrics[0]["ram_percent"] == 25.0

    alerts = m.list_alerts()
    assert alerts[0]["tipo"] == "memory"
    assert alerts[0]["estado"] == "open"

    m.resolve_alerts("memory", "ubuntu-dev")
    assert m.list_alerts()[0]["estado"] == "resolved"


def test_snapshot_record(tmp_path):
    m = MetricsStore(tmp_path / "m.db")
    m.record_snapshot("ubuntu-dev", "C:/snaps/a.tar", 12345)
    rows = m.list_snapshots()
    assert rows[0]["size_bytes"] == 12345


def test_tokens(tmp_path):
    m = MetricsStore(tmp_path / "m.db")
    tid = m.add_token("abc", "write", None, "ci")
    assert m.verify_token("abc")["scope"] == "write"
    assert m.verify_token("xyz") is None
    assert m.revoke_token(tid)
    assert m.verify_token("abc") is None


def test_legacy_token_compat(tmp_path):
    """Legacy tokens (SHA-256 without salt) must still verify."""
    import hashlib
    import sqlite3

    m = MetricsStore(tmp_path / "m.db")
    # Insert a legacy token directly (no salt column value)
    legacy_hash = hashlib.sha256(b"legacy-token").hexdigest()
    with m._lock:
        m._conn.execute(
            "INSERT INTO tokens (token_hash, salt, scope, created, expires, note) VALUES (?,?,?,?,?,?)",
            (legacy_hash, None, "read", 1000.0, None, "legacy"),
        )
        m._conn.commit()
    # The legacy token must verify via verify_token
    assert m.verify_token("legacy-token")["scope"] == "read"
    assert m.verify_token("wrong") is None


def test_prune(tmp_path):
    import time

    m = MetricsStore(tmp_path / "m.db")
    m.insert_metric("ubuntu-dev", "Running", 100, 10.0, None)
    old = time.time() - 100 * 86400
    m._exec("UPDATE metrics SET ts = ?", (old,))  # envejece todas
    m.prune(metrics_days=30)
    assert m.list_metrics() == []
