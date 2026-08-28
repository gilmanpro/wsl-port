# Reporte de Pruebas — wsl-port

- **Fecha:** 2026-08-28
- **Version:** 0.1.0
- **Entorno:** Windows 11, Python 3.11, WSL2

---

## Resumen Ejecutivo

| Componente | Pruebas | Estado |
|------------|---------|--------|
| Unit Tests | 64 | PASS |
| Panel Web | 10 | PASS |
| API REST | 18 | PASS |
| MCP Tools | 30 | OK |
| CLI | 7 | PASS |
| GUI | 12 pestañas | OK |

---

## 1. Panel Web (puerto 8790)

### 1.1 Login y Autenticación

| # | Prueba | Método | Endpoint | Resultado |
|---|--------|--------|----------|-----------|
| 1 | Login page accessible | GET | /login | 200 OK |
| 2 | Root redirect sin auth | GET | / | 302 → /login |
| 3 | API sin auth retorna 401 | GET | /api/status | 401 |
| 4 | Login exitoso con token | POST | /login | 302 redirect |
| 5 | Acceder con cookie | GET | / (cookie) | 200 OK |
| 6 | API status con cookie | GET | /api/status | 200 JSON |
| 7 | API metrics con cookie | GET | /api/metrics | 200 JSON |
| 8 | API alerts con cookie | GET | /api/alerts | 200 JSON |
| 9 | Token incorrecto rechazado | POST | /login (bad token) | 200 con error |
| 10 | Logout (sin cookie) | GET | / | 302 redirect |

### 1.2 Endpoints del Panel Web

| Endpoint | Método | Descripción | Estado |
|----------|--------|-------------|--------|
| / | GET | Dashboard principal | OK |
| /login | GET | Pagina de login | OK |
| /login | POST | Autenticacion | OK |
| /api/status | GET | Estado de distros | OK |
| /api/metrics | GET | Metricas RAM/CPU | OK |
| /api/alerts | GET | Alertas recientes | OK |
| /api/events | GET | Eventos del journal | OK |
| /api/distros/{name}/start | POST | Iniciar distro | OK |
| /api/distros/{name}/stop | POST | Detener distro | OK |
| /api/distros/{name}/restart | POST | Reiniciar distro | OK |
| /api/distros/{name}/snapshot | POST | Crear snapshot | OK |
| /api/shutdown | POST | Apagar todas | OK |
| /api/forwards | GET | Lista forwards | OK |
| /api/forwards/{name}/start | POST | Iniciar forward | OK |
| /api/forwards/{name}/stop | POST | Detener forward | OK |
| /api/forwards/{name}/remove | POST | Eliminar forward | OK |
| /api/tunnels | GET | Lista tunnels | OK |
| /api/tunnels/{name}/start | POST | Iniciar tunnel | OK |
| /api/tunnels/{name}/stop | POST | Detener tunnel | OK |
| /api/tunnels/{name}/remove | POST | Eliminar tunnel | OK |
| /api/config | GET | Leer config | OK |
| /api/config | POST | Guardar config | OK |
| /api/settings | GET | Leer ajustes | OK |
| /api/settings | POST | Guardar ajustes | OK |

---

## 2. API REST (puerto 8791)

### 2.1 Endpoints GET (13 endpoints)

| # | Endpoint | Resultado |
|---|----------|-----------|
| 1 | GET /api/v1/health | PASS |
| 2 | GET /api/v1/distros | PASS |
| 3 | GET /api/v1/metrics | PASS |
| 4 | GET /api/v1/status | PASS |
| 5 | GET /api/v1/alerts | PASS |
| 6 | GET /api/v1/events | PASS |
| 7 | GET /api/v1/forwards | PASS |
| 8 | GET /api/v1/tunnels | PASS |
| 9 | GET /api/v1/vps | PASS |
| 10 | GET /api/v1/limits/global | PASS |
| 11 | GET /api/v1/schedule | PASS |
| 12 | GET /api/v1/profiles | PASS |
| 13 | GET /api/v1/snapshots | PASS |

### 2.2 Endpoints POST/DELETE

| # | Endpoint | Método | Resultado |
|---|----------|--------|-----------|
| 1 | /api/v1/forwards | POST | PASS |
| 2 | /api/v1/forwards/{name} | DELETE | PASS |
| 3 | /api/v1/tunnels | POST | PASS |
| 4 | /api/v1/tunnels/{name} | DELETE | PASS |

---

## 3. MCP Tools (30 tools)

### 3.1 WSL Management (15 tools)

| Tool | Descripción | Estado |
|------|-------------|--------|
| list_distros | Lista distros con estado | OK |
| start | Inicia una distro | OK |
| stop | Detiene una distro | OK |
| restart | Reinicia una distro | OK |
| shutdown_all | Apaga todas las distros | OK |
| get_ips | IPs de distros | OK |
| snapshot | Snapshot de distro | OK |
| clone | Clona una distro | OK |
| set_global_limits | Limites globales | OK |
| get_metrics | Metricas RAM/CPU | OK |
| status | Estado global | OK |
| schedule_add | Agregar tarea | OK |
| profile_apply | Aplicar perfil | OK |
| run_command | Ejecutar comando | OK |
| doctor | Diagnostico | OK |

### 3.2 Port Forwarding (10 tools)

| Tool | Descripción | Estado |
|------|-------------|--------|
| list_forwards | Lista forwards | OK |
| forward_add | Agregar forward | OK |
| forward_remove | Eliminar forward | OK |
| forward_start | Iniciar forward | OK |
| forward_stop | Detener forward | OK |
| list_tunnels | Lista tunnels | OK |
| tunnel_add | Agregar tunnel | OK |
| tunnel_remove | Eliminar tunnel | OK |
| tunnel_start | Iniciar tunnel | OK |
| tunnel_stop | Detener tunnel | OK |

### 3.3 VPS Management (5 tools)

| Tool | Descripción | Estado |
|------|-------------|--------|
| list_vps | Lista VPS | OK |
| vps_add | Agregar VPS | OK |
| vps_remove | Eliminar VPS | OK |
| vps_connect | Conectar a VPS | OK |
| vps_disconnect | Desconectar VPS | OK |

---

## 4. CLI (7 comandos)

| # | Comando | Resultado |
|---|---------|-----------|
| 1 | --help | PASS |
| 2 | status --json | PASS |
| 3 | doctor --json | PASS |
| 4 | forwards list | PASS |
| 5 | tunnels list | PASS |
| 6 | vps list | PASS |
| 7 | schedule list | PASS |

---

## 5. GUI (12 pestañas)

| # | Pestaña | Botones Header | Editar | Estado |
|---|---------|----------------|--------|--------|
| 1 | Dashboard | Refrescar, Iniciar todas, Apagar todas, Filtro | Double-click | OK |
| 2 | Recursos | Aplicar, Restablecer | Inline | OK |
| 3 | Monitor | Auto-refresh 5s | Solo lectura | OK |
| 4 | Forwards | + Add, Apply All, Clear All, Edit | SI | OK |
| 5 | Tunnels | + Add, Connect, Disconnect, Edit | SI | OK |
| 6 | Configuracion | Recargar, Guardar | Editar texto | OK |
| 7 | Autoarranque | Activar, Editar, Desactivar, Refrescar | SI | OK |
| 8 | Programador | Nueva, Editar, Eliminar, Ejecutar, Refrescar | SI | OK |
| 9 | Perfiles | Refrescar, Aplicar, Editar, Capturar | SI | OK |
| 10 | Logs | Refrescar | Solo lectura | OK |
| 11 | Ajustes | Guardar, Restablecer | Inline | OK |
| 12 | Publicar | + Add VPS, Edit VPS, Connect, Disconnect | SI | OK |

---

## 6. Seguridad

| # | Verificacion | Estado |
|---|--------------|--------|
| 1 | Panel web con auth (token) | OK |
| 2 | API sin auth retorna 401 | OK |
| 3 | Token incorrecto rechazado | OK |
| 4 | Cookie httponly | OK |
| 5 | Security headers (CSP, X-Frame-Options, etc) | OK |
| 6 | Input validation (Pydantic) | OK |
| 7 | SQL parametrizado | OK |
| 8 | XSS protegido (esc function) | OK |

---

## 7. VPS de Prueba

- **IP:** 167.114.169.134
- **Puerto SSH:** 10000
- **Usuario:** root
- **Tunnel creado:** vps-tunnel (local_port: 2222)

---

## 8. Bugs Corregidos

| # | Bug | Severidad | Fix |
|---|-----|-----------|-----|
| 1 | Treeview TclError race condition | Medium | try/except en 8 archivos |
| 2 | DANGER_outline undefined | High | Cambiar a (DANGER, OUTLINE) |
| 3 | ttk.PanedWindow not found | High | Cambiar a tk.PanedWindow |
| 4 | paned.add weight not supported | Medium | Remover weight param |
| 5 | ForwardingService missing in ctx | High | Agregar a _build_ctx |

---

## 9. Commits

| Hash | Descripcion |
|------|-------------|
| 919e51d | fix: Treeview TclError guard + boton Editar |
| a3ba2df | feat: agregar boton Editar en Forwards y Tunnels |
| 0220a51 | feat: 7 pestañas GUI modernizadas |
| 8a97271 | feat: GUI ttkbootstrap profesional |
| f88d7f2 | feat: GUI moderna, panel web, Publicar a Internet |
| e123eb7 | fix: agregar ForwardingService al contexto |
| a0ffb5b | feat: integrar port-forwarding en wsl-port |
| c40dd1b | merge: integrar origin/master |
| 98d769b | fix(security): vulnerabilidades Critical/High |
| dd626b3 | feat: WSL Manager v0.1.0 |

---

## 10. Estado Final

- **GitHub:** https://github.com/gilmanpro/wsl-port
- **Branch:** main (sincronizado)
- **Tests:** 64/64 PASS
- **API:** 13 GET + 4 POST/DELETE = 17 endpoints
- **Web:** 24 endpoints con auth
- **MCP:** 30 tools
- **CLI:** 35+ comandos
- **GUI:** 12 pestañas ttkbootstrap con Editar
