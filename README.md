# wsl-port — WSL Manager + Port Forwarding integrados

Aplicación unificada que combina **WSL Manager** (gestión de distros WSL2) y
**Port Forwarding Manager** (forwards Windows→WSL y túneles SSH al VPS), con un
flujo de primera clase: **publicar un servicio de WSL en Internet** en un paso.

## Características integradas

- **Distros WSL**: estado, inicio/parada, IPs (de wsl-manager-gui).
- **Forwards** y **Tunnels/VPS**: estado, tráfico por túnel y gestión de VPS
  (de port-forwarder-app).
- **Publicar en Internet**: asistente que crea y arranca el túnel
  `distro WSL → VPS` y muestra la URL pública.
- **Estado único**: CLI `wsl-port status` con todo combinado.
- **Paneles web** de ambas apps accesibles desde la ventana.

## Estructura

```
wsl-port/
├── run.py              # ventana integrada (pythonw run.py)
├── wsl_port/
│   ├── core.py         # acceso a ambas apps (delegación CLI) + estado único
│   ├── publish.py      # flujo "publicar en Internet"
│   ├── cli.py          # CLI integrado
│   └── ui/             # ventana tkinter (tabs + asistente)
└── tests/              # pytest
```

## Uso (CLI)

```bash
# Estado integrado
python cli_runner.py status

# Publicar un servicio de WSL en Internet
python cli_runner.py publish --distro Debian --wsl-port 9000 \
  --vps "vps1 de canada" --public-port 18097

# Detener la publicación
python cli_runner.py unpublish pub-debian-9000
```

## Uso (ventana)

```bash
pythonw run.py
```

Pestañas: **Distros WSL** · **Publicar en Internet** (asistente) ·
**Tunnels / VPS** · **Forwards**. La barra inferior abre los paneles web
(`:8790` WSL y `:8794` PF).

## Cómo funciona la integración

No duplica lógica: delega en los CLIs de ambas aplicaciones (cada una con su
venv) y combina los datos. El flujo *publish* usa el **espejo de localhost de
WSL2** (`127.0.0.1:<puerto>`), crea el túnel en port-forwarder-app y lo arranca.

Ver el manual completo: `port-forwarder-app/docs/manual-wsl-vps.md`.