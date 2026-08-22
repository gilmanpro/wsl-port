# wsl-port — WSL + Internet en 1 clic

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](#requisitos)
[![Integracion](https://img.shields.io/badge/Integra-WSL%20Manager%20%2B%20Port%20Forwarding-2ea44f)](#caracteristicas-integradas)
[![Plataforma](https://img.shields.io/badge/Plataforma-Windows%2010%2F11-0078D6?logo=windows&logoColor=white)](#requisitos)
[![Licencia](https://img.shields.io/badge/Licencia-MIT-blue.svg)](LICENSE)

> **Publica cualquier servicio de tu WSL en Internet con 1 clic.** wsl-port une **WSL Manager** (tus distros) y **Port Forwarding Manager** (tuneles al VPS) en una sola ventana y un solo comando.

**Reemplaza a las 2 apps por separado** — si usas wsl-port ya no necesitas abrir WSL Manager ni Port Forwarder.

---

## Inicio rapido

**Opcion A — Doble clic (recomendado, sin consola)**

1. Doble clic en `wsl-port.vbs` o el acceso directo del Escritorio.
2. ¡Listo! No se abre ninguna terminal — todo queda en segundo plano.

**Opcion B — Linea de comandos**

```bash
# Modo headless (fondo, sin ventana)
python run.py --headless

# Con interfaz grafica
python run.py

# Solo CLI (para scripts)
wsl-port status
```

---

## Caracteristicas integradas

| Lo que ves | De donde viene |
|---|---|
| **Distros WSL** — estado, IP, iniciar/apagar, snapshots, clones | WSL Manager |
| **Publicar en Internet** — asistente WSL -> VPS (1 clic) | **Nuevo: flujo integrado** |
| **Tunnels / VPS** — estado, trafico, gestion VPS, latency | Port Forwarder |
| **Forwards** — redirecciones Windows->WSL (netsh + firewall) | Port Forwarder |
| **Limites de recursos** — .wslconfig (RAM, CPUs, swap) | WSL Manager |
| **Autoarranque** — distros con Windows + delay | WSL Manager |
| **Health checks** — TCP, alertas, umbrales configurables | Port Forwarder |
| **Scheduler** — tareas programadas (dias/hora) | Ambos |
| **Perfiles** — capturar/aplicar estados | Ambos |
| **Maintenance** — pausar todo sin borrar config | Port Forwarder |
| **Drift** — config vs realidad (deteccion + reconciliacion) | Port Forwarder |
| **Doctor** — diagnostico del entorno | Ambos |
| **Supervisor** — loop unificado (IPs + tunnels + forwards) | Port Forwarder |
| **Panel web** — dashboard en `:8780` | Nuevo |
| **API REST** — `:8781` con tokens + scopes | Nuevo |
| **MCP** — `:8782` para agentes LLM | Nuevo |

---

## CLI completo

```
wsl-port status                          # Estado integrado
wsl-port distro list/start/stop/ips      # Gestion WSL
wsl-port limits get/set                  # Recursos .wslconfig
wsl-port autostart list/set/remove       # Autoarranque
wsl-port forwards list/add/remove/apply  # Forwards Windows->WSL
wsl-port tunnels list/add/start/stop     # Tunnels SSH
wsl-port vps list/add/remove             # VPS
wsl-port publish --distro Debian ...     # Publicar en Internet
wsl-port health check                    # Health checks
wsl-port alerts list/resolve             # Alertas
wsl-port schedule list/add/remove        # Tareas programadas
wsl-port profile list/apply/capture      # Perfiles
wsl-port maintenance on/off/status       # Modo mantenimiento
wsl-port drift check                     # Deteccion de drift
wsl-port doctor                          # Diagnostico
wsl-port config export/import/validate   # Configuracion
wsl-port secrets set/check               # Secretos DPAPI
wsl-port supervise                       # Supervisor headless
wsl-port watch                           # Eventos en vivo
```

---

## Publicar en Internet (1 clic)

```bash
# Publicar el servicio 9000 de Debian en http://TU_VPS:18097
wsl-port publish --distro Debian --wsl-port 9000 --vps "vps1 de canada" --public-port 18097

# Detener publicacion
wsl-port unpublish pub-debian-9000
```

Desde la GUI: pestana **Publicar en Internet** — elige distro, puerto, VPS y puerto publico.

---

## Estructura

```
wsl-port/
├── run.py                  # Entry point (GUI / headless)
├── wsl-port.vbs            # Lanzador sin consola
├── wsl_port/
│   ├── core.py             # Nucleo integrado (providers directos)
│   ├── cli.py              # CLI completo (20 comandos)
│   ├── publish.py          # Flujo publicar/despublicar
│   ├── ui/
│   │   ├── main_window.py  # Ventana (5 pestanas + ajustes)
│   │   └── publish_tab.py  # Asistente Publicar
│   └── vendor/             # Providers de ambas apps (auto-generado)
├── tests/                  # pytest (7 tests)
├── config/                 # Ejemplo de config
├── scripts/                # SSH key setup, autossh, build
└── vps/                    # sshd_config + install.sh
```

---

## Requisitos

- Windows 10/11 + WSL2 con al menos 1 distro.
- Python 3.11+.
- Un VPS con `GatewayPorts yes` (ver `vps/sshd_config.snippet`).
- Admin (UAC) solo para aplicar forwards.

---

## Instalacion

```bash
git clone https://github.com/gilmanpro/wsl-port
cd wsl-port
python -m venv .venv
.venv\Scripts\activate
pip install -e .
# o para desarrollo:
pip install -e ".[dev]"
```

---

## Tests

```bash
python -m pytest tests -q
```

---

## Licencia

MIT — ver [LICENSE](LICENSE) y los repos base:
[WSL Manager](https://github.com/gilmanpro/wsl-manager-gui) ·
[Port Forwarder](https://github.com/gilmanpro/port-forwarder-app)
