# wsl-port — WSL + Internet en 1 clic

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](#requisitos)
[![Integración](https://img.shields.io/badge/Integra-WSL%20Manager%20%2B%20Port%20Forwarding-2ea44f)](#caracter%C3%ADsticas-integradas)
[![Plataforma](https://img.shields.io/badge/Plataforma-Windows%2010%2F11-0078D6?logo=windows&logoColor=white)](#requisitos)
[![Licencia](https://img.shields.io/badge/Licencia-MIT-blue.svg)](LICENSE)

> **Publica cualquier servicio de tu WSL en Internet con 1 clic.** wsl-port une **WSL Manager** (tus distros) y **Port Forwarding Manager** (túneles al VPS) en una sola ventana y un solo comando.

**Reemplaza a las 2 apps por separado** — si usas wsl-port ya no necesitas abrir WSL Manager ni Port Forwarder.

---

## 🚀 Inicio en 10 segundos

**Opción A — Doble clic (recomendado, sin consola)**

1. Doble clic en `dist\wsl-port\wsl-port.exe` (compilado) o en `wsl-port.vbs` / el acceso directo **wsl-port** del Escritorio.
2. ¡Listo! No se abre ninguna terminal — todo queda en segundo plano.

**Opción B — Línea de comandos**

```bash
pythonw run.py
```

> **Requisito único:** tener instaladas las 2 apps base en `../wsl-manager-gui` y `../port-forwarder-app` con sus `.venv` ( `pip install -e ".[api,dev]"` ). wsl-port las usa automáticamente.

---

## ✨ Características integradas

| Lo que ves | De dónde viene |
|---|---|
| **Distros WSL** — estado, IP, iniciar/apagar | WSL Manager |
| **Publicar en Internet** — asistente WSL → VPS | **Nuevo: flujo de 1 clic** |
| **Tunnels / VPS** — estado, tráfico, gestión VPS | Port Forwarder |
| **Forwards** — redirecciones Windows→WSL | Port Forwarder |
| **Estado único** — todo en `wsl-port status` | Combinado |

---

## 📖 Uso

### Ventana (recomendado)

Pestañas:

- **Distros WSL** — tus distros, su IP y botones para iniciar/apagar.
- **Publicar en Internet** — elige **distro** (ej. Debian), **puerto del servicio** (ej. 9000), **VPS** y **puerto público** (ej. 18097) → **Publicar**. Te da la URL pública y la abre.
- **Tunnels / VPS** — todos tus túneles, su estado, tráfico (rx/tx + velocidad) y tus VPS.
- **Forwards** — tus redirecciones.

Barra inferior: abre los paneles web de cada app (`:8790` WSL, `:8794` PF) con un clic.

### CLI

```bash
# Ver todo de un vistazo
python cli_runner.py status

# Publicar el servicio 9000 de Debian en http://TU_VPS:18097
python cli_runner.py publish --distro Debian --wsl-port 9000 --vps "vps1 de canada" --public-port 18097

# El servicio queda en http://VPS_IP_REDACTED:18097 (ejemplo) — pruébalo
# Detener:
python cli_runner.py unpublish pub-debian-9000
```

> El flujo `publish` verifica que la distro exista, que el VPS esté registrado y que el puerto local responda (espejo localhost de WSL2 `127.0.0.1:<puerto>`), crea el túnel si no existe y lo arranca.

---

## 🧩 Cómo funciona

```
[TU VPS :18097]  ←túnel SSH reverso→  [Tu PC: ssh.exe]  ←→  [WSL Debian :9000]
                                           ↑
                                    Port Forwarder (túnel)
                                    WSL Manager (distro/IP)
                                           ↑
                                      wsl-port (une ambos)
```

No duplica código: **delega en los CLIs de cada app** (cada una con su venv) y combina los datos. Usa el **espejo de localhost de WSL2** (`127.0.0.1`), por eso no necesita la IP cambiante de WSL.

Guía completa de WSL→VPS: [`port-forwarder-app/docs/manual-wsl-vps.md`](../port-forwarder-app/docs/manual-wsl-vps.md)

---

## 📁 Estructura

```
wsl-port/
├── run.py              # ← DOBLE CLIC AQUÍ (pythonw) — ventana integrada
├── wsl-port.vbs        # acceso directo sin consola
├── wsl_port/
│   ├── core.py         # estado único (delega sin abrir terminales)
│   ├── publish.py      # flujo publicar/despublicar
│   ├── cli.py          # CLI integrado
│   └── ui/             # ventana (tabs + asistente Publicar)
└── tests/              # pytest (7 tests)
```

---

## ✅ Requisitos

- Windows 10/11 + WSL2 con al menos 1 distro.
- Python 3.11+ con `.venv` de las 2 apps base instalados.
- Un VPS con `GatewayPorts yes` (ver `port-forwarder-app/vps/sshd_config.snippet`).

Todo corre **en segundo plano, sin terminales** (`pythonw` + `CREATE_NO_WINDOW`).

## 🛠️ Desarrollo

```bash
python -m pytest tests -q   # 7 tests
```

---

## 📄 Licencia

MIT — ver [LICENSE](LICENSE) y los repos base:
[WSL Manager](https://github.com/gilmanpro/wsl-manager-gui) ·
[Port Forwarder](https://github.com/gilmanpro/port-forwarder-app)
