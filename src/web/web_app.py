"""Panel web local (M7, P2): dashboard en http://127.0.0.1:8790.

Solo loopback. Token de sesion simple para proteger endpoints de accion.
Panel completo con todas las secciones de la GUI.
"""
from __future__ import annotations

import json
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
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; background: #14181f; color: #e8eaf0; min-height: 100vh; }

  /* --- Navbar --- */
  .navbar { background: #1a2030; border-bottom: 1px solid #2a3344; padding: 0 20px; display: flex; align-items: center; gap: 4px; overflow-x: auto; }
  .navbar .brand { font-size: 16px; font-weight: 700; color: #2ecc71; padding: 14px 16px 14px 0; border-right: 1px solid #2a3344; margin-right: 8px; white-space: nowrap; }
  .nav-tab { padding: 14px 16px; font-size: 13px; color: #8b93a3; cursor: pointer; border-bottom: 2px solid transparent; transition: all 0.2s; white-space: nowrap; background: none; border-top: none; border-left: none; border-right: none; font-family: inherit; }
  .nav-tab:hover { color: #e8eaf0; background: #1d2430; }
  .nav-tab.active { color: #2ecc71; border-bottom-color: #2ecc71; }

  /* --- Layout --- */
  .page { display: none; padding: 20px; max-width: 1400px; margin: 0 auto; }
  .page.active { display: block; }
  .page-header { margin-bottom: 20px; }
  .page-header h2 { font-size: 18px; font-weight: 600; margin-bottom: 4px; }
  .page-header .sub { color: #8b93a3; font-size: 13px; }

  /* --- Cards --- */
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
  .card { background: #1d2430; border: 1px solid #2a3344; border-radius: 10px; padding: 16px; transition: border-color 0.2s; }
  .card:hover { border-color: #39445c; }
  .card h3 { margin: 0 0 10px; font-size: 15px; display: flex; justify-content: space-between; align-items: center; }
  .card .row { font-size: 13px; color: #b8c0cf; margin: 4px 0; }
  .card .row b { color: #e8eaf0; font-weight: 600; }

  /* --- Dots & Status --- */
  .dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; vertical-align: middle; margin-right: 4px; }
  .dot.on { background: #2ecc71; box-shadow: 0 0 8px #2ecc7188; }
  .dot.off { background: #566070; }
  .dot.warn { background: #e67e22; box-shadow: 0 0 8px #e67e2288; }

  /* --- Bars --- */
  .bar { height: 8px; background: #2a3344; border-radius: 4px; overflow: hidden; margin-top: 6px; }
  .bar > div { height: 100%; background: linear-gradient(90deg, #2ecc71, #f1c40f); transition: width 0.5s; }
  .bar > div.hot { background: #e74c3c; }

  /* --- Tables --- */
  .table-wrap { background: #1d2430; border: 1px solid #2a3344; border-radius: 10px; overflow: hidden; margin-top: 12px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid #2a3344; }
  th { color: #8b93a3; font-weight: 500; background: #1a2030; position: sticky; top: 0; }
  td { color: #e8eaf0; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: #1f2a3a; }
  .muted { color: #8b93a3; font-size: 12px; }

  /* --- Buttons --- */
  .btns { margin-top: 10px; display: flex; gap: 6px; flex-wrap: wrap; }
  .btn { display: inline-flex; align-items: center; gap: 4px; background: #2a3344; color: #e8eaf0; border: 1px solid #39445c; border-radius: 6px; padding: 6px 12px; font-size: 12px; cursor: pointer; transition: all 0.2s; font-family: inherit; }
  .btn:hover { background: #35415c; transform: translateY(-1px); }
  .btn:active { transform: translateY(0); }
  .btn-ok { background: #1a4d2e; border-color: #2ecc71; color: #2ecc71; }
  .btn-ok:hover { background: #1f5c33; }
  .btn-danger { background: #4d1a1a; border-color: #e74c3c; color: #e74c3c; }
  .btn-danger:hover { background: #5c1f1f; }
  .btn-warn { background: #4d3a1a; border-color: #e67e22; color: #e67e22; }
  .btn-warn:hover { background: #5c3d1f; }
  .btn-blue { background: #1a2d4d; border-color: #3498db; color: #3498db; }
  .btn-blue:hover { background: #1f3660; }
  .btn-sm { padding: 4px 8px; font-size: 11px; }
  .btn-icon { padding: 4px 8px; font-size: 14px; }

  /* --- Alerts --- */
  .alert { border-left: 3px solid #e67e22; padding: 8px 12px; margin: 6px 0; font-size: 13px; background: #241f17; border-radius: 4px; display: flex; justify-content: space-between; align-items: center; }
  .alert.error { border-left-color: #e74c3c; background: #2a1717; }
  .alert.success { border-left-color: #2ecc71; background: #172a1a; }

  /* --- Forms --- */
  .form-group { margin-bottom: 14px; }
  .form-group label { display: block; font-size: 13px; color: #b8c0cf; margin-bottom: 4px; }
  .form-input { width: 100%; padding: 8px 12px; font-size: 13px; border-radius: 6px; border: 1px solid #39445c; background: #14181f; color: #e8eaf0; font-family: inherit; transition: border-color 0.2s; }
  .form-input:focus { outline: none; border-color: #2ecc71; }
  .form-row { display: flex; gap: 12px; flex-wrap: wrap; }
  .form-row .form-group { flex: 1; min-width: 160px; }

  /* --- Textarea (config editor) --- */
  .config-editor { width: 100%; min-height: 400px; padding: 12px; font-family: 'Consolas', 'Fira Code', monospace; font-size: 13px; border-radius: 8px; border: 1px solid #39445c; background: #0f1318; color: #e8eaf0; resize: vertical; line-height: 1.5; tab-size: 2; }
  .config-editor:focus { outline: none; border-color: #2ecc71; }

  /* --- Settings form --- */
  .settings-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
  .settings-section { background: #1d2430; border: 1px solid #2a3344; border-radius: 10px; padding: 16px; }
  .settings-section h3 { font-size: 14px; margin-bottom: 12px; color: #2ecc71; }
  .toggle { display: flex; align-items: center; gap: 8px; padding: 6px 0; }
  .toggle input[type="checkbox"] { width: 18px; height: 18px; accent-color: #2ecc71; }
  .toggle span { font-size: 13px; }

  /* --- Modal --- */
  .modal-overlay { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.6); z-index: 1000; justify-content: center; align-items: center; }
  .modal-overlay.show { display: flex; }
  .modal { background: #1d2430; border: 1px solid #2a3344; border-radius: 12px; padding: 24px; width: 440px; max-width: 90vw; max-height: 90vh; overflow-y: auto; }
  .modal h3 { font-size: 16px; margin-bottom: 16px; }
  .modal-footer { display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px; }

  /* --- Stats row --- */
  .stats-row { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
  .stat-card { background: #1d2430; border: 1px solid #2a3344; border-radius: 10px; padding: 14px 20px; min-width: 150px; flex: 1; }
  .stat-card .label { font-size: 11px; color: #8b93a3; text-transform: uppercase; letter-spacing: 0.5px; }
  .stat-card .value { font-size: 22px; font-weight: 700; margin-top: 4px; }
  .stat-card .value.green { color: #2ecc71; }
  .stat-card .value.blue { color: #3498db; }
  .stat-card .value.orange { color: #e67e22; }
  .stat-card .value.red { color: #e74c3c; }

  /* --- Responsive --- */
  @media (max-width: 768px) {
    .page { padding: 12px; }
    .grid { grid-template-columns: 1fr; }
    .stats-row { flex-direction: column; }
    .form-row { flex-direction: column; }
    .settings-grid { grid-template-columns: 1fr; }
    .table-wrap { overflow-x: auto; }
    .navbar { padding: 0 8px; }
    .nav-tab { padding: 12px 10px; font-size: 12px; }
  }

  /* --- Toast --- */
  .toast { position: fixed; bottom: 20px; right: 20px; background: #1d2430; border: 1px solid #2ecc71; border-radius: 8px; padding: 12px 20px; font-size: 13px; z-index: 2000; animation: slideIn 0.3s; }
  .toast.error { border-color: #e74c3c; }
  @keyframes slideIn { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }

  /* --- Spinner --- */
  .spinner { display: inline-block; width: 14px; height: 14px; border: 2px solid #39445c; border-top-color: #2ecc71; border-radius: 50%; animation: spin 0.8s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>

<!-- === Navbar === -->
<nav class="navbar">
  <div class="brand">WSL Manager</div>
  <button class="nav-tab active" onclick="showPage('dashboard')">Dashboard</button>
  <button class="nav-tab" onclick="showPage('forwards')">Forwards</button>
  <button class="nav-tab" onclick="showPage('tunnels')">Tunnels</button>
  <button class="nav-tab" onclick="showPage('publish')">Publicar</button>
  <button class="nav-tab" onclick="showPage('config')">Configuracion</button>
  <button class="nav-tab" onclick="showPage('settings')">Ajustes</button>
  <div style="flex:1"></div>
  <span class="muted" id="clock" style="padding-right:8px"></span>
</nav>

<!-- ======================== DASHBOARD ======================== -->
<div class="page active" id="page-dashboard">
  <div class="page-header">
    <h2>Dashboard</h2>
    <div class="sub">Estado de distros, metricas y alertas</div>
  </div>

  <div class="stats-row" id="dash-stats"></div>

  <h3 style="font-size:14px;margin-bottom:10px;color:#8b93a3">Distribuciones</h3>
  <div class="grid" id="cards"></div>

  <h3 style="font-size:14px;margin:20px 0 10px;color:#8b93a3">Metricas</h3>
  <div class="table-wrap">
    <table id="metrics">
      <thead><tr><th>Distro</th><th>Estado</th><th>RAM usada/total</th><th>%</th><th>CPU</th><th>Uptime</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>

  <h3 style="font-size:14px;margin:20px 0 10px;color:#8b93a3">Alertas recientes</h3>
  <div id="alerts"><span class="muted">sin alertas</span></div>
</div>

<!-- ======================== FORWARDS ======================== -->
<div class="page" id="page-forwards">
  <div class="page-header" style="display:flex;justify-content:space-between;align-items:flex-start">
    <div>
      <h2>Port Forwards</h2>
      <div class="sub">Forwards Windows &rarr; WSL via netsh portproxy</div>
    </div>
    <div style="display:flex;gap:6px;flex-wrap:wrap">
      <button class="btn btn-ok" onclick="fwdApplyAll()">Aplicar todos</button>
      <button class="btn btn-warn" onclick="fwdClearAll()">Limpiar todo</button>
      <button class="btn btn-blue" onclick="openModal('add-fwd-modal')">+ Agregar</button>
    </div>
  </div>

  <div class="stats-row" id="fwd-stats"></div>

  <div class="table-wrap">
    <table id="fwd-table">
      <thead><tr><th>Nombre</th><th>Puerto Local</th><th>WSL IP</th><th>WSL Port</th><th>Habilitado</th><th>Estado</th><th>Acciones</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>
</div>

<!-- ======================== TUNNELS ======================== -->
<div class="page" id="page-tunnels">
  <div class="page-header" style="display:flex;justify-content:space-between;align-items:flex-start">
    <div>
      <h2>Tunnels SSH</h2>
      <div class="sub">Tunnels SSH con reconexion automatica</div>
    </div>
    <button class="btn btn-blue" onclick="openModal('add-tun-modal')">+ Agregar</button>
  </div>

  <div class="stats-row" id="tun-stats"></div>

  <div class="table-wrap">
    <table id="tun-table">
      <thead><tr><th>Nombre</th><th>Host Remoto</th><th>Puerto Remoto</th><th>Puerto Local</th><th>Usuario SSH</th><th>SSH Host</th><th>Reconexion</th><th>Estado</th><th>Acciones</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>
</div>

<!-- ======================== PUBLISH (Publicar a Internet) ======================== -->
<div class="page" id="page-publish">
  <div class="page-header" style="display:flex;justify-content:space-between;align-items:flex-start">
    <div>
      <h2>Publicar a Internet</h2>
      <div class="sub">VPS configurados y tunnels para publicar servicios</div>
    </div>
    <button class="btn btn-ok" onclick="openModal('add-vps-modal')">+ Agregar VPS</button>
  </div>

  <div class="stats-row" id="publish-stats"></div>

  <h3 style="font-size:14px;margin-bottom:10px;color:#8b93a3">VPS Configurados</h3>
  <div class="table-wrap">
    <table id="vps-table">
      <thead><tr><th>ID</th><th>Host</th><th>Usuario</th><th>Puerto SSH</th><th>Clave SSH</th><th>Tunnels</th><th>Acciones</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>

  <h3 style="font-size:14px;margin:20px 0 10px;color:#8b93a3">Tunnels Activos por VPS</h3>
  <div class="table-wrap">
    <table id="pub-tun-table">
      <thead><tr><th>VPS</th><th>Nombre</th><th>Host Remoto</th><th>Puerto Remoto</th><th>Puerto Local</th><th>Estado</th><th>Acciones</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>
</div>

<!-- ======================== CONFIG ======================== -->
<div class="page" id="page-config">
  <div class="page-header" style="display:flex;justify-content:space-between;align-items:flex-start">
    <div>
      <h2>Configuracion</h2>
      <div class="sub">Edicion de config.json &mdash; se crea backup antes de guardar</div>
    </div>
    <div style="display:flex;gap:6px">
      <button class="btn" onclick="loadConfig()">&#x21bb; Recargar</button>
      <button class="btn btn-ok" onclick="saveConfig()">&#x1f4be; Guardar (con backup)</button>
    </div>
  </div>
  <div id="config-status" class="muted" style="margin-bottom:8px"></div>
  <textarea class="config-editor" id="config-editor" spellcheck="false" placeholder="Cargando config.json..."></textarea>
</div>

<!-- ======================== SETTINGS ======================== -->
<div class="page" id="page-settings">
  <div class="page-header">
    <h2>Ajustes</h2>
    <div class="sub">Tema, comportamiento, API y MCP</div>
  </div>

  <div class="settings-grid">
    <!-- UI Section -->
    <div class="settings-section">
      <h3>Interfaz</h3>
      <div class="form-group">
        <label>Tema</label>
        <select class="form-input" id="set-theme">
          <option value="darkly">Darkly</option>
          <option value="superhero">Superhero</option>
          <option value="cyborg">Cyborg</option>
          <option value="cosmo">Cosmo</option>
          <option value="flatly">Flatly</option>
          <option value="journal">Journal</option>
        </select>
      </div>
      <div class="form-group">
        <label>Intervalo de refresh (segundos)</label>
        <input class="form-input" type="number" id="set-refresh" min="1" max="60" value="2">
      </div>
      <div class="toggle">
        <input type="checkbox" id="set-minimized">
        <span>Iniciar minimizado (solo tray)</span>
      </div>
      <div class="toggle">
        <input type="checkbox" id="set-tray">
        <span>Cerrar ventana &rarr; minimizar a tray</span>
      </div>
    </div>

    <!-- Behavior Section -->
    <div class="settings-section">
      <h3>Comportamiento</h3>
      <div class="toggle">
        <input type="checkbox" id="set-stop-close">
        <span>Al salir: detener todas las distros</span>
      </div>
      <div class="form-group" style="margin-top:12px">
        <label>Nivel de log (LogLevel)</label>
        <select class="form-input" id="set-loglevel">
          <option value="DEBUG">DEBUG</option>
          <option value="INFO" selected>INFO</option>
          <option value="WARNING">WARNING</option>
          <option value="ERROR">ERROR</option>
        </select>
      </div>
      <div class="form-group">
        <label>Directorio de logs</label>
        <input class="form-input" type="text" id="set-logsdir" placeholder="(auto)">
      </div>
    </div>

    <!-- API Section -->
    <div class="settings-section">
      <h3>API REST</h3>
      <div class="toggle">
        <input type="checkbox" id="set-api-enabled">
        <span>Habilitada (loopback)</span>
      </div>
      <div class="form-group" style="margin-top:8px">
        <label>Puerto API</label>
        <input class="form-input" type="number" id="set-api-port" min="1024" max="65535" value="8791">
      </div>
    </div>

    <!-- Alerts Section -->
    <div class="settings-section">
      <h3>Alertas</h3>
      <div class="form-group">
        <label>Umbral de memoria (%)</label>
        <input class="form-input" type="number" id="set-alert-mem" min="1" max="100" value="85">
      </div>
      <div class="form-group">
        <label>Intervalo de chequeo (segundos)</label>
        <input class="form-input" type="number" id="set-alert-interval" min="5" max="300" value="15">
      </div>
      <div class="toggle">
        <input type="checkbox" id="set-alert-stop">
        <span>Alertar si distro se detiene inesperadamente</span>
      </div>
    </div>

    <!-- Snapshots Section -->
    <div class="settings-section">
      <h3>Snapshots</h3>
      <div class="toggle">
        <input type="checkbox" id="set-snap-enabled">
        <span>Snapshots habilitados</span>
      </div>
      <div class="form-group" style="margin-top:8px">
        <label>Retencion (dias)</label>
        <input class="form-input" type="number" id="set-snap-retention" min="1" max="365" value="14">
      </div>
    </div>

    <!-- Web Panel Section -->
    <div class="settings-section">
      <h3>Panel Web</h3>
      <div class="toggle">
        <input type="checkbox" id="set-web-enabled">
        <span>Panel web habilitado</span>
      </div>
      <div class="form-group" style="margin-top:8px">
        <label>Idioma</label>
        <select class="form-input" id="set-language">
          <option value="es">Español</option>
          <option value="en">English</option>
        </select>
      </div>
    </div>
  </div>

  <div style="margin-top:20px;display:flex;gap:8px">
    <button class="btn btn-ok" onclick="saveSettings()">&#x1f4be; Guardar ajustes</button>
    <span class="muted" id="settings-status" style="display:flex;align-items:center"></span>
  </div>
</div>

<!-- ======================== MODALS ======================== -->

<!-- Add Forward Modal -->
<div class="modal-overlay" id="add-fwd-modal">
  <div class="modal">
    <h3>Agregar Forward</h3>
    <div class="form-row">
      <div class="form-group">
        <label>Nombre</label>
        <input class="form-input" id="fwd-name" placeholder="mi-forward">
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Puerto Local</label>
        <input class="form-input" id="fwd-local-port" type="number" value="8080" min="1" max="65535">
      </div>
      <div class="form-group">
        <label>WSL Port</label>
        <input class="form-input" id="fwd-wsl-port" type="number" value="80" min="1" max="65535">
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>WSL IP</label>
        <input class="form-input" id="fwd-wsl-ip" value="127.0.0.1">
      </div>
      <div class="form-group">
        <label>&nbsp;</label>
        <div class="toggle" style="padding-top:8px">
          <input type="checkbox" id="fwd-enabled" checked>
          <span>Habilitado</span>
        </div>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn" onclick="closeModal('add-fwd-modal')">Cancelar</button>
      <button class="btn btn-ok" onclick="addForward()">Agregar</button>
    </div>
  </div>
</div>

<!-- Add Tunnel Modal -->
<div class="modal-overlay" id="add-tun-modal">
  <div class="modal">
    <h3>Agregar Tunnel SSH</h3>
    <div class="form-row">
      <div class="form-group">
        <label>Nombre</label>
        <input class="form-input" id="tun-name" placeholder="mi-tunnel">
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Host Remoto</label>
        <input class="form-input" id="tun-remote-host" placeholder="192.168.1.100">
      </div>
      <div class="form-group">
        <label>Puerto Remoto</label>
        <input class="form-input" id="tun-remote-port" type="number" value="22" min="1" max="65535">
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Puerto Local</label>
        <input class="form-input" id="tun-local-port" type="number" value="2222" min="1" max="65535">
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Usuario SSH</label>
        <input class="form-input" id="tun-ssh-user" value="root">
      </div>
      <div class="form-group">
        <label>SSH Host (si difiere del remoto)</label>
        <input class="form-input" id="tun-ssh-host" placeholder="(vacio = igual a remoto)">
      </div>
    </div>
    <div style="display:flex;gap:16px;margin-top:8px">
      <div class="toggle">
        <input type="checkbox" id="tun-auto" checked>
        <span>Reconexion automatica</span>
      </div>
      <div class="toggle">
        <input type="checkbox" id="tun-enabled" checked>
        <span>Habilitado</span>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn" onclick="closeModal('add-tun-modal')">Cancelar</button>
      <button class="btn btn-ok" onclick="addTunnel()">Agregar</button>
    </div>
  </div>
</div>

<!-- Add VPS Modal -->
<div class="modal-overlay" id="add-vps-modal">
  <div class="modal">
    <h3>Agregar VPS</h3>
    <div class="form-row">
      <div class="form-group">
        <label>ID (nombre descriptivo)</label>
        <input class="form-input" id="vps-id" placeholder="mi-vps">
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Host (IP o dominio)</label>
        <input class="form-input" id="vps-host" placeholder="192.168.1.100">
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Usuario SSH</label>
        <input class="form-input" id="vps-user" value="root">
      </div>
      <div class="form-group">
        <label>Puerto SSH</label>
        <input class="form-input" id="vps-port" type="number" value="22" min="1" max="65535">
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Clave SSH (ruta, opcional)</label>
        <input class="form-input" id="vps-identity" placeholder="C:/Users/.../.ssh/id_rsa">
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn" onclick="closeModal('add-vps-modal')">Cancelar</button>
      <button class="btn btn-ok" onclick="addVps()">Agregar</button>
    </div>
  </div>
</div>

<!-- Connect VPS Modal -->
<div class="modal-overlay" id="connect-vps-modal">
  <div class="modal">
    <h3>Abrir Tunnel al VPS</h3>
    <div class="form-row">
      <div class="form-group">
        <label>Nombre del Tunnel</label>
        <input class="form-input" id="pub-tun-name" placeholder="pub-mi-vps">
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Puerto Remoto (en el VPS)</label>
        <input class="form-input" id="pub-tun-remote-port" type="number" value="80" min="1" max="65535">
      </div>
      <div class="form-group">
        <label>Puerto Local (en Windows)</label>
        <input class="form-input" id="pub-tun-local-port" type="number" value="8080" min="1" max="65535">
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn" onclick="closeModal('connect-vps-modal')">Cancelar</button>
      <button class="btn btn-blue" onclick="connectVps()">Abrir Tunnel</button>
    </div>
  </div>
</div>

<!-- Confirm Modal -->
<div class="modal-overlay" id="confirm-modal">
  <div class="modal" style="width:360px">
    <h3 id="confirm-title">Confirmar</h3>
    <p id="confirm-msg" style="font-size:13px;color:#b8c0cf"></p>
    <div class="modal-footer">
      <button class="btn" onclick="closeModal('confirm-modal')">Cancelar</button>
      <button class="btn btn-danger" id="confirm-ok" onclick="">Confirmar</button>
    </div>
  </div>
</div>

<script>
// === Utility ===
const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);
function esc(s) { const d = document.createElement('div'); d.textContent = s ?? ''; return d.innerHTML; }

async function api(path, method='GET', body=null) {
  const opts = { method, headers: {} };
  if (body) {
    if (body instanceof FormData) {
      opts.body = body;
    } else {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
  }
  const r = await fetch(path, opts);
  if (r.status === 401) { window.location.href = '/login'; throw new Error('no autenticado'); }
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

function fmtRam(mb) { return mb == null ? '-' : (mb >= 1024 ? (mb/1024).toFixed(1)+' GB' : mb+' MB'); }
function fmtUptime(s) { if (!s) return '-'; const h=Math.floor(s/3600), m=Math.floor((s%3600)/60); return h ? h+'h '+m+'m' : m+'m'; }
function uptime(s) { return s < 60 ? Math.floor(s)+'s' : fmtUptime(s); }

function toast(msg, isError=false) {
  const el = document.createElement('div');
  el.className = 'toast' + (isError ? ' error' : '');
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3000);
}

// === Navigation ===
let currentPage = 'dashboard';
function showPage(name) {
  currentPage = name;
  $$('.page').forEach(p => p.classList.remove('active'));
  $$('.nav-tab').forEach(t => t.classList.remove('active'));
  const page = $('#page-' + name);
  if (page) page.classList.add('active');
  const tabs = $$('.nav-tab');
  const idx = ['dashboard','forwards','tunnels','publish','config','settings'].indexOf(name);
  if (idx >= 0 && tabs[idx]) tabs[idx].classList.add('active');
}

// === Modal ===
function openModal(id) { document.getElementById(id).classList.add('show'); }
function closeModal(id) { document.getElementById(id).classList.remove('show'); }
document.querySelectorAll('.modal-overlay').forEach(m => {
  m.addEventListener('click', e => { if (e.target === m) m.classList.remove('show'); });
});

// === Confirm dialog ===
let confirmCallback = null;
function confirmAction(title, msg, cb) {
  $('#confirm-title').textContent = title;
  $('#confirm-msg').textContent = msg;
  confirmCallback = cb;
  $('#confirm-ok').onclick = () => { closeModal('confirm-modal'); if (confirmCallback) confirmCallback(); };
  openModal('confirm-modal');
}

// === Clock ===
function updateClock() { $('#clock').textContent = new Date().toLocaleTimeString(); }
setInterval(updateClock, 1000);
updateClock();

// === DASHBOARD ===
async function loadDashboard() {
  try {
    const st = await api('/api/status');
    const distros = st.distros || [];
    const running = distros.filter(d => d.running).length;
    const total = distros.length;

    $('#dash-stats').innerHTML = `
      <div class="stat-card"><div class="label">Distro</div><div class="value green">${running}/${total}</div></div>
      <div class="stat-card"><div class="label">Ejecutando</div><div class="value blue">${running}</div></div>
      <div class="stat-card"><div class="label">Detenidas</div><div class="value orange">${total - running}</div></div>
      <div class="stat-card"><div class="label">Alertas</div><div class="value red" id="alert-count">-</div></div>
    `;

    $('#cards').innerHTML = distros.map(d => {
      const pct = d.ram_percent ?? null;
      const hot = pct != null && pct >= 85;
      return `<div class="card">
        <h3>${esc(d.name)} <span class="dot ${d.running ? 'on' : 'off'}"></span></h3>
        <div class="row">Estado: <b>${esc(d.state)}</b>${d.default ? ' &middot; default' : ''}</div>
        <div class="row">IP: <b>${esc(d.ip ?? '-')}</b></div>
        <div class="row">RAM: <b>${pct != null ? pct.toFixed(0)+'%' : '-'}</b></div>
        ${pct != null ? `<div class="bar"><div class="${hot ? 'hot' : ''}" style="width:${Math.min(100,pct)}%"></div></div>` : ''}
        <div class="btns">
          ${d.running
            ? `<button class="btn btn-danger btn-sm" onclick="act('stop','${esc(d.name)}')">Detener</button>
               <button class="btn btn-sm" onclick="act('restart','${esc(d.name)}')">Reiniciar</button>
               <button class="btn btn-blue btn-sm" onclick="act('snapshot','${esc(d.name)}')">Snapshot</button>`
            : `<button class="btn btn-ok btn-sm" onclick="act('start','${esc(d.name)}')">Iniciar</button>`}
        </div>
      </div>`;
    }).join('') || '<div class="card"><span class="muted">Sin distros detectadas</span></div>';

    const m = await api('/api/metrics');
    $('#metrics tbody').innerHTML = (m.metrics || []).map(x => `<tr>
      <td>${esc(x.name)}</td>
      <td><span class="dot ${x.running ? 'on' : 'off'}"></span>${x.running ? 'RUN' : 'STOP'}</td>
      <td>${fmtRam(x.ram_used_mb)} / ${fmtRam(x.ram_total_mb)}</td>
      <td>${x.ram_percent != null ? x.ram_percent.toFixed(0)+'%' : '-'}</td>
      <td>${x.cpus ?? '-'}</td>
      <td>${uptime(x.uptime_s)}</td>
    </tr>`).join('') || '<tr><td colspan="6" class="muted">sin metricas</td></tr>';

    const al = await api('/api/alerts');
    const alerts = al.alerts || [];
    if ($('#alert-count')) $('#alert-count').textContent = alerts.length;
    $('#alerts').innerHTML = alerts.length ? alerts.slice(0, 10).map(a =>
      `<div class="alert"><div><b>${esc(a.tipo)}</b> — ${esc(a.message)}</div><span class="muted">${new Date(a.ts*1000).toLocaleTimeString()}</span></div>`
    ).join('') : '<span class="muted">sin alertas</span>';
  } catch(e) { console.error('dashboard error:', e); }
}

async function act(action, name) {
  try {
    await api('/api/distros/' + encodeURIComponent(name) + '/' + action, 'POST');
    toast(name + ': ' + action + ' OK');
  } catch(e) { toast(action + ' ' + name + ': ' + e.message, true); }
  setTimeout(loadAll, 800);
}

// === FORWARDS ===
async function loadForwards() {
  try {
    const fw = await api('/api/forwards');
    const fwdBody = fw.forwards || [];
    const active = fwdBody.filter(f => f.active).length;

    $('#fwd-stats').innerHTML = `
      <div class="stat-card"><div class="label">Total</div><div class="value blue">${fwdBody.length}</div></div>
      <div class="stat-card"><div class="label">Activos</div><div class="value green">${active}</div></div>
      <div class="stat-card"><div class="label">Inactivos</div><div class="value orange">${fwdBody.length - active}</div></div>
    `;

    $('#fwd-table tbody').innerHTML = fwdBody.length ? fwdBody.map(f => `<tr>
      <td><b>${esc(f.name)}</b></td>
      <td>${f.local_port}</td>
      <td>${esc(f.wsl_ip)}</td>
      <td>${f.wsl_port}</td>
      <td>${f.enabled ? '<span style="color:#2ecc71">Si</span>' : '<span style="color:#e74c3c">No</span>'}</td>
      <td>${f.active ? '<span class="dot on"></span> Activo' : '<span class="dot off"></span> Inactivo'}</td>
      <td>
        ${f.active
          ? `<button class="btn btn-warn btn-sm" onclick="fwdAct('stop','${esc(f.name)}')">Detener</button>`
          : `<button class="btn btn-ok btn-sm" onclick="fwdAct('start','${esc(f.name)}')">Iniciar</button>`}
        <button class="btn btn-danger btn-sm" onclick="fwdRemove('${esc(f.name)}')">Eliminar</button>
      </td>
    </tr>`).join('') : '<tr><td colspan="7" class="muted" style="text-align:center;padding:24px">Sin forwards configurados. Haz clic en "+ Agregar" para crear uno.</td></tr>';
  } catch(e) { console.error('forwards error:', e); }
}

async function fwdAct(action, name) {
  try {
    await api('/api/forwards/' + encodeURIComponent(name) + '/' + action, 'POST');
    toast('Forward ' + name + ': ' + action + ' OK');
  } catch(e) { toast('forward ' + action + ': ' + e.message, true); }
  setTimeout(loadAll, 800);
}

function fwdRemove(name) {
  confirmAction('Eliminar Forward', '¿Eliminar el forward "' + name + '"?', async () => {
    try {
      await api('/api/forwards/' + encodeURIComponent(name) + '/remove', 'POST');
      toast('Forward ' + name + ' eliminado');
    } catch(e) { toast('error: ' + e.message, true); }
    setTimeout(loadAll, 800);
  });
}

function fwdApplyAll() {
  confirmAction('Aplicar todos', '¿Aplicar todas las reglas netsh para forwards habilitados?', async () => {
    try {
      const r = await api('/api/forwards/apply-all', 'POST');
      toast('Aplicados: ' + r.applied + '/' + r.total);
    } catch(e) { toast('error: ' + e.message, true); }
    setTimeout(loadAll, 800);
  });
}

function fwdClearAll() {
  confirmAction('Limpiar todo', '¿Eliminar TODAS las reglas netsh? Esto es destructivo.', async () => {
    try {
      const r = await api('/api/forwards/clear-all', 'POST');
      toast('Limpiados: ' + r.cleared + ' forwards');
    } catch(e) { toast('error: ' + e.message, true); }
    setTimeout(loadAll, 800);
  });
}

async function addForward() {
  const name = $('#fwd-name').value.trim();
  if (!name) { toast('El nombre es obligatorio', true); return; }
  const fd = new FormData();
  fd.append('name', name);
  fd.append('local_port', $('#fwd-local-port').value);
  fd.append('wsl_port', $('#fwd-wsl-port').value);
  fd.append('wsl_ip', $('#fwd-wsl-ip').value || '127.0.0.1');
  fd.append('enabled', $('#fwd-enabled').checked);
  try {
    await api('/api/forwards', 'POST', fd);
    toast('Forward "' + name + '" agregado');
    closeModal('add-fwd-modal');
    // Reset form
    $('#fwd-name').value = '';
    $('#fwd-local-port').value = '8080';
    $('#fwd-wsl-port').value = '80';
    $('#fwd-wsl-ip').value = '127.0.0.1';
  } catch(e) { toast('error: ' + e.message, true); }
  setTimeout(loadAll, 800);
}

// === TUNNELS ===
async function loadTunnels() {
  try {
    const tn = await api('/api/tunnels');
    const tunBody = tn.tunnels || [];
    const active = tunBody.filter(t => t.active).length;

    $('#tun-stats').innerHTML = `
      <div class="stat-card"><div class="label">Total</div><div class="value blue">${tunBody.length}</div></div>
      <div class="stat-card"><div class="label">Activos</div><div class="value green">${active}</div></div>
      <div class="stat-card"><div class="label">Inactivos</div><div class="value orange">${tunBody.length - active}</div></div>
    `;

    $('#tun-table tbody').innerHTML = tunBody.length ? tunBody.map(t => `<tr>
      <td><b>${esc(t.name)}</b></td>
      <td>${esc(t.remote_host)}</td>
      <td>${t.remote_port}</td>
      <td>${t.local_port}</td>
      <td>${esc(t.ssh_user || '-')}</td>
      <td>${esc(t.ssh_host || '-')}</td>
      <td>${t.auto_reconnect ? '<span style="color:#2ecc71">Si</span>' : 'No'}</td>
      <td>${t.active ? '<span class="dot on"></span> Activo' : '<span class="dot off"></span> Inactivo'}</td>
      <td>
        ${t.active
          ? `<button class="btn btn-warn btn-sm" onclick="tunAct('stop','${esc(t.name)}')">Detener</button>`
          : `<button class="btn btn-ok btn-sm" onclick="tunAct('start','${esc(t.name)}')">Iniciar</button>`}
        <button class="btn btn-danger btn-sm" onclick="tunRemove('${esc(t.name)}')">Eliminar</button>
      </td>
    </tr>`).join('') : '<tr><td colspan="9" class="muted" style="text-align:center;padding:24px">Sin tunnels configurados. Haz clic en "+ Agregar" para crear uno.</td></tr>';
  } catch(e) { console.error('tunnels error:', e); }
}

async function tunAct(action, name) {
  try {
    await api('/api/tunnels/' + encodeURIComponent(name) + '/' + action, 'POST');
    toast('Tunnel ' + name + ': ' + action + ' OK');
  } catch(e) { toast('tunnel ' + action + ': ' + e.message, true); }
  setTimeout(loadAll, 800);
}

function tunRemove(name) {
  confirmAction('Eliminar Tunnel', '¿Eliminar el tunnel "' + name + '"?', async () => {
    try {
      await api('/api/tunnels/' + encodeURIComponent(name) + '/remove', 'POST');
      toast('Tunnel ' + name + ' eliminado');
    } catch(e) { toast('error: ' + e.message, true); }
    setTimeout(loadAll, 800);
  });
}

async function addTunnel() {
  const name = $('#tun-name').value.trim();
  if (!name) { toast('El nombre es obligatorio', true); return; }
  const fd = new FormData();
  fd.append('name', name);
  fd.append('remote_host', $('#tun-remote-host').value);
  fd.append('remote_port', $('#tun-remote-port').value);
  fd.append('local_port', $('#tun-local-port').value);
  fd.append('ssh_user', $('#tun-ssh-user').value);
  fd.append('ssh_host', $('#tun-ssh-host').value);
  fd.append('auto_reconnect', $('#tun-auto').checked);
  fd.append('enabled', $('#tun-enabled').checked);
  try {
    await api('/api/tunnels', 'POST', fd);
    toast('Tunnel "' + name + '" agregado');
    closeModal('add-tun-modal');
    // Reset form
    $('#tun-name').value = '';
    $('#tun-remote-host').value = '';
    $('#tun-remote-port').value = '22';
    $('#tun-local-port').value = '2222';
    $('#tun-ssh-user').value = 'root';
    $('#tun-ssh-host').value = '';
  } catch(e) { toast('error: ' + e.message, true); }
  setTimeout(loadAll, 800);
}

// === PUBLISH (VPS) ===
let connectVpsId = null;

async function loadPublish() {
  try {
    const vpsResp = await api('/api/vps');
    const vpsList = vpsResp.vps || [];

    const tnResp = await api('/api/tunnels');
    const allTunnels = tnResp.tunnels || [];

    // Get VPS hosts for matching
    const vpsHosts = {};
    vpsList.forEach(v => { vpsHosts[v.host] = v.id; });

    // Filter tunnels that belong to VPS
    const pubTunnels = allTunnels.filter(t => vpsHosts[t.ssh_host] || vpsHosts[t.remote_host]);

    $('#publish-stats').innerHTML = `
      <div class="stat-card"><div class="label">VPS</div><div class="value blue">${vpsList.length}</div></div>
      <div class="stat-card"><div class="label">Tunnels Activos</div><div class="value green">${pubTunnels.filter(t => t.active).length}</div></div>
      <div class="stat-card"><div class="label">Tunnels Totales</div><div class="value orange">${pubTunnels.length}</div></div>
    `;

    // VPS table
    $('#vps-table tbody').innerHTML = vpsList.length ? vpsList.map(v => {
      const tuns = allTunnels.filter(t => t.ssh_host === v.host || t.remote_host === v.host);
      const activeTuns = tuns.filter(t => t.active).length;
      return `<tr>
        <td><b>${esc(v.id)}</b></td>
        <td>${esc(v.host)}</td>
        <td>${esc(v.user)}</td>
        <td>${v.port}</td>
        <td>${v.identity_file ? esc(v.identity_file) : '<span class="muted">(default)</span>'}</td>
        <td>${activeTuns}/${tuns.length}</td>
        <td>
          <button class="btn btn-blue btn-sm" onclick="openConnectVps('${esc(v.id)}')">Conectar</button>
          <button class="btn btn-warn btn-sm" onclick="disconnectVps('${esc(v.id)}')">Desconectar</button>
          <button class="btn btn-danger btn-sm" onclick="removeVps('${esc(v.id)}')">Eliminar</button>
        </td>
      </tr>`;
    }).join('') : '<tr><td colspan="7" class="muted" style="text-align:center;padding:24px">Sin VPS configurados. Haz clic en "+ Agregar VPS" para crear uno.</td></tr>';

    // Publish tunnels table
    $('#pub-tun-table tbody').innerHTML = pubTunnels.length ? pubTunnels.map(t => {
      const vpsId = vpsHosts[t.ssh_host] || vpsHosts[t.remote_host] || '?';
      return `<tr>
        <td><b>${esc(vpsId)}</b></td>
        <td>${esc(t.name)}</td>
        <td>${esc(t.remote_host)}</td>
        <td>${t.remote_port}</td>
        <td>${t.local_port}</td>
        <td>${t.active ? '<span class="dot on"></span> Activo' : '<span class="dot off"></span> Inactivo'}</td>
        <td>
          ${t.active
            ? `<button class="btn btn-warn btn-sm" onclick="tunAct('stop','${esc(t.name)}')">Detener</button>`
            : `<button class="btn btn-ok btn-sm" onclick="tunAct('start','${esc(t.name)}')">Iniciar</button>`}
          <button class="btn btn-danger btn-sm" onclick="tunRemove('${esc(t.name)}')">Eliminar</button>
        </td>
      </tr>`;
    }).join('') : '<tr><td colspan="7" class="muted" style="text-align:center;padding:24px">Sin tunnels activos para VPS.</td></tr>';
  } catch(e) { console.error('publish error:', e); }
}

async function addVps() {
  const id = $('#vps-id').value.trim();
  if (!id) { toast('El ID es obligatorio', true); return; }
  const host = $('#vps-host').value.trim();
  if (!host) { toast('El host es obligatorio', true); return; }
  try {
    await api('/api/vps', 'POST', {
      id, host,
      user: $('#vps-user').value || 'root',
      port: parseInt($('#vps-port').value) || 22,
      identity_file: $('#vps-identity').value || '',
    });
    toast('VPS "' + id + '" agregado');
    closeModal('add-vps-modal');
    $('#vps-id').value = '';
    $('#vps-host').value = '';
    $('#vps-user').value = 'root';
    $('#vps-port').value = '22';
    $('#vps-identity').value = '';
  } catch(e) { toast('error: ' + e.message, true); }
  setTimeout(loadAll, 800);
}

function removeVps(id) {
  confirmAction('Eliminar VPS', '¿Eliminar el VPS "' + id + '"?', async () => {
    try {
      await api('/api/vps/' + encodeURIComponent(id), 'DELETE');
      toast('VPS ' + id + ' eliminado');
    } catch(e) { toast('error: ' + e.message, true); }
    setTimeout(loadAll, 800);
  });
}

function openConnectVps(id) {
  connectVpsId = id;
  $('#pub-tun-name').value = 'pub-' + id;
  openModal('connect-vps-modal');
}

async function connectVps() {
  if (!connectVpsId) return;
  try {
    await api('/api/vps/' + encodeURIComponent(connectVpsId) + '/connect', 'POST', {
      name: $('#pub-tun-name').value || 'pub-' + connectVpsId,
      remote_port: parseInt($('#pub-tun-remote-port').value) || 80,
      local_port: parseInt($('#pub-tun-local-port').value) || 8080,
    });
    toast('Tunnel al VPS ' + connectVpsId + ' abierto');
    closeModal('connect-vps-modal');
  } catch(e) { toast('error: ' + e.message, true); }
  setTimeout(loadAll, 800);
}

async function disconnectVps(id) {
  confirmAction('Desconectar VPS', '¿Cerrar todos los tunnels del VPS "' + id + '"?', async () => {
    try {
      const r = await api('/api/vps/' + encodeURIComponent(id) + '/disconnect', 'POST');
      toast(r.closed + ' tunnel(s) cerrado(s)');
    } catch(e) { toast('error: ' + e.message, true); }
    setTimeout(loadAll, 800);
  });
}

// === CONFIG ===
async function loadConfig() {
  try {
    const r = await api('/api/config');
    $('#config-editor').value = JSON.stringify(r.config, null, 2);
    $('#config-status').textContent = 'Configuracion cargada correctamente';
  } catch(e) { $('#config-status').textContent = 'Error: ' + e.message; }
}

async function saveConfig() {
  const content = $('#config-editor').value;
  try {
    JSON.parse(content); // validate
  } catch(e) {
    toast('JSON invalido: ' + e.message, true);
    return;
  }
  try {
    await api('/api/config', 'POST', { content });
    toast('Configuracion guardada (con backup)');
    $('#config-status').textContent = 'Guardado: ' + new Date().toLocaleTimeString();
  } catch(e) { toast('error: ' + e.message, true); }
}

// === SETTINGS ===
async function loadSettings() {
  try {
    const r = await api('/api/settings');
    const s = r.settings;
    $('#set-theme').value = s.theme || 'darkly';
    $('#set-refresh').value = s.refresh_interval_seconds || 2;
    $('#set-minimized').checked = s.start_minimized || false;
    $('#set-tray').checked = s.close_to_tray || false;
    $('#set-stop-close').checked = s.stop_distros || false;
    $('#set-loglevel').value = s.log_level || 'INFO';
    $('#set-logsdir').value = s.logs_dir || '';
    $('#set-api-enabled').checked = s.api_enabled || false;
    $('#set-api-port').value = s.api_port || 8791;
    $('#set-alert-mem').value = s.alert_memory_percent || 85;
    $('#set-alert-interval').value = s.alert_check_interval || 15;
    $('#set-alert-stop').checked = s.alert_distro_stopped || false;
    $('#set-snap-enabled').checked = s.snapshots_enabled || false;
    $('#set-snap-retention').value = s.snapshots_retention || 14;
    $('#set-web-enabled').checked = s.web_panel_enabled || false;
    $('#set-language').value = s.language || 'es';
  } catch(e) { console.error('settings load error:', e); }
}

async function saveSettings() {
  const data = {
    theme: $('#set-theme').value,
    refresh_interval_seconds: parseInt($('#set-refresh').value) || 2,
    start_minimized: $('#set-minimized').checked,
    close_to_tray: $('#set-tray').checked,
    stop_distros: $('#set-stop-close').checked,
    log_level: $('#set-loglevel').value,
    logs_dir: $('#set-logsdir').value || null,
    api_enabled: $('#set-api-enabled').checked,
    api_port: parseInt($('#set-api-port').value) || 8791,
    alert_memory_percent: parseInt($('#set-alert-mem').value) || 85,
    alert_check_interval: parseInt($('#set-alert-interval').value) || 15,
    alert_distro_stopped: $('#set-alert-stop').checked,
    snapshots_enabled: $('#set-snap-enabled').checked,
    snapshots_retention: parseInt($('#set-snap-retention').value) || 14,
    web_panel_enabled: $('#set-web-enabled').checked,
    language: $('#set-language').value,
  };
  try {
    await api('/api/settings', 'POST', data);
    toast('Ajustes guardados correctamente');
    $('#settings-status').textContent = 'Guardado: ' + new Date().toLocaleTimeString();
  } catch(e) { toast('error: ' + e.message, true); }
}

// === Load all ===
async function loadAll() {
  await loadDashboard();
  await loadForwards();
  await loadTunnels();
  await loadPublish();
  // Load config/settings on demand (when page visible)
  if (currentPage === 'config') await loadConfig();
  if (currentPage === 'settings') await loadSettings();
}

// Initial load
loadAll();
setInterval(loadAll, 3000);

// Load config/settings when switching to those tabs
const origShowPage = showPage;
// Already defined above, so we hook into page visibility
setInterval(() => {
  if (currentPage === 'config') loadConfig();
  if (currentPage === 'settings') loadSettings();
  if (currentPage === 'publish') loadPublish();
}, 5000);
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
  .login-box h1 { font-size: 20px; margin: 0 0 4px; color: #2ecc71; }
  .login-box .sub { color: #8b93a3; font-size: 13px; margin-bottom: 20px; }
  .login-box input { width: 100%; padding: 10px 12px; font-size: 14px; border-radius: 8px;
                      border: 1px solid #39445c; background: #14181f; color: #e8eaf0; margin-bottom: 14px; }
  .login-box input:focus { outline: none; border-color: #2ecc71; }
  .login-box button { width: 100%; padding: 10px; font-size: 14px; border-radius: 8px;
                       border: 1px solid #2ecc71; background: #1f5c33; color: #e8eaf0;
                       cursor: pointer; font-weight: 600; transition: background 0.2s; }
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

    app = FastAPI(title="WSL Manager Panel", version="0.2.0")
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

    # === Pages ===

    @app.get("/", response_class=HTMLResponse)
    def index():
        return INDEX_HTML

    # === Dashboard / Status API ===

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

    # === Distro actions ===

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

    # === Forwards ===

    @app.get("/api/forwards")
    def forwards_list():
        c = get_ctx()
        return {"forwards": c.forwarding.list_forwards()}

    @app.post("/api/forwards")
    def forwards_add(name: str = Form(...), local_port: int = Form(...), wsl_port: int = Form(...), wsl_ip: str = Form("127.0.0.1"), enabled: bool = Form(True)):
        from src.core.config import ForwardItem
        c = get_ctx()
        fwd = ForwardItem(name=name, local_port=local_port, wsl_port=wsl_port, wsl_ip=wsl_ip, enabled=enabled)
        r = c.forwarding.add_forward(fwd)
        if not r.get("ok"):
            raise HTTPException(status_code=400, detail=r.get("error", "error"))
        return r

    @app.post("/api/forwards/apply-all")
    def forwards_apply_all():
        c = get_ctx()
        return c.forwarding.apply_all_forwards()

    @app.post("/api/forwards/clear-all")
    def forwards_clear_all():
        c = get_ctx()
        return c.forwarding.clear_all_forwards()

    @app.post("/api/forwards/{name}/start")
    def forwards_start(name: str):
        c = get_ctx()
        r = c.forwarding.start_forward(name)
        if not r.get("ok"):
            raise HTTPException(status_code=400, detail=r.get("error", "error"))
        return r

    @app.post("/api/forwards/{name}/stop")
    def forwards_stop(name: str):
        c = get_ctx()
        r = c.forwarding.stop_forward(name)
        if not r.get("ok"):
            raise HTTPException(status_code=400, detail=r.get("error", "error"))
        return r

    @app.post("/api/forwards/{name}/remove")
    def forwards_remove(name: str):
        c = get_ctx()
        r = c.forwarding.remove_forward(name)
        if not r.get("ok"):
            raise HTTPException(status_code=400, detail=r.get("error", "error"))
        return r

    # === Tunnels ===

    @app.get("/api/tunnels")
    def tunnels_list():
        c = get_ctx()
        return {"tunnels": c.forwarding.list_tunnels()}

    @app.post("/api/tunnels")
    def tunnels_add(name: str = Form(...), remote_host: str = Form(...), remote_port: int = Form(22), local_port: int = Form(2222), ssh_user: str = Form(""), ssh_host: str = Form(""), auto_reconnect: bool = Form(True), enabled: bool = Form(True)):
        from src.core.config import TunnelCfg
        c = get_ctx()
        tun = TunnelCfg(name=name, remote_host=remote_host, remote_port=remote_port, local_port=local_port, ssh_user=ssh_user, ssh_host=ssh_host, auto_reconnect=auto_reconnect, enabled=enabled)
        r = c.forwarding.add_tunnel(tun)
        if not r.get("ok"):
            raise HTTPException(status_code=400, detail=r.get("error", "error"))
        return r

    @app.post("/api/tunnels/{name}/start")
    def tunnels_start(name: str):
        c = get_ctx()
        r = c.forwarding.start_tunnel(name)
        if not r.get("ok"):
            raise HTTPException(status_code=400, detail=r.get("error", "error"))
        return r

    @app.post("/api/tunnels/{name}/stop")
    def tunnels_stop(name: str):
        c = get_ctx()
        r = c.forwarding.stop_tunnel(name)
        if not r.get("ok"):
            raise HTTPException(status_code=400, detail=r.get("error", "error"))
        return r

    @app.post("/api/tunnels/{name}/remove")
    def tunnels_remove(name: str):
        c = get_ctx()
        r = c.forwarding.remove_tunnel(name)
        if not r.get("ok"):
            raise HTTPException(status_code=400, detail=r.get("error", "error"))
        return r

    # === VPS (Publicar a Internet) ===

    @app.get("/api/vps")
    def vps_list():
        c = get_ctx()
        vps_list = c.store.get().publish.vps_list
        return {"vps": [v.model_dump() for v in vps_list]}

    @app.post("/api/vps")
    def vps_add(id: str = Form(...), host: str = Form(...), user: str = Form("root"), port: int = Form(22), identity_file: str = Form("")):
        from src.core.config import VpsCfg
        c = get_ctx()
        vps = VpsCfg(id=id, host=host, user=user, port=port, identity_file=identity_file)
        try:
            c.store.add_vps(vps)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"ok": True, "id": vps.id}

    @app.delete("/api/vps/{vps_id}")
    def vps_remove(vps_id: str):
        c = get_ctx()
        try:
            c.store.remove_vps(vps_id)
        except Exception as e:
            raise HTTPException(status_code=404, detail=str(e))
        return {"ok": True, "id": vps_id}

    @app.post("/api/vps/{vps_id}/connect")
    def vps_connect(vps_id: str, name: str = Form(""), remote_port: int = Form(80), local_port: int = Form(8080)):
        from src.core.config import TunnelCfg
        c = get_ctx()
        vps = c.store.get_vps(vps_id)
        if not vps:
            raise HTTPException(status_code=404, detail=f"vps '{vps_id}' no existe")
        tun_name = name or f"pub-{vps_id}"
        tun = TunnelCfg(
            name=tun_name, remote_host=vps.host, remote_port=remote_port,
            local_port=local_port, ssh_user=vps.user, ssh_host=vps.host,
            auto_reconnect=True, enabled=True,
        )
        r = c.forwarding.add_tunnel(tun)
        if not r.get("ok"):
            raise HTTPException(status_code=400, detail=r.get("error", "error"))
        r2 = c.forwarding.start_tunnel(tun_name)
        if not r2.get("ok"):
            raise HTTPException(status_code=400, detail=r2.get("error", "error"))
        return {"ok": True, "tunnel": tun_name, "vps": vps_id}

    @app.post("/api/vps/{vps_id}/disconnect")
    def vps_disconnect(vps_id: str):
        c = get_ctx()
        vps = c.store.get_vps(vps_id)
        if not vps:
            raise HTTPException(status_code=404, detail=f"vps '{vps_id}' no existe")
        cfg = c.store.get()
        closed = 0
        for t in cfg.forwarding.tunnels:
            if (t.ssh_host == vps.host or t.remote_host == vps.host) and t.enabled:
                r = c.forwarding.stop_tunnel(t.name)
                if r.get("ok"):
                    closed += 1
        return {"ok": True, "closed": closed, "vps": vps_id}

    # === Config ===

    @app.get("/api/config")
    def config_get():
        c = get_ctx()
        cfg = c.store.get()
        data = cfg.model_dump(by_alias=True, exclude_none=True)
        return {"config": data}

    @app.post("/api/config")
    def config_save(payload: dict):
        from pydantic import ValidationError as _VE
        from src.core.config import AppConfig
        c = get_ctx()
        content = payload.get("content", "")
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"JSON invalido: {e}")
        try:
            new_cfg = AppConfig.model_validate(data)
        except _VE as e:
            raise HTTPException(status_code=400, detail=f"Config invalida: {e}")
        c.store.save(new_cfg)
        # Reload config in context
        c.config = new_cfg
        c.metrics.log_event("web_config", message="config.json guardado desde el panel web")
        return {"ok": True, "message": "configuracion guardada"}

    # === Settings (UI-focused subset of config) ===

    @app.get("/api/settings")
    def settings_get():
        c = get_ctx()
        cfg = c.store.get()
        return {
            "settings": {
                # UI
                "theme": cfg.ui.theme,
                "refresh_interval_seconds": cfg.ui.refresh_interval_seconds,
                "start_minimized": cfg.ui.start_minimized,
                "close_to_tray": cfg.ui.close_to_tray,
                "log_level": cfg.ui.log_level,
                "logs_dir": cfg.ui.logs_dir,
                "language": cfg.ui.language,
                "web_panel_enabled": cfg.ui.web_panel_enabled,
                # On close
                "stop_distros": cfg.on_close.stop_distros,
                # API
                "api_enabled": cfg.api.enabled,
                "api_port": cfg.api.port,
                # Alerts
                "alert_memory_percent": cfg.alerts.memory_percent,
                "alert_check_interval": cfg.alerts.check_interval_seconds,
                "alert_distro_stopped": cfg.alerts.distro_stopped_unexpected,
                # Snapshots
                "snapshots_enabled": cfg.snapshots.enabled,
                "snapshots_retention": cfg.snapshots.retention_days,
            }
        }

    @app.post("/api/settings")
    def settings_save(data: dict):
        c = get_ctx()
        cfg = c.store.get()

        # UI settings
        cfg.ui.theme = data.get("theme", cfg.ui.theme)
        cfg.ui.refresh_interval_seconds = int(data.get("refresh_interval_seconds", cfg.ui.refresh_interval_seconds))
        cfg.ui.start_minimized = data.get("start_minimized", cfg.ui.start_minimized)
        cfg.ui.close_to_tray = data.get("close_to_tray", cfg.ui.close_to_tray)
        cfg.ui.log_level = data.get("log_level", cfg.ui.log_level)
        cfg.ui.logs_dir = data.get("logs_dir", cfg.ui.logs_dir)
        cfg.ui.language = data.get("language", cfg.ui.language)
        cfg.ui.web_panel_enabled = data.get("web_panel_enabled", cfg.ui.web_panel_enabled)

        # On close
        cfg.on_close.stop_distros = data.get("stop_distros", cfg.on_close.stop_distros)

        # API
        cfg.api.enabled = data.get("api_enabled", cfg.api.enabled)
        api_port = int(data.get("api_port", cfg.api.port))
        if 1024 <= api_port <= 65535:
            cfg.api.port = api_port

        # Alerts
        cfg.alerts.memory_percent = int(data.get("alert_memory_percent", cfg.alerts.memory_percent))
        cfg.alerts.check_interval_seconds = int(data.get("alert_check_interval", cfg.alerts.check_interval_seconds))
        cfg.alerts.distro_stopped_unexpected = data.get("alert_distro_stopped", cfg.alerts.distro_stopped_unexpected)

        # Snapshots
        cfg.snapshots.enabled = data.get("snapshots_enabled", cfg.snapshots.enabled)
        cfg.snapshots.retention_days = int(data.get("snapshots_retention", cfg.snapshots.retention_days))

        c.store.save(cfg)
        c.config = cfg
        c.metrics.log_event("web_settings", message="ajustes guardados desde el panel web")
        return {"ok": True, "message": "ajustes guardados"}

    return app
