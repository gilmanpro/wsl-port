# Gilberto Castillo — Proyectos de Software e Infraestructura

**Ingeniero en Telecomunicaciones · Big Data & Data Science · Desarrollador de Soluciones**

> Diseño soluciones que cubren el ciclo completo de la información: desde la infraestructura TI y las redes hasta los pipelines de datos, las APIs y la aplicación que utiliza el usuario final.

---

## Portafolio de Proyectos

### 1. wsl-port — WSL + Internet en 1 clic

**Repo:** [github.com/gilmanpro/wsl-port](https://github.com/gilmanpro/wsl-port)

Aplicacion unificada que fusiona **WSL Manager** (gestion de distros WSL) y **Port Forwarding Manager** (tuneles SSH hacia VPS) en una sola ventana y un solo comando.

**Stack:** Python · ttkbootstrap · pystray · FastAPI · SQLite · DPAPI · SSH

**Caracteristicas:**
- Gestion completa de distros WSL (ciclo de vida, IPs, recursos, snapshots, clones, crear/eliminar)
- Forwards Windows→WSL (netsh portproxy + firewall)
- Tuneles SSH hacia VPS con autossh y keepalive
- Publicar servicios en Internet con 1 clic
- Supervisor unificado (IPs + tunnels + forwards + health gate)
- Panel web, API REST y MCP para agentes LLM
- CLI completo con 20 grupos de comandos
- GUI con 6 pestanas + ajustes

**KPIs:**
- Configuracion inicial: < 15 min
- Uptime de tuneles: > 99%
- Reaplicacion tras cambio de IP: < 60s

---

### 2. WSL Manager GUI

**Repo:** [github.com/gilmanpro/wsl-manager-gui](https://github.com/gilmanpro/wsl-manager-gui)

Aplicacion de escritorio para gestionar distribuciones WSL2 con GUI en system tray, CLI operativo, API REST, servidor MCP y panel web local.

**Stack:** Python · ttkbootstrap · pystray · FastAPI · SQLite · DPAPI

**Caracteristicas:**
- Dashboard de distros (estado, version, IP, default)
- Ciclo de vida (iniciar, detener, reiniciar, apagar todas)
- Limites de recursos (.wslconfig: RAM, CPUs, swap)
- Snapshots con retencion
- Autoarranque con Windows
- Programador de tareas
- Perfiles de configuracion
- Panel web, API REST y MCP

---

### 3. Port Forwarder App

**Repo:** [github.com/gilmanpro/port-forwarder-app](https://github.com/gilmanpro/port-forwarder-app)

Herramienta para administrar redirecciones de puertos entre Windows y WSL, tuneles SSH hacia VPS, supervision automatica, health checks, alertas, panel web, API REST, CLI y MCP.

**Stack:** Python · netsh · SSH · autossh · FastAPI · SQLite · DPAPI · Docker

**Caracteristicas:**
- CRUD de forwards (netsh portproxy + firewall)
- Tuneles SSH reversos multi-puerto
- Supervisor con backoff exponencial
- Health checks y alertas
- Trafico por tunel (bytes acumulados + velocidad)
- Drift detection (config vs realidad)
- Modo mantenimiento
- Panel web, API REST y MCP

---

### 4. Portafolio Profesional Autogestionable

**Web:** [perfil.gilman.pro](https://perfil.gilman.pro/proyecto/portafolio-profesional-autogestionable)

CMS que convierte un portafolio personal en un sitio autogestionable: desde el panel de administracion puedes gestionar contenido, proyectos, experiencia, formacion y blog.

**Stack:** Python · FastAPI · PostgreSQL · Docker · HTMX · JWT · Cloudflare · Resend

**Caracteristicas:**
- Panel de administracion completo
- Gestion de proyectos, experiencia, formacion
- Blog integrado
- API REST
- JWT para autenticacion
- Despliegue en Cloudflare

---

### 5. Broker MQTT

**Web:** [perfil.gilman.pro/proyecto/broker-mqtt](https://perfil.gilman.pro/proyecto/broker-mqtt)

Broker MQTT con dashboard de administracion, monitoreo en tiempo real, certificados TLS por dispositivo, WebSocket y API REST.

**Stack:** MQTT · Mosquitto · Python · FastAPI · WebSocket · TLS/mTLS · Docker · SQLite

**Caracteristicas:**
- Dashboard de administracion
- Monitoreo en tiempo real
- Certificados TLS/mTLS por dispositivo
- WebSocket para clientes web
- API REST para gestion
- Docker para despliegue

---

### 6. Test MQTT

**Web:** [perfil.gilman.pro/proyecto/test-mqtt](https://perfil.gilman.pro/proyecto/test-mqtt)

Herramienta web para probar y depurar cualquier broker MQTT desde el navegador, sin instalar herramientas CLI.

**Stack:** Python · FastAPI · PostgreSQL · Docker · Tailwind CSS · WebSockets · paho-mqtt v2

**Caracteristicas:**
- Interfaz web para testing MQTT
- Sin instalacion de herramientas CLI
- Soporte para multiples brokers
- WebSocket para tiempo real
- Historial de mensajes

---

### 7. VPN + DNS — Infraestructura de Red Centralizada

**Web:** [perfil.gilman.pro/proyecto/vpn-dns-infraestructura-de-red-centralizada](https://perfil.gilman.pro/proyecto/vpn-dns-infraestructura-de-red-centralizada)

12 contenedores. 1 solo dominio de red. 10 tuneles WireGuard + 2 servidores DNS con sinkhole que operan como una infraestructura centralizada.

**Stack:** WireGuard · Pi-hole · Docker · VPN · DNS · Contenedores

**Caracteristicas:**
- 10 tuneles WireGuard
- 2 servidores DNS con sinkhole
- Infraestructura centralizada
- Docker para despliegue
- Gestion centralizada de red

---

### 8. Autohospedado de Correo Corporativo

**Web:** [perfil.gilman.pro/proyecto/mail-server](https://perfil.gilman.pro/proyecto/mail-server)

Plataforma de correo corporativo multi-dominio con panel de administracion, API REST, email transaccional, marketing y servicios de entrega de correo.

**Stack:** Python · FastAPI · Bootstrap · Docker · Postfix · Dovecot · Rspamd · Nginx · SMTP · IMAP · POP3 · DNS · DKIM · JWT

**Caracteristicas:**
- Multi-dominio
- Panel de administracion
- API REST
- Email transaccional
- Marketing email
- DKIM para autenticacion
- JWT para autenticacion

---

### 9. Aplicaciones Web Desplegadas

**Web:** [perfil.gilman.pro/proyecto/aplicaciones-web-desplegadas](https://perfil.gilman.pro/proyecto/aplicaciones-web-desplegadas)

Aplicaciones web desarrolladas por encargo para pequenos negocios.

**Stack:** HTML · CSS · JavaScript · full-stack · Cloudflare Pages

---

## Recomendaciones del Portafolio

### Arquitectura

1. **Provider Pattern** — Cada backend detras de una interfaz comun y testeable
2. **CLI first-class** — El CLI opera sobre los mismos servicios que la GUI (paridad garantizada)
3. **Multi-interfaz + AuthService** — GUI, CLI, API REST y MCP comparten los mismos providers
4. **Repository** — ConfigStore (JSON) y MetricsStore (SQLite) separados
5. **Event Bus** — Un unico `state-changed` que las pestanas consumen por interes
6. **Supervisor (un loop)** — Poll de distros/IPs + watchdog de tunnels + reaplicacion + health checks

### Seguridad

1. **DPAPI** para cifrado de secrets en Windows
2. **Redactor global** de secretos en logs
3. **Backups automaticos** de config antes de cada escritura
4. **UAC selectivo** — solo aplicar forwards elevan
5. **CSRF protection** en paneles web
6. **Headers de seguridad** (nosniff, X-Frame-Options, CSP)

### Testing

1. **Unit tests** con mocks (no tocan WSL)
2. **Smoke tests** reales en scripts
3. **Paridad GUI/CLI** — tests que verifican que ambos usan los mismos providers
4. **CI/CD** con GitHub Actions

### Packaging

1. **PyInstaller** para ejecutables
2. **Inno Setup** para instaladores
3. **Docker** para despliegue en servidores
4. **VBS launcher** para inicio sin consola

---

## Stack Tecnologico Consolidado

### Backend

- **Python 3.11+** — Lenguaje principal
- **FastAPI** — API REST y paneles web
- **SQLite** — Metricas, alertas, journal
- **Pydantic** — Validacion de configuracion

### Frontend

- **ttkbootstrap** — GUI de escritorio
- **pystray** — System tray
- **HTMX** — Web dinamico
- **Tailwind CSS** — Estilos web

### Infraestructura

- **Docker** — Contenedores
- **WireGuard** — VPN
- **SSH** — Tuneles reversos
- **netsh** — Port forwarding Windows

### Seguridad

- **DPAPI** — Cifrado de secrets
- **JWT** — Autenticacion
- **TLS/mTLS** — Certificados
- **DKIM** — Autenticacion de correo

---

## Contacto

- **Web:** [perfil.gilman.pro](https://perfil.gilman.pro)
- **GitHub:** [github.com/gilmanpro](https://github.com/gilmanpro)
- **LinkedIn:** [linkedin.com/in/gilberto-castillo](https://linkedin.com/in/gilberto-castillo)
- **Email:** gilberto@gilman.pro

---

**Gilberto Castillo**  
Ingeniero en Telecomunicaciones  
Especialista en Big Data & Data Science  
Panama
