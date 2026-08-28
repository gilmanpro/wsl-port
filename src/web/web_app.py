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
  <button class="nav-tab" onclick="showPage('vps')">VPS</button>
  <button class="nav-tab" onclick="showPage('profiles')">Perfiles</button>
  <button class="nav-tab" onclick="showPage('scheduler')">Programador</button>
  <button class="nav-tab" onclick="showPage('autostart')">Autoarranque</button>
  <button class="nav-tab" onclick="showPage('monitor')">Monitor</button>
  <button class="nav-tab" onclick="showPage('resources')">Recursos</button>
  <button class="nav-tab" onclick="showPage('config')">Configuracion</button>
  <button class="nav-tab" onclick="showPage('settings')">Ajustes</button>
  <button class="nav-tab" onclick="showPage('logs')">Logs</button>
  <div style="flex:1"></div>
  <span class="muted" id="clock" style="padding-right:8px"></span>
</nav>

<!-- ======================== DASHBOARD ======================== -->
<div class="page active" id="page-dashboard">
  <div class="page-header" style="display:flex;justify-content:space-between;align-items:flex-start">
    <div>
      <h2>Dashboard</h2>
      <div class="sub">Estado de distros, metricas y alertas</div>
    </div>
    <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">
      <input class="form-input" id="dash-filter" placeholder="Filtrar distros..." style="width:180px;padding:5px 10px;font-size:12px" oninput="filterDashCards()">
      <button class="btn btn-ok" onclick="startAll()">Iniciar todas</button>
      <button class="btn btn-danger" onclick="shutdownAll()">Detener todas</button>
    </div>
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

<!-- ======================== VPS ======================== -->
<div class="page" id="page-vps">
  <div class="page-header" style="display:flex;justify-content:space-between;align-items:flex-start">
    <div>
      <h2>VPS</h2>
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

<!-- ======================== PROFILES ======================== -->
<div class="page" id="page-profiles">
  <div class="page-header" style="display:flex;justify-content:space-between;align-items:flex-start">
    <div>
      <h2>Perfiles</h2>
      <div class="sub">Captura y aplica conjuntos de distros</div>
    </div>
    <div style="display:flex;gap:6px;flex-wrap:wrap">
      <button class="btn btn-ok" onclick="openModal('capture-profile-modal')">Capturar</button>
      <button class="btn btn-blue" onclick="editProfile()">Editar</button>
      <button class="btn" onclick="applyProfile()">Aplicar</button>
      <button class="btn" onclick="loadProfiles()">&#x21bb; Refrescar</button>
    </div>
  </div>

  <div class="table-wrap">
    <table id="profiles-table">
      <thead><tr><th>Nombre</th><th>Descripcion</th><th>Distros a iniciar</th><th>Activo</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>
</div>

<!-- ======================== SCHEDULER ======================== -->
<div class="page" id="page-scheduler">
  <div class="page-header" style="display:flex;justify-content:space-between;align-items:flex-start">
    <div>
      <h2>Programador</h2>
      <div class="sub">Tareas programadas automaticas</div>
    </div>
    <div style="display:flex;gap:6px;flex-wrap:wrap">
      <button class="btn btn-ok" onclick="openSchedulerModal()">Nueva tarea</button>
      <button class="btn btn-blue" onclick="editSchedulerTask()">Editar</button>
      <button class="btn btn-danger" onclick="removeSchedulerTask()">Eliminar</button>
      <button class="btn" onclick="runSchedulerTask()">Ejecutar ahora</button>
      <button class="btn" onclick="loadScheduler()">&#x21bb; Refrescar</button>
    </div>
  </div>

  <div class="table-wrap">
    <table id="scheduler-table">
      <thead><tr><th>ID</th><th>Nombre</th><th>Accion</th><th>Destino</th><th>Hora</th><th>Dias</th><th>Habilitada</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>
</div>

<!-- ======================== AUTOSTART ======================== -->
<div class="page" id="page-autostart">
  <div class="page-header" style="display:flex;justify-content:space-between;align-items:flex-start">
    <div>
      <h2>Autoarranque</h2>
      <div class="sub">Distros que se inician al iniciar Windows</div>
    </div>
    <div style="display:flex;gap:6px;flex-wrap:wrap">
      <button class="btn btn-ok" onclick="openModal('add-autostart-modal')">Activar</button>
      <button class="btn btn-blue" onclick="editAutostart()">Editar</button>
      <button class="btn btn-warn" onclick="disableAutostart()">Desactivar</button>
      <button class="btn" onclick="loadAutostart()">&#x21bb; Refrescar</button>
    </div>
  </div>

  <div class="table-wrap">
    <table id="autostart-table">
      <thead><tr><th>Distro</th><th>Delay (s)</th><th>Comando</th><th>Estado</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>
</div>

<!-- ======================== MONITOR ======================== -->
<div class="page" id="page-monitor">
  <div class="page-header">
    <h2>Monitor</h2>
    <div class="sub">Metricas en tiempo real (actualiza cada 5s)</div>
  </div>

  <div class="stats-row" id="monitor-stats"></div>

  <div class="table-wrap">
    <table id="monitor-table">
      <thead><tr><th>Nombre</th><th>Estado</th><th>RAM usada/total</th><th>%</th><th>CPU</th><th>Uptime</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>
</div>

<!-- ======================== RESOURCES ======================== -->
<div class="page" id="page-resources">
  <div class="page-header">
    <h2>Recursos</h2>
    <div class="sub">Limites globales de WSL (.wslconfig)</div>
  </div>

  <div class="stats-row" id="resources-stats"></div>

  <div class="settings-section" style="max-width:600px">
    <h3>Limites Globales</h3>
    <div class="form-group">
      <label>Memoria (GB)</label>
      <input class="form-input" type="number" id="res-memory" min="0.5" max="256" step="0.5" placeholder="(sin limite)">
    </div>
    <div class="form-group">
      <label>Procesadores</label>
      <input class="form-input" type="number" id="res-processors" min="1" max="256" placeholder="(sin limite)">
    </div>
    <div class="form-group">
      <label>Swap (GB)</label>
      <input class="form-input" type="number" id="res-swap" min="0" max="256" step="0.5" placeholder="(sin limite)">
    </div>
    <div class="form-group">
      <label>Auto Memory Reclaim</label>
      <select class="form-input" id="res-auto-reclaim">
        <option value="">(sin configurar)</option>
        <option value="gradual">gradual</option>
        <option value="dropcache">dropcache</option>
        <option value="disabled">disabled</option>
      </select>
    </div>
    <div class="toggle">
      <input type="checkbox" id="res-sparse-vhd">
      <span>Sparse VHD</span>
    </div>
    <div style="margin-top:16px;display:flex;gap:8px">
      <button class="btn btn-ok" onclick="applyResources()">Aplicar limites</button>
      <button class="btn btn-warn" onclick="resetResources()">Restablecer</button>
    </div>
  </div>
</div>

<!-- ======================== LOGS ======================== -->
<div class="page" id="page-logs">
  <div class="page-header" style="display:flex;justify-content:space-between;align-items:flex-start">
    <div>
      <h2>Logs</h2>
      <div class="sub">Eventos del sistema</div>
    </div>
    <button class="btn" onclick="loadLogs()">&#x21bb; Refrescar</button>
  </div>

  <div class="stats-row" id="logs-stats"></div>

  <div class="table-wrap">
    <div id="logs-container" style="max-height:600px;overflow-y:auto;padding:12px;font-family:'Consolas','Fira Code',monospace;font-size:12px;line-height:1.6"></div>
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
        <label>Contraseña del panel</label>
        <input class="form-input" type="password" id="set-web-password" placeholder="Contraseña de acceso">
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

<!-- Edit Forward Modal -->
<div class="modal-overlay" id="edit-fwd-modal">
  <div class="modal">
    <h3>Editar Forward</h3>
    <div class="form-row">
      <div class="form-group">
        <label>Nombre</label>
        <input class="form-input" id="edit-fwd-name" readonly style="opacity:0.6">
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Puerto Local</label>
        <input class="form-input" id="edit-fwd-local-port" type="number" min="1" max="65535">
      </div>
      <div class="form-group">
        <label>WSL Port</label>
        <input class="form-input" id="edit-fwd-wsl-port" type="number" min="1" max="65535">
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>WSL IP</label>
        <input class="form-input" id="edit-fwd-wsl-ip">
      </div>
      <div class="form-group">
        <label>&nbsp;</label>
        <div class="toggle" style="padding-top:8px">
          <input type="checkbox" id="edit-fwd-enabled" checked>
          <span>Habilitado</span>
        </div>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn" onclick="closeModal('edit-fwd-modal')">Cancelar</button>
      <button class="btn btn-ok" onclick="saveFwdEdit()">Guardar</button>
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

<!-- Edit Tunnel Modal -->
<div class="modal-overlay" id="edit-tun-modal">
  <div class="modal">
    <h3>Editar Tunnel SSH</h3>
    <div class="form-row">
      <div class="form-group">
        <label>Nombre</label>
        <input class="form-input" id="edit-tun-name" readonly style="opacity:0.6">
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Host Remoto</label>
        <input class="form-input" id="edit-tun-remote-host">
      </div>
      <div class="form-group">
        <label>Puerto Remoto</label>
        <input class="form-input" id="edit-tun-remote-port" type="number" min="1" max="65535">
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Puerto Local</label>
        <input class="form-input" id="edit-tun-local-port" type="number" min="1" max="65535">
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Usuario SSH</label>
        <input class="form-input" id="edit-tun-ssh-user">
      </div>
      <div class="form-group">
        <label>SSH Host</label>
        <input class="form-input" id="edit-tun-ssh-host">
      </div>
    </div>
    <div style="display:flex;gap:16px;margin-top:8px">
      <div class="toggle">
        <input type="checkbox" id="edit-tun-auto" checked>
        <span>Reconexion automatica</span>
      </div>
      <div class="toggle">
        <input type="checkbox" id="edit-tun-enabled" checked>
        <span>Habilitado</span>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn" onclick="closeModal('edit-tun-modal')">Cancelar</button>
      <button class="btn btn-ok" onclick="saveTunEdit()">Guardar</button>
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

<!-- Edit VPS Modal -->
<div class="modal-overlay" id="edit-vps-modal">
  <div class="modal">
    <h3>Editar VPS</h3>
    <div class="form-row">
      <div class="form-group">
        <label>ID</label>
        <input class="form-input" id="edit-vps-id" readonly style="opacity:0.6">
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Host (IP o dominio)</label>
        <input class="form-input" id="edit-vps-host">
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Usuario SSH</label>
        <input class="form-input" id="edit-vps-user">
      </div>
      <div class="form-group">
        <label>Puerto SSH</label>
        <input class="form-input" id="edit-vps-port" type="number" min="1" max="65535">
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Clave SSH (ruta, opcional)</label>
        <input class="form-input" id="edit-vps-identity">
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn" onclick="closeModal('edit-vps-modal')">Cancelar</button>
      <button class="btn btn-ok" onclick="saveVpsEdit()">Guardar</button>
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

<!-- Capture Profile Modal -->
<div class="modal-overlay" id="capture-profile-modal">
  <div class="modal">
    <h3>Capturar Perfil</h3>
    <p style="font-size:13px;color:#b8c0cf;margin-bottom:12px">Captura las distros actualmente en ejecucion como un perfil.</p>
    <div class="form-group">
      <label>Nombre del perfil</label>
      <input class="form-input" id="profile-capture-name" placeholder="mi-perfil">
    </div>
    <div class="form-group">
      <label>Descripcion (opcional)</label>
      <input class="form-input" id="profile-capture-desc" placeholder="Descripcion del perfil">
    </div>
    <div class="modal-footer">
      <button class="btn" onclick="closeModal('capture-profile-modal')">Cancelar</button>
      <button class="btn btn-ok" onclick="captureProfile()">Capturar</button>
    </div>
  </div>
</div>

<!-- Edit Profile Modal -->
<div class="modal-overlay" id="edit-profile-modal">
  <div class="modal">
    <h3>Editar Perfil</h3>
    <div class="form-group">
      <label>Nombre del perfil</label>
      <input class="form-input" id="profile-edit-name" placeholder="nombre">
    </div>
    <div class="form-group">
      <label>Descripcion</label>
      <input class="form-input" id="profile-edit-desc" placeholder="descripcion">
    </div>
    <div class="form-group">
      <label>Distros a iniciar</label>
      <div id="profile-edit-distros" style="max-height:200px;overflow-y:auto;padding:8px;background:#14181f;border-radius:6px;border:1px solid #39445c"></div>
    </div>
    <div class="modal-footer">
      <button class="btn" onclick="closeModal('edit-profile-modal')">Cancelar</button>
      <button class="btn btn-ok" onclick="saveProfileEdit()">Guardar</button>
    </div>
  </div>
</div>

<!-- Scheduler Task Modal -->
<div class="modal-overlay" id="scheduler-modal">
  <div class="modal">
    <h3 id="scheduler-modal-title">Nueva Tarea</h3>
    <input type="hidden" id="sched-edit-id" value="">
    <div class="form-group">
      <label>Nombre</label>
      <input class="form-input" id="sched-name" placeholder="mi-tarea">
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Tipo de accion</label>
        <select class="form-input" id="sched-action-type">
          <option value="distro_start">Iniciar distro</option>
          <option value="distro_stop">Detener distro</option>
          <option value="apply_profile">Aplicar perfil</option>
          <option value="snapshot">Snapshot</option>
        </select>
      </div>
      <div class="form-group">
        <label>Distro / Perfil</label>
        <input class="form-input" id="sched-target" placeholder="nombre de distro o perfil">
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label>Hora (HH:MM)</label>
        <input class="form-input" type="time" id="sched-time" value="09:00">
      </div>
    </div>
    <div class="form-group">
      <label>Dias</label>
      <div style="display:flex;gap:4px;flex-wrap:wrap;margin-top:4px">
        <label class="toggle"><input type="checkbox" class="sched-day" value="mon" checked><span>Lun</span></label>
        <label class="toggle"><input type="checkbox" class="sched-day" value="tue" checked><span>Mar</span></label>
        <label class="toggle"><input type="checkbox" class="sched-day" value="wed" checked><span>Mie</span></label>
        <label class="toggle"><input type="checkbox" class="sched-day" value="thu" checked><span>Jue</span></label>
        <label class="toggle"><input type="checkbox" class="sched-day" value="fri" checked><span>Vie</span></label>
        <label class="toggle"><input type="checkbox" class="sched-day" value="sat"><span>Sab</span></label>
        <label class="toggle"><input type="checkbox" class="sched-day" value="sun"><span>Dom</span></label>
      </div>
    </div>
    <div class="toggle" style="margin-top:8px">
      <input type="checkbox" id="sched-enabled" checked>
      <span>Habilitada</span>
    </div>
    <div class="modal-footer">
      <button class="btn" onclick="closeModal('scheduler-modal')">Cancelar</button>
      <button class="btn btn-ok" onclick="saveSchedulerTask()">Guardar</button>
    </div>
  </div>
</div>

<!-- Autostart Enable Modal -->
<div class="modal-overlay" id="add-autostart-modal">
  <div class="modal">
    <h3>Activar Autoarranque</h3>
    <div class="form-group">
      <label>Distro</label>
      <select class="form-input" id="autostart-distro"></select>
    </div>
    <div class="form-group">
      <label>Retraso (segundos)</label>
      <input class="form-input" type="number" id="autostart-delay" min="0" max="300" value="0">
    </div>
    <div class="modal-footer">
      <button class="btn" onclick="closeModal('add-autostart-modal')">Cancelar</button>
      <button class="btn btn-ok" onclick="enableAutostart()">Activar</button>
    </div>
  </div>
</div>

<!-- Autostart Edit Modal -->
<div class="modal-overlay" id="edit-autostart-modal">
  <div class="modal">
    <h3>Editar Autoarranque</h3>
    <input type="hidden" id="edit-autostart-distro" value="">
    <div class="form-group">
      <label>Retraso (segundos)</label>
      <input class="form-input" type="number" id="edit-autostart-delay" min="0" max="300" value="0">
    </div>
    <div class="modal-footer">
      <button class="btn" onclick="closeModal('edit-autostart-modal')">Cancelar</button>
      <button class="btn btn-ok" onclick="saveAutostartEdit()">Guardar</button>
    </div>
  </div>
</div>

<!-- Clone Distro Modal -->
<div class="modal-overlay" id="clone-modal">
  <div class="modal">
    <h3>Clonar Distro</h3>
    <p style="font-size:13px;color:#b8c0cf;margin-bottom:12px">Clonar: <b id="clone-source"></b></p>
    <div class="form-group">
      <label>Nombre para la copia</label>
      <input class="form-input" id="clone-target-name" placeholder="mi-distro-copia">
    </div>
    <div class="modal-footer">
      <button class="btn" onclick="closeModal('clone-modal')">Cancelar</button>
      <button class="btn btn-ok" onclick="doClone()">Clonar</button>
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
const ALL_PAGES = ['dashboard','forwards','tunnels','vps','profiles','scheduler','autostart','monitor','resources','config','settings','logs'];
function showPage(name) {
  currentPage = name;
  $$('.page').forEach(p => p.classList.remove('active'));
  $$('.nav-tab').forEach(t => t.classList.remove('active'));
  const page = $('#page-' + name);
  if (page) page.classList.add('active');
  const tabs = $$('.nav-tab');
  const idx = ALL_PAGES.indexOf(name);
  if (idx >= 0 && tabs[idx]) tabs[idx].classList.add('active');
  if (name === 'profiles') loadProfiles();
  if (name === 'scheduler') loadScheduler();
  if (name === 'autostart') loadAutostart();
  if (name === 'monitor') loadMonitor();
  if (name === 'resources') loadResources();
  if (name === 'logs') loadLogs();
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
let _dashDistros = [];
let _dashFilter = '';
function filterDashCards() {
  _dashFilter = ($('#dash-filter')?.value || '').toLowerCase();
  renderDashCards();
}
function renderDashCards() {
  const filtered = _dashDistros.filter(d => !_dashFilter || d.name.toLowerCase().includes(_dashFilter));
  $('#cards').innerHTML = filtered.map(d => {
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
      <div class="btns" style="margin-top:4px">
        <button class="btn btn-sm" onclick="distroAction('shell','${esc(d.name)}')">Terminal</button>
        <button class="btn btn-sm" onclick="distroAction('explorer','${esc(d.name)}')">Explorador</button>
        <button class="btn btn-sm" onclick="distroAction('export','${esc(d.name)}')">Exportar</button>
        <button class="btn btn-sm" onclick="openCloneModal('${esc(d.name)}')">Clonar</button>
      </div>
    </div>`;
  }).join('') || '<div class="card"><span class="muted">Sin distros detectadas</span></div>';
}

async function loadDashboard() {
  try {
    const st = await api('/api/status');
    const distros = st.distros || [];
    _dashDistros = distros;
    const running = distros.filter(d => d.running).length;
    const total = distros.length;

    $('#dash-stats').innerHTML = `
      <div class="stat-card"><div class="label">Distro</div><div class="value green">${running}/${total}</div></div>
      <div class="stat-card"><div class="label">Ejecutando</div><div class="value blue">${running}</div></div>
      <div class="stat-card"><div class="label">Detenidas</div><div class="value orange">${total - running}</div></div>
      <div class="stat-card"><div class="label">Alertas</div><div class="value red" id="alert-count">-</div></div>
    `;

    renderDashCards();

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
      `<div class="alert"><div><b>${esc(a.tipo)}</b> &mdash; ${esc(a.message)}</div><span class="muted">${new Date(a.ts*1000).toLocaleTimeString()}</span></div>`
    ).join('') : '<span class="muted">sin alertas</span>';
  } catch(e) { console.error('dashboard error:', e); }
}

async function act(action, name) {
  toast('Iniciando ' + action + '...');
  try {
    await api('/api/distros/' + encodeURIComponent(name) + '/' + action, 'POST');
    toast(name + ': ' + action + ' OK');
  } catch(e) { toast('Error: ' + e.message, true); }
  setTimeout(loadAll, 800);
}

async function distroAction(action, name) {
  toast('Iniciando ' + action + '...');
  try {
    await api('/api/distros/' + encodeURIComponent(name) + '/' + action, 'POST');
    if (action === 'export') toast('Exportado a escritorio');
    else toast(action + ' OK para ' + name);
  } catch(e) { toast('Error: ' + e.message, true); }
  setTimeout(loadAll, 800);
}

function openCloneModal(name) {
  $('#clone-source').textContent = name;
  $('#clone-source').dataset.name = name;
  $('#clone-target-name').value = name + '-copia';
  openModal('clone-modal');
}

async function doClone() {
  const source = $('#clone-source').dataset.name;
  const target = $('#clone-target-name').value.trim();
  if (!target) { toast('Nombre requerido', true); return; }
  toast('Clonando ' + source + '...');
  try {
    await api('/api/distros/' + encodeURIComponent(source) + '/clone', 'POST', { target_name: target });
    toast('Clonada como "' + target + '" OK');
    closeModal('clone-modal');
  } catch(e) { toast('Error: ' + e.message, true); }
  setTimeout(loadAll, 1500);
}

function startAll() {
  confirmAction('Iniciar todas', '\u00bfIniciar todas las distros?', async () => {
    toast('Iniciando todas las distros...');
    try {
      const r = await api('/api/start-all', 'POST');
      toast('Iniciadas: ' + (r.started || []).length + ' distros');
    } catch(e) { toast('Error: ' + e.message, true); }
    setTimeout(loadAll, 1500);
  });
}

function shutdownAll() {
  confirmAction('Detener todas', '\u00bfDetener todas las distros en ejecucion?', async () => {
    toast('Deteniendo todas las distros...');
    try {
      await api('/api/shutdown', 'POST');
      toast('Todas las distros detenidas');
    } catch(e) { toast('Error: ' + e.message, true); }
    setTimeout(loadAll, 1500);
  });
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
        <button class="btn btn-blue btn-sm" onclick="editFwd('${esc(f.name)}')">Editar</button>
        <button class="btn btn-danger btn-sm" onclick="fwdRemove('${esc(f.name)}')">Eliminar</button>
      </td>
    </tr>`).join('') : '<tr><td colspan="7" class="muted" style="text-align:center;padding:24px">Sin forwards configurados. Haz clic en "+ Agregar" para crear uno.</td></tr>';
  } catch(e) { console.error('forwards error:', e); }
}

async function fwdAct(action, name) {
  toast('Iniciando forward...');
  try {
    await api('/api/forwards/' + encodeURIComponent(name) + '/' + action, 'POST');
    toast('Forward ' + name + ': ' + action + ' OK');
  } catch(e) { toast('Error: ' + e.message, true); }
  setTimeout(loadAll, 800);
}

function fwdRemove(name) {
  confirmAction('Eliminar Forward', '\u00bfEliminar el forward "' + name + '"?', async () => {
    toast('Eliminando forward...');
    try {
      await api('/api/forwards/' + encodeURIComponent(name) + '/remove', 'POST');
      toast('Forward ' + name + ' eliminado');
    } catch(e) { toast('Error: ' + e.message, true); }
    setTimeout(loadAll, 800);
  });
}

function editFwd(name) {
  api('/api/forwards').then(fw => {
    const f = (fw.forwards || []).find(x => x.name === name);
    if (!f) { toast('Forward no encontrado', true); return; }
    $('#edit-fwd-name').value = f.name;
    $('#edit-fwd-local-port').value = f.local_port;
    $('#edit-fwd-wsl-port').value = f.wsl_port;
    $('#edit-fwd-wsl-ip').value = f.wsl_ip || '127.0.0.1';
    $('#edit-fwd-enabled').checked = f.enabled;
    openModal('edit-fwd-modal');
  }).catch(e => toast('Error: ' + e.message, true));
}

async function saveFwdEdit() {
  const name = $('#edit-fwd-name').value;
  toast('Guardando forward...');
  try {
    await api('/api/forwards/' + encodeURIComponent(name) + '/remove', 'POST');
    await api('/api/forwards', 'POST', {
      name,
      local_port: parseInt($('#edit-fwd-local-port').value),
      wsl_port: parseInt($('#edit-fwd-wsl-port').value),
      wsl_ip: $('#edit-fwd-wsl-ip').value || '127.0.0.1',
      enabled: $('#edit-fwd-enabled').checked,
    });
    toast('Forward "' + name + '" actualizado');
    closeModal('edit-fwd-modal');
  } catch(e) { toast('Error: ' + e.message, true); }
  setTimeout(loadAll, 800);
}

function fwdApplyAll() {
  confirmAction('Aplicar todos', '\u00bfAplicar todas las reglas netsh para forwards habilitados?', async () => {
    toast('Aplicando forwards...');
    try {
      const r = await api('/api/forwards/apply-all', 'POST');
      toast('Aplicados: ' + r.applied + '/' + r.total);
    } catch(e) { toast('Error: ' + e.message, true); }
    setTimeout(loadAll, 800);
  });
}

function fwdClearAll() {
  confirmAction('Limpiar todo', '\u00bfEliminar TODAS las reglas netsh? Esto es destructivo.', async () => {
    toast('Limpiando forwards...');
    try {
      const r = await api('/api/forwards/clear-all', 'POST');
      toast('Limpiados: ' + r.cleared + ' forwards');
    } catch(e) { toast('Error: ' + e.message, true); }
    setTimeout(loadAll, 800);
  });
}

async function addForward() {
  const name = $('#fwd-name').value.trim();
  if (!name) { toast('El nombre es obligatorio', true); return; }
  toast('Agregando forward...');
  const fd = new FormData();
  fd.append('name', name);
  fd.append('local_port', $('#fwd-local-port').value);
  fd.append('wsl_port', $('#fwd-wsl-port').value);
  fd.append('wsl_ip', $('#fwd-wsl-ip').value || '127.0.0.1');
  fd.append('enabled', $('#fwd-enabled').checked);
  try {
    await api('/api/forwards', 'POST', fd);
    toast('Forward "' + name + '" agregado OK');
    closeModal('add-fwd-modal');
    $('#fwd-name').value = '';
    $('#fwd-local-port').value = '8080';
    $('#fwd-wsl-port').value = '80';
    $('#fwd-wsl-ip').value = '127.0.0.1';
  } catch(e) { toast('Error: ' + e.message, true); }
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
        <button class="btn btn-blue btn-sm" onclick="editTun('${esc(t.name)}')">Editar</button>
        <button class="btn btn-danger btn-sm" onclick="tunRemove('${esc(t.name)}')">Eliminar</button>
      </td>
    </tr>`).join('') : '<tr><td colspan="9" class="muted" style="text-align:center;padding:24px">Sin tunnels configurados. Haz clic en "+ Agregar" para crear uno.</td></tr>';
  } catch(e) { console.error('tunnels error:', e); }
}

async function tunAct(action, name) {
  toast('Iniciando tunnel...');
  try {
    await api('/api/tunnels/' + encodeURIComponent(name) + '/' + action, 'POST');
    toast('Tunnel ' + name + ': ' + action + ' OK');
  } catch(e) { toast('Error: ' + e.message, true); }
  setTimeout(loadAll, 800);
}

function tunRemove(name) {
  confirmAction('Eliminar Tunnel', '\u00bfEliminar el tunnel "' + name + '"?', async () => {
    toast('Eliminando tunnel...');
    try {
      await api('/api/tunnels/' + encodeURIComponent(name) + '/remove', 'POST');
      toast('Tunnel ' + name + ' eliminado');
    } catch(e) { toast('Error: ' + e.message, true); }
    setTimeout(loadAll, 800);
  });
}

function editTun(name) {
  api('/api/tunnels').then(tn => {
    const t = (tn.tunnels || []).find(x => x.name === name);
    if (!t) { toast('Tunnel no encontrado', true); return; }
    $('#edit-tun-name').value = t.name;
    $('#edit-tun-remote-host').value = t.remote_host;
    $('#edit-tun-remote-port').value = t.remote_port;
    $('#edit-tun-local-port').value = t.local_port;
    $('#edit-tun-ssh-user').value = t.ssh_user || 'root';
    $('#edit-tun-ssh-host').value = t.ssh_host || '';
    $('#edit-tun-auto').checked = t.auto_reconnect;
    $('#edit-tun-enabled').checked = t.enabled;
    openModal('edit-tun-modal');
  }).catch(e => toast('Error: ' + e.message, true));
}

async function saveTunEdit() {
  const name = $('#edit-tun-name').value;
  toast('Guardando tunnel...');
  try {
    await api('/api/tunnels/' + encodeURIComponent(name) + '/remove', 'POST');
    const fd = new FormData();
    fd.append('name', name);
    fd.append('remote_host', $('#edit-tun-remote-host').value);
    fd.append('remote_port', $('#edit-tun-remote-port').value);
    fd.append('local_port', $('#edit-tun-local-port').value);
    fd.append('ssh_user', $('#edit-tun-ssh-user').value);
    fd.append('ssh_host', $('#edit-tun-ssh-host').value);
    fd.append('auto_reconnect', $('#edit-tun-auto').checked);
    fd.append('enabled', $('#edit-tun-enabled').checked);
    await api('/api/tunnels', 'POST', fd);
    toast('Tunnel "' + name + '" actualizado');
    closeModal('edit-tun-modal');
  } catch(e) { toast('Error: ' + e.message, true); }
  setTimeout(loadAll, 800);
}

async function addTunnel() {
  const name = $('#tun-name').value.trim();
  if (!name) { toast('El nombre es obligatorio', true); return; }
  toast('Agregando tunnel...');
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
    toast('Tunnel "' + name + '" agregado OK');
    closeModal('add-tun-modal');
    $('#tun-name').value = '';
    $('#tun-remote-host').value = '';
    $('#tun-remote-port').value = '22';
    $('#tun-local-port').value = '2222';
    $('#tun-ssh-user').value = 'root';
    $('#tun-ssh-host').value = '';
  } catch(e) { toast('Error: ' + e.message, true); }
  setTimeout(loadAll, 800);
}

// === VPS ===
let connectVpsId = null;

async function loadPublish() {
  try {
    const vpsResp = await api('/api/vps');
    const vpsList = vpsResp.vps || [];

    const tnResp = await api('/api/tunnels');
    const allTunnels = tnResp.tunnels || [];

    const vpsHosts = {};
    vpsList.forEach(v => { vpsHosts[v.host] = v.id; });

    const pubTunnels = allTunnels.filter(t => vpsHosts[t.ssh_host] || vpsHosts[t.remote_host]);

    $('#publish-stats').innerHTML = `
      <div class="stat-card"><div class="label">VPS</div><div class="value blue">${vpsList.length}</div></div>
      <div class="stat-card"><div class="label">Tunnels Activos</div><div class="value green">${pubTunnels.filter(t => t.active).length}</div></div>
      <div class="stat-card"><div class="label">Tunnels Totales</div><div class="value orange">${pubTunnels.length}</div></div>
    `;

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
          <button class="btn btn-blue btn-sm" onclick="editVps('${esc(v.id)}')">Editar</button>
          <button class="btn btn-danger btn-sm" onclick="removeVps('${esc(v.id)}')">Eliminar</button>
        </td>
      </tr>`;
    }).join('') : '<tr><td colspan="7" class="muted" style="text-align:center;padding:24px">Sin VPS configurados. Haz clic en "+ Agregar VPS" para crear uno.</td></tr>';

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
  } catch(e) { console.error('vps error:', e); }
}

async function addVps() {
  const id = $('#vps-id').value.trim();
  if (!id) { toast('El ID es obligatorio', true); return; }
  const host = $('#vps-host').value.trim();
  if (!host) { toast('El host es obligatorio', true); return; }
  toast('Agregando VPS...');
  try {
    await api('/api/vps', 'POST', {
      id, host,
      user: $('#vps-user').value || 'root',
      port: parseInt($('#vps-port').value) || 22,
      identity_file: $('#vps-identity').value || '',
    });
    toast('VPS "' + id + '" agregado OK');
    closeModal('add-vps-modal');
    $('#vps-id').value = '';
    $('#vps-host').value = '';
    $('#vps-user').value = 'root';
    $('#vps-port').value = '22';
    $('#vps-identity').value = '';
  } catch(e) { toast('Error: ' + e.message, true); }
  setTimeout(loadAll, 800);
}

function removeVps(id) {
  confirmAction('Eliminar VPS', '\u00bfEliminar el VPS "' + id + '"?', async () => {
    toast('Eliminando VPS...');
    try {
      await api('/api/vps/' + encodeURIComponent(id), 'DELETE');
      toast('VPS ' + id + ' eliminado');
    } catch(e) { toast('Error: ' + e.message, true); }
    setTimeout(loadAll, 800);
  });
}

function editVps(id) {
  api('/api/vps').then(resp => {
    const v = (resp.vps || []).find(x => x.id === id);
    if (!v) { toast('VPS no encontrado', true); return; }
    $('#edit-vps-id').value = v.id;
    $('#edit-vps-host').value = v.host;
    $('#edit-vps-user').value = v.user || 'root';
    $('#edit-vps-port').value = v.port || 22;
    $('#edit-vps-identity').value = v.identity_file || '';
    openModal('edit-vps-modal');
  }).catch(e => toast('Error: ' + e.message, true));
}

async function saveVpsEdit() {
  const id = $('#edit-vps-id').value;
  toast('Guardando VPS...');
  try {
    await api('/api/vps/' + encodeURIComponent(id), 'DELETE');
    await api('/api/vps', 'POST', {
      id,
      host: $('#edit-vps-host').value,
      user: $('#edit-vps-user').value || 'root',
      port: parseInt($('#edit-vps-port').value) || 22,
      identity_file: $('#edit-vps-identity').value || '',
    });
    toast('VPS "' + id + '" actualizado');
    closeModal('edit-vps-modal');
  } catch(e) { toast('Error: ' + e.message, true); }
  setTimeout(loadAll, 800);
}

function openConnectVps(id) {
  connectVpsId = id;
  $('#pub-tun-name').value = 'pub-' + id;
  openModal('connect-vps-modal');
}

async function connectVps() {
  if (!connectVpsId) return;
  toast('Abriendo tunnel...');
  try {
    await api('/api/vps/' + encodeURIComponent(connectVpsId) + '/connect', 'POST', {
      name: $('#pub-tun-name').value || 'pub-' + connectVpsId,
      remote_port: parseInt($('#pub-tun-remote-port').value) || 80,
      local_port: parseInt($('#pub-tun-local-port').value) || 8080,
    });
    toast('Tunnel al VPS ' + connectVpsId + ' abierto OK');
    closeModal('connect-vps-modal');
  } catch(e) { toast('Error: ' + e.message, true); }
  setTimeout(loadAll, 800);
}

async function disconnectVps(id) {
  confirmAction('Desconectar VPS', '\u00bfCerrar todos los tunnels del VPS "' + id + '"?', async () => {
    toast('Desconectando VPS...');
    try {
      const r = await api('/api/vps/' + encodeURIComponent(id) + '/disconnect', 'POST');
      toast(r.closed + ' tunnel(s) cerrado(s)');
    } catch(e) { toast('Error: ' + e.message, true); }
    setTimeout(loadAll, 800);
  });
}

// === PROFILES ===
let _selectedProfile = null;

async function loadProfiles() {
  try {
    const r = await api('/api/profiles');
    const profiles = r.profiles || [];
    $('#profiles-table tbody').innerHTML = profiles.length ? profiles.map(p =>
      `<tr onclick="selectProfile('${esc(p.name)}')" style="cursor:pointer;${_selectedProfile===p.name?'background:#1f2a3a':''}">
        <td><b>${esc(p.name)}</b></td>
        <td>${esc(p.description || '-')}</td>
        <td>${(p.distros_to_start || []).join(', ') || '-'}</td>
        <td>${p.active ? '<span class="dot on"></span> Activo' : '<span class="dot off"></span>'}</td>
      </tr>`
    ).join('') : '<tr><td colspan="4" class="muted" style="text-align:center;padding:24px">Sin perfiles. Haz clic en "Capturar" para crear uno.</td></tr>';
  } catch(e) { console.error('profiles error:', e); }
}

function selectProfile(name) {
  _selectedProfile = name;
  loadProfiles();
}

async function captureProfile() {
  const name = $('#profile-capture-name').value.trim();
  if (!name) { toast('Nombre requerido', true); return; }
  toast('Capturando perfil...');
  try {
    await api('/api/profiles/capture', 'POST', {
      name,
      description: $('#profile-capture-desc').value || '',
    });
    toast('Perfil "' + name + '" capturado OK');
    closeModal('capture-profile-modal');
    $('#profile-capture-name').value = '';
    $('#profile-capture-desc').value = '';
    loadProfiles();
  } catch(e) { toast('Error: ' + e.message, true); }
}

async function editProfile() {
  if (!_selectedProfile) { toast('Selecciona un perfil primero', true); return; }
  try {
    const r = await api('/api/profiles');
    const profiles = r.profiles || [];
    const p = profiles.find(x => x.name === _selectedProfile);
    if (!p) { toast('Perfil no encontrado', true); return; }
    $('#profile-edit-name').value = p.name;
    $('#profile-edit-desc').value = p.description || '';
    const st = await api('/api/status');
    const allDistros = (st.distros || []).map(d => d.name);
    const selected = p.distros_to_start || [];
    $('#profile-edit-distros').innerHTML = allDistros.map(d =>
      `<div class="toggle"><input type="checkbox" class="profile-distro-cb" value="${esc(d)}" ${selected.includes(d)?'checked':''}><span>${esc(d)}</span></div>`
    ).join('') || '<span class="muted">No hay distros disponibles</span>';
    openModal('edit-profile-modal');
  } catch(e) { toast('Error: ' + e.message, true); }
}

async function saveProfileEdit() {
  const name = $('#profile-edit-name').value.trim();
  if (!name) { toast('Nombre requerido', true); return; }
  const distros = Array.from($$('.profile-distro-cb:checked')).map(cb => cb.value);
  toast('Guardando perfil...');
  try {
    await api('/api/profiles/edit', 'POST', {
      name,
      description: $('#profile-edit-desc').value || '',
      distros_to_start: distros,
    });
    toast('Perfil "' + name + '" guardado OK');
    closeModal('edit-profile-modal');
    loadProfiles();
  } catch(e) { toast('Error: ' + e.message, true); }
}

function applyProfile() {
  if (!_selectedProfile) { toast('Selecciona un perfil primero', true); return; }
  confirmAction('Aplicar Perfil', '\u00bfAplicar el perfil "' + _selectedProfile + '"? Se iniciaran/distopran las distros segun el perfil.', async () => {
    toast('Aplicando perfil...');
    try {
      await api('/api/profiles/apply/' + encodeURIComponent(_selectedProfile), 'POST');
      toast('Perfil "' + _selectedProfile + '" aplicado OK');
    } catch(e) { toast('Error: ' + e.message, true); }
    setTimeout(loadAll, 2000);
  });
}

// === SCHEDULER ===
let _selectedTask = null;

async function loadScheduler() {
  try {
    const r = await api('/api/schedule');
    const tasks = r.tasks || [];
    $('#scheduler-table tbody').innerHTML = tasks.length ? tasks.map(t => {
      const days = (t.schedule?.days || []).join(', ');
      const target = t.action?.distro || t.action?.profile || '-';
      return `<tr onclick="selectTask('${esc(t.id)}')" style="cursor:pointer;${_selectedTask===t.id?'background:#1f2a3a':''}">
        <td class="muted">${esc(t.id)}</td>
        <td><b>${esc(t.name)}</b></td>
        <td>${esc(t.action?.type || '-')}</td>
        <td>${esc(target)}</td>
        <td>${esc(t.schedule?.time || '-')}</td>
        <td class="muted">${esc(days)}</td>
        <td>${t.enabled ? '<span style="color:#2ecc71">Si</span>' : '<span style="color:#e74c3c">No</span>'}</td>
      </tr>`;
    }).join('') : '<tr><td colspan="7" class="muted" style="text-align:center;padding:24px">Sin tareas programadas. Haz clic en "Nueva tarea" para crear una.</td></tr>';
  } catch(e) { console.error('scheduler error:', e); }
}

function selectTask(id) {
  _selectedTask = id;
  loadScheduler();
}

function openSchedulerModal() {
  $('#scheduler-modal-title').textContent = 'Nueva Tarea';
  $('#sched-edit-id').value = '';
  $('#sched-name').value = '';
  $('#sched-action-type').value = 'distro_start';
  $('#sched-target').value = '';
  $$('.sched-day').forEach(cb => {
    const day = cb.value;
    cb.checked = ['mon','tue','wed','thu','fri'].includes(day);
  });
  $('#sched-enabled').checked = true;
  openModal('scheduler-modal');
}

async function editSchedulerTask() {
  if (!_selectedTask) { toast('Selecciona una tarea primero', true); return; }
  try {
    const r = await api('/api/schedule');
    const task = (r.tasks || []).find(t => t.id === _selectedTask);
    if (!task) { toast('Tarea no encontrada', true); return; }
    $('#scheduler-modal-title').textContent = 'Editar Tarea';
    $('#sched-edit-id').value = task.id;
    $('#sched-name').value = task.name || '';
    $('#sched-action-type').value = task.action?.type || 'distro_start';
    $('#sched-target').value = task.action?.distro || task.action?.profile || '';
    const days = task.schedule?.days || [];
    $$('.sched-day').forEach(cb => { cb.checked = days.includes(cb.value); });
    $('#sched-time').value = task.schedule?.time || '09:00';
    $('#sched-enabled').checked = task.enabled;
    openModal('scheduler-modal');
  } catch(e) { toast('Error: ' + e.message, true); }
}

async function saveSchedulerTask() {
  const editId = $('#sched-edit-id').value;
  const name = $('#sched-name').value.trim();
  if (!name) { toast('Nombre requerido', true); return; }
  const actionType = $('#sched-action-type').value;
  const target = $('#sched-target').value.trim();
  const days = Array.from($$('.sched-day:checked')).map(cb => cb.value);
  if (!days.length) { toast('Selecciona al menos un dia', true); return; }

  const payload = {
    name,
    action_type: actionType,
    distro: (actionType === 'apply_profile') ? null : target || null,
    profile: (actionType === 'apply_profile') ? target || null : null,
    time: $('#sched-time').value || '09:00',
    days,
    enabled: $('#sched-enabled').checked,
  };

  toast(editId ? 'Actualizando tarea...' : 'Creando tarea...');
  try {
    if (editId) {
      await api('/api/schedule/' + editId, 'DELETE');
    }
    await api('/api/schedule', 'POST', payload);
    toast('Tarea "' + name + '" guardada OK');
    closeModal('scheduler-modal');
    loadScheduler();
  } catch(e) { toast('Error: ' + e.message, true); }
}

function removeSchedulerTask() {
  if (!_selectedTask) { toast('Selecciona una tarea primero', true); return; }
  confirmAction('Eliminar tarea', '\u00bfEliminar esta tarea programada?', async () => {
    toast('Eliminando tarea...');
    try {
      await api('/api/schedule/' + _selectedTask, 'DELETE');
      toast('Tarea eliminada OK');
      _selectedTask = null;
      loadScheduler();
    } catch(e) { toast('Error: ' + e.message, true); }
  });
}

async function runSchedulerTask() {
  if (!_selectedTask) { toast('Selecciona una tarea primero', true); return; }
  toast('Ejecutando tarea...');
  try {
    await api('/api/schedule/' + _selectedTask + '/run', 'POST');
    toast('Tarea ejecutada OK');
  } catch(e) { toast('Error: ' + e.message, true); }
  setTimeout(loadAll, 1500);
}

// === AUTOSTART ===
let _selectedAutostart = null;

async function loadAutostart() {
  try {
    const r = await api('/api/autostart');
    const items = r.autostart || {};
    const entries = Object.entries(items);
    const st = await api('/api/status');
    const allDistros = (st.distros || []).map(d => d.name);
    const activeDistros = entries.map(([k]) => k);
    const available = allDistros.filter(d => !activeDistros.includes(d));
    const sel = $('#autostart-distro');
    if (sel) {
      sel.innerHTML = available.map(d => `<option value="${esc(d)}">${esc(d)}</option>`).join('') || '<option value="">(ninguna disponible)</option>';
    }

    $('#autostart-table tbody').innerHTML = entries.length ? entries.map(([distro, info]) =>
      `<tr onclick="selectAutostart('${esc(distro)}')" style="cursor:pointer;${_selectedAutostart===distro?'background:#1f2a3a':''}">
        <td><b>${esc(distro)}</b></td>
        <td>${info.delay_s ?? 0}s</td>
        <td class="muted" style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${esc(info.command || '')}">${esc(info.command || '-')}</td>
        <td><span class="dot on"></span> Activo</td>
      </tr>`
    ).join('') : '<tr><td colspan="4" class="muted" style="text-align:center;padding:24px">Sin autoarranque configurado.</td></tr>';
  } catch(e) { console.error('autostart error:', e); }
}

function selectAutostart(distro) {
  _selectedAutostart = distro;
  loadAutostart();
}

async function enableAutostart() {
  const distro = $('#autostart-distro').value;
  if (!distro) { toast('Selecciona una distro', true); return; }
  const delay = parseInt($('#autostart-delay').value) || 0;
  toast('Activando autoarranque...');
  try {
    await api('/api/autostart', 'POST', { distro, delay_s: delay });
    toast('Autoarranque activado para ' + distro);
    closeModal('add-autostart-modal');
    loadAutostart();
  } catch(e) { toast('Error: ' + e.message, true); }
}

async function editAutostart() {
  if (!_selectedAutostart) { toast('Selecciona una distro primero', true); return; }
  const r = await api('/api/autostart');
  const items = r.autostart || {};
  const info = items[_selectedAutostart];
  if (!info) { toast('No encontrado', true); return; }
  $('#edit-autostart-distro').value = _selectedAutostart;
  $('#edit-autostart-delay').value = info.delay_s || 0;
  openModal('edit-autostart-modal');
}

async function saveAutostartEdit() {
  const distro = $('#edit-autostart-distro').value;
  const delay = parseInt($('#edit-autostart-delay').value) || 0;
  toast('Actualizando autoarranque...');
  try {
    await api('/api/autostart/' + encodeURIComponent(distro) + '/edit', 'POST', { delay_s: delay });
    toast('Autoarranque actualizado OK');
    closeModal('edit-autostart-modal');
    loadAutostart();
  } catch(e) { toast('Error: ' + e.message, true); }
}

function disableAutostart() {
  if (!_selectedAutostart) { toast('Selecciona una distro primero', true); return; }
  confirmAction('Desactivar Autoarranque', '\u00bfDesactivar autoarranque para "' + _selectedAutostart + '"?', async () => {
    toast('Desactivando autoarranque...');
    try {
      await api('/api/autostart/' + encodeURIComponent(_selectedAutostart) + '/disable', 'POST');
      toast('Autoarranque desactivado');
      _selectedAutostart = null;
      loadAutostart();
    } catch(e) { toast('Error: ' + e.message, true); }
  });
}

// === MONITOR ===
async function loadMonitor() {
  try {
    const m = await api('/api/metrics');
    const metrics = m.metrics || [];
    const running = metrics.filter(x => x.running);
    const totalRam = metrics.reduce((s, x) => s + (x.ram_total_mb || 0), 0);
    const totalCpus = metrics.reduce((s, x) => s + (x.cpus || 0), 0);

    $('#monitor-stats').innerHTML = `
      <div class="stat-card"><div class="label">Distro ejecutando</div><div class="value green">${running.length}</div></div>
      <div class="stat-card"><div class="label">RAM Total</div><div class="value blue">${fmtRam(totalRam)}</div></div>
      <div class="stat-card"><div class="label">CPU Total</div><div class="value orange">${totalCpus}</div></div>
    `;

    $('#monitor-table tbody').innerHTML = metrics.length ? metrics.map(x => {
      const pct = x.ram_percent != null;
      return `<tr>
        <td>${esc(x.name)}</td>
        <td><span class="dot ${x.running ? 'on' : 'off'}"></span>${x.running ? 'RUN' : 'STOP'}</td>
        <td>${fmtRam(x.ram_used_mb)} / ${fmtRam(x.ram_total_mb)}</td>
        <td>${pct ? x.ram_percent.toFixed(0)+'%' : '-'}</td>
        <td>${x.cpus ?? '-'}</td>
        <td>${uptime(x.uptime_s)}</td>
      </tr>`;
    }).join('') : '<tr><td colspan="6" class="muted">sin metricas</td></tr>';
  } catch(e) { console.error('monitor error:', e); }
}

// === RESOURCES ===
async function loadResources() {
  try {
    const r = await api('/api/limits/global');
    const l = r.limits || {};
    $('#res-memory').value = l.memory_gb ?? '';
    $('#res-processors').value = l.processors ?? '';
    $('#res-swap').value = l.swap_gb ?? '';
    $('#res-auto-reclaim').value = l.auto_memory_reclaim ?? '';
    $('#res-sparse-vhd').checked = !!l.sparse_vhd;

    $('#resources-stats').innerHTML = `
      <div class="stat-card"><div class="label">Memoria</div><div class="value green">${l.memory_gb != null ? l.memory_gb + ' GB' : 'Sin limite'}</div></div>
      <div class="stat-card"><div class="label">CPUs</div><div class="value blue">${l.processors ?? 'Sin limite'}</div></div>
      <div class="stat-card"><div class="label">Swap</div><div class="value orange">${l.swap_gb != null ? l.swap_gb + ' GB' : 'Sin limite'}</div></div>
    `;
  } catch(e) { console.error('resources error:', e); }
}

async function applyResources() {
  toast('Aplicando limites...');
  const payload = {};
  const mem = parseFloat($('#res-memory').value);
  const procs = parseInt($('#res-processors').value);
  const swap = parseFloat($('#res-swap').value);
  const reclaim = $('#res-auto-reclaim').value;
  const sparse = $('#res-sparse-vhd').checked;
  if (!isNaN(mem) && mem > 0) payload.memory_gb = mem;
  if (!isNaN(procs) && procs > 0) payload.processors = procs;
  if (!isNaN(swap) && swap >= 0) payload.swap_gb = swap;
  if (reclaim) payload.auto_memory_reclaim = reclaim;
  payload.sparse_vhd = sparse;
  try {
    await api('/api/limits/global', 'POST', payload);
    toast('Limites aplicados OK (requiere wsl --shutdown)');
    loadResources();
  } catch(e) { toast('Error: ' + e.message, true); }
}

function resetResources() {
  confirmAction('Restablecer limites', '\u00bfRestablecer todos los limites a valores por defecto?', async () => {
    toast('Restableciendo limites...');
    try {
      await api('/api/limits/global', 'POST', {});
      toast('Limites restablecidos OK');
      loadResources();
    } catch(e) { toast('Error: ' + e.message, true); }
  });
}

// === LOGS ===
async function loadLogs() {
  try {
    const r = await api('/api/events');
    const events = r.events || [];
    const types = [...new Set(events.map(e => e.tipo || e.type || ''))];

    $('#logs-stats').innerHTML = `
      <div class="stat-card"><div class="label">Total eventos</div><div class="value blue">${events.length}</div></div>
      <div class="stat-card"><div class="label">Tipos</div><div class="value green">${types.length}</div></div>
      <div class="stat-card"><div class="label">Ultimo evento</div><div class="value orange">${events.length ? new Date((events[0].ts || 0)*1000).toLocaleTimeString() : '-'}</div></div>
    `;

    $('#logs-container').innerHTML = events.length ? events.map(e => {
      const ts = e.ts ? new Date(e.ts * 1000).toLocaleString() : '';
      const tipo = e.tipo || e.type || '';
      const target = e.target || '';
      const msg = e.message || '';
      const detail = e.detail || '';
      return `<div style="border-bottom:1px solid #2a3344;padding:6px 0">
        <span class="muted">${esc(ts)}</span> <b style="color:#3498db">${esc(tipo)}</b> ${target ? '<span style="color:#2ecc71">' + esc(target) + '</span>' : ''} &mdash; ${esc(msg)}${detail ? ' <span class="muted">' + esc(detail) + '</span>' : ''}
      </div>`;
    }).join('') : '<div class="muted" style="padding:20px;text-align:center">Sin eventos registrados</div>';
  } catch(e) { console.error('logs error:', e); }
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
    JSON.parse(content);
  } catch(e) {
    toast('JSON invalido: ' + e.message, true);
    return;
  }
  toast('Guardando configuracion...');
  try {
    await api('/api/config', 'POST', { content });
    toast('Configuracion guardada OK (con backup)');
    $('#config-status').textContent = 'Guardado: ' + new Date().toLocaleTimeString();
  } catch(e) { toast('Error: ' + e.message, true); }
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
    $('#set-web-password').value = s.web_password || '';
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
    web_password: $('#set-web-password').value || 'wsl-manager',
    language: $('#set-language').value,
  };
  toast('Guardando ajustes...');
  try {
    await api('/api/settings', 'POST', data);
    toast('Ajustes guardados OK');
    $('#settings-status').textContent = 'Guardado: ' + new Date().toLocaleTimeString();
  } catch(e) { toast('Error: ' + e.message, true); }
}

// === Load all ===
async function loadAll() {
  await loadDashboard();
  await loadForwards();
  await loadTunnels();
  await loadPublish();
  if (currentPage === 'config') await loadConfig();
  if (currentPage === 'settings') await loadSettings();
}

// Initial load
loadAll();
setInterval(loadAll, 3000);

// Auto-refresh for monitor (5s) and page-specific tabs
setInterval(() => {
  if (currentPage === 'monitor') loadMonitor();
  if (currentPage === 'logs') loadLogs();
  if (currentPage === 'config') loadConfig();
  if (currentPage === 'settings') loadSettings();
  if (currentPage === 'vps') loadPublish();
  if (currentPage === 'profiles') loadProfiles();
  if (currentPage === 'scheduler') loadScheduler();
  if (currentPage === 'autostart') loadAutostart();
  if (currentPage === 'resources') loadResources();
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
  <div class="sub">Ingresa tu contraseña</div>
  <div id="err" class="error" style="display:none"></div>
  <form method="POST" action="/login">
    <input type="password" name="password" placeholder="Contraseña" autocomplete="current-password" autofocus required>
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

    # --- Password-based auth ---
    web_password = ctx.config.ui.web_password or "wsl-manager"
    session_secret = secrets.token_urlsafe(16)
    apply_security_headers(app)

    print(f"\n{'='*60}")
    print(f"  Contraseña del panel web: {web_password}")
    print(f"  Abre: http://127.0.0.1:8791")
    print(f"{'='*60}\n")

    # --- Auth middleware ---
    UNAUTHENTICATED_PATHS = {"/login"}

    def _check_session(request: Request) -> bool:
        session_cookie = request.cookies.get("session")
        if not session_cookie:
            return False
        # Verify HMAC-signed session cookie
        try:
            import hashlib, hmac
            parts = session_cookie.split("|", 1)
            if len(parts) != 2:
                return False
            payload, sig = parts
            expected = hmac.new(session_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
            return hmac.compare_digest(sig, expected)
        except Exception:
            return False

    def _make_session_cookie() -> str:
        import hashlib, hmac
        payload = secrets.token_urlsafe(16)
        sig = hmac.new(session_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return f"{payload}|{sig}"

    class SessionAuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            path = request.url.path
            if path in UNAUTHENTICATED_PATHS:
                return await call_next(request)
            if path == "/login" and request.method == "POST":
                return await call_next(request)
            if _check_session(request):
                return await call_next(request)
            accept = request.headers.get("accept", "")
            if "application/json" in accept or request.url.path.startswith("/api/"):
                return JSONResponse(status_code=401, content={"detail": "no autenticado"})
            return RedirectResponse(url="/login", status_code=302)

    app.add_middleware(SessionAuthMiddleware)

    @app.get("/login", response_class=HTMLResponse)
    def login_page():
        return LOGIN_HTML

    @app.post("/login")
    def login_submit(password: str = Form("")):
        from starlette.responses import HTMLResponse as _HTML
        current_password = get_ctx().config.ui.web_password or "wsl-manager"
        if password == current_password:
            resp = RedirectResponse(url="/", status_code=302)
            resp.set_cookie("session", _make_session_cookie(), httponly=True, samesite="strict", max_age=86400)
            return resp
        err_html = LOGIN_HTML.replace(
            '<div id="err" class="error" style="display:none"></div>',
            '<div id="err" class="error">Contraseña incorrecta. Intenta de nuevo.</div>'
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

    # === Distro extra actions (shell, explorer, export, clone, start-all) ===

    @app.post("/api/distros/{name}/shell")
    def distro_shell(name: str):
        import subprocess
        c = get_ctx()
        try:
            subprocess.Popen(["wsl.exe", "-d", name])
            c.metrics.log_event("web_shell", name, f"terminal abierto para {name}")
            return {"ok": True}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/distros/{name}/explorer")
    def distro_explorer(name: str):
        import subprocess
        c = get_ctx()
        try:
            subprocess.Popen(["explorer.exe", f"\\\\wsl$\\{name}"])
            c.metrics.log_event("web_explorer", name, f"explorador abierto para {name}")
            return {"ok": True}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/distros/{name}/export")
    def distro_export(name: str):
        import subprocess
        from pathlib import Path
        c = get_ctx()
        try:
            import time as _time
            ts = _time.strftime("%Y%m%d_%H%M%S")
            out_path = Path.home() / "Desktop" / f"{name}_{ts}.tar"
            r = subprocess.run(
                ["wsl.exe", "--export", name, str(out_path)],
                capture_output=True, text=True, timeout=300
            )
            if r.returncode != 0:
                raise RuntimeError(r.stderr or r.stdout or "export failed")
            c.metrics.log_event("web_export", name, f"exportado a {out_path}")
            return {"ok": True, "path": str(out_path)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/distros/{name}/clone")
    def distro_clone(name: str, payload: dict):
        import subprocess
        from pathlib import Path
        c = get_ctx()
        target = payload.get("target_name", "").strip()
        if not target:
            raise HTTPException(status_code=400, detail="target_name requerido")
        try:
            import time as _time, tempfile
            ts = _time.strftime("%Y%m%d_%H%M%S")
            tmp = Path(tempfile.gettempdir()) / f"wsl_clone_{ts}.tar"
            r1 = subprocess.run(
                ["wsl.exe", "--export", name, str(tmp)],
                capture_output=True, text=True, timeout=300
            )
            if r1.returncode != 0:
                raise RuntimeError(r1.stderr or r1.stdout or "export failed for clone")
            r2 = subprocess.run(
                ["wsl.exe", "--import", target, "", str(tmp)],
                capture_output=True, text=True, timeout=300
            )
            if r2.returncode != 0:
                raise RuntimeError(r2.stderr or r2.stdout or "import failed for clone")
            try:
                tmp.unlink()
            except OSError:
                pass
            c.metrics.log_event("web_clone", name, f"clonada como '{target}'")
            return {"ok": True, "target": target}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/start-all")
    def start_all():
        c = get_ctx()
        cfg = c.store.get()
        started = []
        for inst in cfg.distros.instances:
            r = c.wsl.start(inst.name)
            if r.ok:
                started.append(inst.name)
        c.metrics.log_event("web_start_all", message=f"{len(started)} distros iniciadas")
        return {"ok": True, "started": started}

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
                "web_password": cfg.ui.web_password,
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
        cfg.ui.web_password = data.get("web_password", cfg.ui.web_password)

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

    # === Profiles ===

    @app.get("/api/profiles")
    def profiles_list():
        c = get_ctx()
        from src.core.profiles import ProfileService
        svc = ProfileService(c.store, c.wsl)
        return {"profiles": svc.list()}

    @app.post("/api/profiles/capture")
    def profiles_capture(payload: dict):
        c = get_ctx()
        from src.core.profiles import ProfileService
        name = payload.get("name", "").strip()
        description = payload.get("description", "")
        if not name:
            raise HTTPException(status_code=400, detail="nombre requerido")
        svc = ProfileService(c.store, c.wsl)
        item = svc.capture(name, description)
        c.metrics.log_event("web_profile_capture", name, f"perfil '{name}' capturado")
        return {"ok": True, "profile": item.model_dump()}

    @app.post("/api/profiles/apply/{name}")
    def profiles_apply(name: str):
        c = get_ctx()
        from src.core.profiles import ProfileService
        svc = ProfileService(c.store, c.wsl)
        try:
            ok = svc.apply(name)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))
        if not ok:
            raise HTTPException(status_code=500, detail="fallo al aplicar perfil")
        c.metrics.log_event("web_profile_apply", name, f"perfil '{name}' aplicado")
        return {"ok": True}

    @app.post("/api/profiles/edit")
    def profiles_edit(payload: dict):
        c = get_ctx()
        name = payload.get("name", "").strip()
        description = payload.get("description", "")
        distros_to_start = payload.get("distros_to_start", [])
        if not name:
            raise HTTPException(status_code=400, detail="nombre requerido")
        cfg = c.store.get()
        existing = [i for i in cfg.profiles.items if i.name != name]
        from src.core.config import ProfileItem
        item = ProfileItem(name=name, description=description, distros_to_start=distros_to_start)
        existing.append(item)
        cfg.profiles.items = existing
        c.store.save(cfg)
        c.metrics.log_event("web_profile_edit", name, f"perfil '{name}' editado")
        return {"ok": True, "profile": item.model_dump()}

    # === Scheduler ===

    @app.get("/api/schedule")
    def schedule_list():
        c = get_ctx()
        from src.core.scheduler import Scheduler as _S
        tasks = c.scheduler.list_tasks()
        return {"tasks": tasks}

    @app.post("/api/schedule")
    def schedule_add(payload: dict):
        c = get_ctx()
        import uuid
        from src.core.config import ScheduleTask, ScheduleAction, ScheduleSpec
        task_id = str(uuid.uuid4())[:8]
        task = ScheduleTask(
            id=task_id,
            name=payload.get("name", ""),
            action=ScheduleAction(
                type=payload.get("action_type", "distro_start"),
                distro=payload.get("distro", None),
                profile=payload.get("profile", None),
            ),
            schedule=ScheduleSpec(
                days=payload.get("days", ["mon", "tue", "wed", "thu", "fri"]),
                time=payload.get("time", "09:00"),
            ),
            enabled=payload.get("enabled", True),
        )
        c.scheduler.add_task(task)
        c.metrics.log_event("web_schedule_add", task.name, f"tarea '{task.name}' creada")
        return {"ok": True, "task": task.model_dump()}

    @app.post("/api/schedule/{task_id}/run")
    def schedule_run(task_id: str):
        c = get_ctx()
        ok = c.scheduler.run_task(task_id)
        if not ok:
            raise HTTPException(status_code=404, detail="tarea no encontrada o fallo")
        return {"ok": True}

    @app.delete("/api/schedule/{task_id}")
    def schedule_remove(task_id: str):
        c = get_ctx()
        ok = c.scheduler.remove_task(task_id)
        if not ok:
            raise HTTPException(status_code=404, detail="tarea no encontrada")
        c.metrics.log_event("web_schedule_remove", task_id, f"tarea '{task_id}' eliminada")
        return {"ok": True}

    # === Autostart ===

    @app.get("/api/autostart")
    def autostart_list():
        c = get_ctx()
        items = c.autostart.list_autostart()
        return {"autostart": items}

    @app.post("/api/autostart")
    def autostart_enable(payload: dict):
        c = get_ctx()
        distro = payload.get("distro", "").strip()
        delay = int(payload.get("delay_s", 0))
        if not distro:
            raise HTTPException(status_code=400, detail="distro requerida")
        r = c.autostart.set_autostart(distro, True, delay)
        if not r.ok:
            raise HTTPException(status_code=500, detail=r.error)
        c.metrics.log_event("web_autostart_enable", distro, f"autoarranque activado (delay {delay}s)")
        return {"ok": True}

    @app.post("/api/autostart/{distro}/disable")
    def autostart_disable(distro: str):
        c = get_ctx()
        r = c.autostart.set_autostart(distro, False)
        if not r.ok:
            raise HTTPException(status_code=500, detail=r.error)
        c.metrics.log_event("web_autostart_disable", distro, "autoarranque desactivado")
        return {"ok": True}

    @app.post("/api/autostart/{distro}/edit")
    def autostart_edit(distro: str, payload: dict):
        c = get_ctx()
        delay = int(payload.get("delay_s", 0))
        r = c.autostart.set_autostart(distro, True, delay)
        if not r.ok:
            raise HTTPException(status_code=500, detail=r.error)
        c.metrics.log_event("web_autostart_edit", distro, f"retraso actualizado a {delay}s")
        return {"ok": True}

    # === Resources (Global Limits) ===

    @app.get("/api/limits/global")
    def limits_global_get():
        c = get_ctx()
        limits = c.resources.get_global_limits()
        return {"limits": limits.model_dump(exclude_none=True)}

    @app.post("/api/limits/global")
    def limits_global_set(payload: dict):
        c = get_ctx()
        from src.core.config import GlobalLimits
        limits = GlobalLimits(**payload)
        r = c.resources.set_global_limits(limits)
        if not r.ok:
            raise HTTPException(status_code=500, detail=r.error)
        c.metrics.log_event("web_limits_global", message="limites globales actualizados")
        return {"ok": True, "message": r.output}

    return app
