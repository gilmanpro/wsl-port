"""Panel web local (M7, P2): dashboard en http://127.0.0.1:8790.

Solo loopback. Token de sesion simple para proteger endpoints de accion.
"""
from __future__ import annotations

import secrets
import time

from fastapi import FastAPI, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse

INDEX_HTML = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>WSL Manager</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { font-family: 'Segoe UI', system-ui, sans-serif; background: #14181f; color: #e8eaf0; margin: 0; padding: 16px; }
  h1 { font-size: 20px; margin: 0 0 4px; }
  .sub { color: #8b93a3; font-size: 13px; margin-bottom: 16px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }
  .card { background: #1d2430; border: 1px solid #2a3344; border-radius: 10px; padding: 14px; }
  .card h3 { margin: 0 0 8px; font-size: 15px; display: flex; justify-content: space-between; align-items: center; }
  .dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; }
  .dot.on { background: #2ecc71; box-shadow: 0 0 8px #2ecc7188; }
  .dot.off { background: #566070; }
  .card .row { font-size: 13px; color: #b8c0cf; margin: 3px 0; }
  .card .row b { color: #e8eaf0; font-weight: 600; }
  .btns { margin-top: 10px; display: flex; gap: 6px; flex-wrap: wrap; }
  button { background: #2a3344; color: #e8eaf0; border: 1px solid #39445c; border-radius: 6px; padding: 4px 10px; font-size: 12px; cursor: pointer; }
  button:hover { background: #35415c; }
  button.ok { background: #1f5c33; border-color: #2ecc71; }
  button.warn { background: #5c3d1f; border-color: #e67e22; }
  button.danger { background: #5c1f1f; border-color: #e74c3c; }
  .bar { height: 8px; background: #2a3344; border-radius: 4px; overflow: hidden; margin-top: 4px; }
  .bar > div { height: 100%; background: linear-gradient(90deg, #2ecc71, #f1c40f); }
  .bar > div.hot { background: #e74c3c; }
  .alert { border-left: 3px solid #e67e22; padding: 6px 10px; margin: 6px 0; font-size: 13px; background: #241f17; border-radius: 4px; }
  .muted { color: #8b93a3; font-size: 12px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 8px; }
  th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid #2a3344; }
  th { color: #8b93a3; font-weight: 500; }
</style>
</head>
<body>
<h1>WSL Manager</h1>
<div class="sub">Panel local — estado de distros, metricas y alertas · <span id="ts">cargando...</span></div>

<div class="grid" id="cards"></div>

<h2 style="font-size:15px;margin-top:22px">Metricas</h2>
<table id="metrics"><thead><tr><th>Distro</th><th>Estado</th><th>RAM usada/total</th><th>%</th><th>CPU</th><th>Uptime</th></tr></thead><tbody></tbody></table>

<h2 style="font-size:15px;margin-top:22px">Alertas recientes</h2>
<div id="alerts"><span class="muted">sin alertas</span></div>

<script>
const $ = (s) => document.querySelector(s);
function esc(s) { const d = document.createElement('div'); d.textContent = s ?? ''; return d.innerHTML; }
async function api(path, method = 'GET') {
  const r = await fetch(path, { method });
  if (r.status === 401) { window.location.href = '/login'; throw new Error('no autenticado'); }
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
function fmtRam(mb) { return mb == null ? '-' : (mb >= 1024 ? (mb/1024).toFixed(1)+' GB' : mb+' MB'); }
function fmtUptime(s) { if (!s) return '-'; const h = Math.floor(s/3600), m = Math.floor((s%3600)/60); return h ? h+'h '+m+'m' : m+'m'; }
function uptime(s) { return s < 60 ? Math.floor(s)+'s' : fmtUptime(s); }

async function load() {
  try {
    const st = await api('/api/status');
    $('#ts').textContent = new Date().toLocaleTimeString();
    $('#cards').innerHTML = st.distros.map(d => {
      const pct = d.ram_percent ?? null;
      const hot = pct != null && pct >= 85;
      return `<div class="card">
        <h3>${esc(d.name)} <span class="dot ${d.running ? 'on' : 'off'}"></span></h3>
        <div class="row">Estado: <b>${esc(d.state)}</b>${d.default ? ' · default' : ''}</div>
        <div class="row">IP: <b>${esc(d.ip ?? '-')}</b></div>
        <div class="row">RAM: <b>${pct != null ? pct.toFixed(0)+'%' : '-'}</b></div>
        ${pct != null ? `<div class="bar"><div class="${hot ? 'hot' : ''}" style="width:${Math.min(100, pct)}%"></div></div>` : ''}
        <div class="btns">
          ${d.running ? `<button class="danger" onclick="act('stop','${d.name}')">Detener</button>
                         <button onclick="act('restart','${d.name}')">Reiniciar</button>
                         <button onclick="act('snapshot','${d.name}')">Snapshot</button>`
                       : `<button class="ok" onclick="act('start','${d.name}')">Iniciar</button>`}
        </div>
      </div>`;
    }).join('') || '<div class="card">Sin distros detectadas</div>';

    const m = await api('/api/metrics');
    $('#metrics tbody').innerHTML = m.metrics.map(x => `<tr>
      <td>${esc(x.name)}</td><td>${x.running ? 'RUN' : 'STOP'}</td>
      <td>${fmtRam(x.ram_used_mb)} / ${fmtRam(x.ram_total_mb)}</td>
      <td>${x.ram_percent != null ? x.ram_percent.toFixed(0)+'%' : '-'}</td>
      <td>${x.cpus ?? '-'}</td><td>${uptime(x.uptime_s)}</td></tr>`).join('');

    const al = await api('/api/alerts');
    $('#alerts').innerHTML = al.alerts.length ? al.alerts.slice(0, 8).map(a =>
      `<div class="alert"><b>${esc(a.tipo)}</b> — ${esc(a.message)} <span class="muted">(${new Date(a.ts*1000).toLocaleTimeString()})</span></div>`
    ).join('') : '<span class="muted">sin alertas</span>';
  } catch (e) {
    $('#ts').textContent = 'error: ' + e.message;
  }
}

async function act(action, name) {
  try {
    await api('/api/distros/' + encodeURIComponent(name) + '/' + action, 'POST');
  } catch (e) { alert(action + ' ' + name + ': ' + e.message); }
  setTimeout(load, 800);
}
load();
setInterval(load, 3000);
</script>
</body>
</html>
"""


LOGIN_HTML = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>WSL Manager — Login</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { font-family: 'Segoe UI', system-ui, sans-serif; background: #14181f; color: #e8eaf0;
         display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
  .login-box { background: #1d2430; border: 1px solid #2a3344; border-radius: 12px;
               padding: 28px 32px; width: 340px; text-align: center; }
  .login-box h1 { font-size: 20px; margin: 0 0 4px; }
  .login-box .sub { color: #8b93a3; font-size: 13px; margin-bottom: 20px; }
  .login-box input { width: 100%; padding: 10px 12px; font-size: 14px; border-radius: 8px;
                      border: 1px solid #39445c; background: #14181f; color: #e8eaf0; margin-bottom: 14px; }
  .login-box button { width: 100%; padding: 10px; font-size: 14px; border-radius: 8px;
                       border: 1px solid #2ecc71; background: #1f5c33; color: #e8eaf0;
                       cursor: pointer; font-weight: 600; }
  .login-box button:hover { background: #2a7a44; }
  .error { color: #e74c3c; font-size: 13px; margin-bottom: 10px; }
</style>
</head>
<body>
<div class="login-box">
  <h1>WSL Manager</h1>
  <div class="sub">Ingresa el token de acceso</div>
  <div id="err" class="error" style="display:none"></div>
  <form method="POST" action="/login">
    <input type="text" name="token" placeholder="Token de sesion" autocomplete="off" autofocus required>
    <button type="submit">Entrar</button>
  </form>
</div>
</body>
</html>
"""


def create_web_app(ctx) -> FastAPI:
    """App del panel web sobre el CliContext compartido (duck typing)."""
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import JSONResponse

    from src.api.server import apply_security_headers

    app = FastAPI(title="WSL Manager Panel", version="0.1.0")
    app.state.ctx = ctx  # type: ignore[attr-defined]

    # --- Session token ---
    web_token = secrets.token_urlsafe(16)
    app.state.web_token = web_token  # type: ignore[attr-defined]
    print(f"\n{'='*60}")
    print(f"  Token de acceso del panel web: {web_token}")
    print(f"  Copialo en: http://127.0.0.1:8790/login")
    print(f"{'='*60}\n")

    apply_security_headers(app)

    # --- Auth middleware ---
    UNAUTHENTICATED_PATHS = {"/login"}

    class SessionAuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            path = request.url.path
            # Allow unauthenticated paths and static root
            if path in UNAUTHENTICATED_PATHS:
                return await call_next(request)
            # Also allow POST /login (form submission)
            if path == "/login" and request.method == "POST":
                return await call_next(request)
            # Check session cookie
            session_cookie = request.cookies.get("session")
            if session_cookie != web_token:
                # API requests get JSON 401; page requests get redirect
                accept = request.headers.get("accept", "")
                if "application/json" in accept or request.url.path.startswith("/api/"):
                    return JSONResponse(status_code=401, content={"detail": "no autenticado"})
                return RedirectResponse(url="/login", status_code=302)
            return await call_next(request)

    app.add_middleware(SessionAuthMiddleware)

    @app.get("/login", response_class=HTMLResponse)
    def login_page():
        return LOGIN_HTML

    @app.post("/login")
    def login_submit(token: str = Form("")):
        from starlette.responses import HTMLResponse as _HTML
        if token == web_token:
            resp = RedirectResponse(url="/", status_code=302)
            resp.set_cookie("session", token, httponly=True, samesite="strict")
            return resp
        # Wrong token — re-render login with error
        err_html = LOGIN_HTML.replace(
            '<div id="err" class="error" style="display:none"></div>',
            '<div id="err" class="error">Token incorrecto. Intenta de nuevo.</div>'
        )
        return _HTML(content=err_html)

    def get_ctx():
        return app.state.ctx  # type: ignore[attr-defined]

    @app.get("/", response_class=HTMLResponse)
    def index():
        return INDEX_HTML

    @app.get("/api/status")
    def status():
        from src.core.watcher import Watcher

        c = get_ctx()
        state = Watcher(c.store, c.metrics, c.bus, c.wsl).snapshot_state()
        # adjunta ram_percent de metricas al payload de distros
        metrics = {m.name: m for m in c.resources.get_metrics()}
        for d in state["distros"]:
            m = metrics.get(d["name"])
            d["ram_percent"] = m.ram_percent if m else None
        return state

    @app.get("/api/metrics")
    def metrics():
        c = get_ctx()
        return {"metrics": [m.to_dict() for m in c.resources.get_metrics()]}

    @app.get("/api/alerts")
    def alerts():
        c = get_ctx()
        return {"alerts": c.metrics.list_alerts(30)}

    @app.get("/api/events")
    def events():
        c = get_ctx()
        return {"events": c.metrics.list_events(30)}

    @app.post("/api/distros/{name}/start")
    def start(name: str):
        c = get_ctx()
        r = c.wsl.start(name)
        if not r.ok:
            raise HTTPException(status_code=500, detail=r.error)
        c.metrics.log_event("web_start", name, "iniciada desde el panel web")
        return {"ok": True}

    @app.post("/api/distros/{name}/stop")
    def stop(name: str):
        c = get_ctx()
        r = c.wsl.stop(name)
        if not r.ok:
            raise HTTPException(status_code=500, detail=r.error)
        c.metrics.log_event("web_stop", name, "detenida desde el panel web")
        return {"ok": True}

    @app.post("/api/distros/{name}/restart")
    def restart(name: str):
        c = get_ctx()
        r = c.wsl.restart(name)
        if not r.ok:
            raise HTTPException(status_code=500, detail=r.error)
        return {"ok": True}

    @app.post("/api/distros/{name}/snapshot")
    def snapshot(name: str):
        c = get_ctx()
        try:
            path = c.wsl.snapshot(name, c.config.snapshots.retention_days, c.config.snapshots.target_dir)
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))
        size = path.stat().st_size if path.exists() else 0
        c.metrics.record_snapshot(name, str(path), size)
        return {"ok": True, "path": str(path), "size_bytes": size}

    @app.post("/api/shutdown")
    def shutdown():
        c = get_ctx()
        r = c.wsl.shutdown_all()
        if not r.ok:
            raise HTTPException(status_code=500, detail=r.error)
        return {"ok": True}

    return app
