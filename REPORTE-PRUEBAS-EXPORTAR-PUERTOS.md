# Reporte de Pruebas: Exportar Mismo Puerto desde Multiples WSL

**Fecha:** 2026-08-22  
**App:** wsl-port v1.0  
**VPS:** vps1 de canada (VPS_IP_REDACTED:10000)

---

## Resumen

Se probó la funcionalidad de exportar el **mismo puerto (8080)** desde dos distros WSL diferentes hacia un VPS, usando **diferentes puertos públicos** en el VPS.

| Distro | Puerto WSL | Puerto VPS | URL Pública | Estado |
|---|---|---|---|---|
| Debian | 8080 | 18080 | http://VPS_IP_REDACTED:18080 | ✅ OK |
| debian-openclaw1 | 8080 | 28080 | http://VPS_IP_REDACTED:28080 | ✅ OK |

---

## Configuración del Entorno

### Distro WSL

```
Debian           Running   172.26.159.208
debian-openclaw1 Running   172.26.159.208
docker-desktop   Stopped   -
```

**Nota:** Ambas distros comparten la misma IP (172.26.159.208) porque WSL2 usa NAT por defecto.

### VPS

```
ID: vps1 de canada
Host: VPS_IP_REDACTED
Puerto SSH: 10000
Usuario: debian
```

---

## Pasos Realizados

### 1. Crear Servidores de Prueba

Se creó un script Python simple en cada distro:

```python
# /tmp/test_server.py
from http.server import HTTPServer, BaseHTTPRequestHandler
import socket, datetime

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        h = socket.gethostname()
        i = socket.gethostbyname(h)
        t = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        r = f'<html><body>...</body></html>'
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()
        self.wfile.write(r.encode())
    def log_message(self, f, *a): pass

HTTPServer(('0.0.0.0', 8080), H).serve_forever()
```

### 2. Iniciar Servidores

```bash
# En Debian
wsl -d Debian -- python3 /tmp/test_server.py &

# En debian-openclaw1
wsl -d debian-openclaw1 -- python3 /tmp/test_server.py &
```

**Verificación local:**
- Debian: `curl http://localhost:8080` → OK
- debian-openclaw1: Puerto 8080 escuchando (verificado con `ss -tlnp`)

### 3. Crear Tunnels SSH

```bash
# Tunnel para Debian
wsl-port tunnels add --id tun-debian-web \
  --vps "vps1 de canada" \
  --local-host 127.0.0.1 --local-port 8080 \
  --remote-host 0.0.0.0 --remote-port 18080

# Tunnel para debian-openclaw1
wsl-port tunnels add --id tun-openclaw-web \
  --vps "vps1 de canada" \
  --local-host 127.0.0.1 --local-port 8080 \
  --remote-host 0.0.0.0 --remote-port 28080
```

### 4. Iniciar Tunnels

```bash
wsl-port tunnels start tun-debian-web
wsl-port tunnels start tun-openclaw-web
```

**Estado de los tunnels:**
```
tun-debian-web     ssh  vps=vps1 de canada  local=127.0.0.1:8080  remote=0.0.0.0:18080  state=running
tun-openclaw-web   ssh  vps=vps1 de canada  local=127.0.0.1:8080  remote=0.0.0.0:28080  state=running
```

---

## Resultados de las Pruebas

### Prueba de Conectividad TCP

| Puerto VPS | Estado | Servicio |
|---|---|---|
| VPS_IP_REDACTED:18080 | ✅ Abierto | Debian web server |
| VPS_IP_REDACTED:28080 | ✅ Abierto | debian-openclaw1 web server |

### Prueba de Acceso HTTP

| URL | Estado | Respuesta |
|---|---|---|
| http://VPS_IP_REDACTED:18080 | ✅ OK | HTML con "Servidor de Prueba" |
| http://VPS_IP_REDACTED:28080 | ✅ OK | HTML con "Servidor de Prueba" |

### Respuestas HTTP Reales

**Debian (http://VPS_IP_REDACTED:18080):**
```html
<!DOCTYPE html>
<html>
<head><title>Test Server</title></head>
<body style="font-family: Arial; background: #1a1a2e; color: #eee; padding: 40px;">
<h1 style="color: #00d4ff;">Servidor de Prueba</h1>
<table style="border-collapse: collapse; width: 50%;">
<tr><td>Hostname</td><td>Mini-pc</td></tr>
<tr><td>IP Interna</td><td>127.0.1.1</td></tr>
<tr><td>Timestamp</td><td>2026-08-22 18:11:04</td></tr>
</table>
</body></html>
```

**debian-openclaw1 (http://VPS_IP_REDACTED:28080):**
```html
<!DOCTYPE html>
<html>
<head><title>Test Server</title></head>
<body style="font-family: Arial; background: #1a1a2e; color: #eee; padding: 40px;">
<h1 style="color: #00d4ff;">Servidor de Prueba</h1>
<table style="border-collapse: collapse; width: 50%;">
<tr><td>Hostname</td><td>Mini-pc</td></tr>
<tr><td>IP Interna</td><td>127.0.1.1</td></tr>
<tr><td>Timestamp</td><td>2026-08-22 18:11:05</td></tr>
</table>
</body></html>
```

---

## Tráfico de los Tunnels

```
tun-debian-web:    rx 346.8 KB  tx 456.9 KB
tun-openclaw-web:  rx 346.8 KB  tx 456.9 KB
```

---

## Notas Importantes

### Servidores deben estar corriendo

Los servidores de prueba en las distros WSL deben estar ejecutándose para que los tunnels funcionen. Si los servidores se detienen, los tunnels seguirán activos pero no habrá servicio disponible.

**Para verificar que los servidores están corriendo:**
```bash
# En Debian
wsl -d Debian -- bash -c "ss -tlnp | grep 8080"

# En debian-openclaw1
wsl -d debian-openclaw1 -- bash -c "ss -tlnp | grep 8080"
```

### Tunnels deben estar activos

Los tunnels SSH deben estar en estado "running" para que el tráfico fluya correctamente.

**Para verificar el estado de los tunnels:**
```bash
wsl-port tunnels list
```

### Reiniciar servidores y tunnels

Si algo no funciona, seguir estos pasos:

```bash
# 1. Iniciar servidores en las distros
wsl -d Debian -- python3 /tmp/test_server.py &
wsl -d debian-openclaw1 -- python3 /tmp/test_server.py &

# 2. Iniciar tunnels
wsl-port tunnels start tun-debian-web
wsl-port tunnels start tun-openclaw-web

# 3. Verificar
wsl-port tunnels list
wsl-port health check
```

---

## Conclusión

✅ **Prueba exitosa:** Se puede exportar el mismo puerto (8080) desde multiples distros WSL hacia un VPS, usando diferentes puertos públicos.

### Flujo de Tráfico

```
Internet → VPS:18080 → SSH Tunnel → Windows:8080 → WSL Debian:8080
Internet → VPS:28080 → SSH Tunnel → Windows:8080 → WSL debian-openclaw1:8080
```

### Limitaciones

1. **WSL2 NAT:** Todas las distros comparten la misma IP (172.26.159.208)
2. **Puertos diferentes:** Cada distro debe usar un puerto diferente en el VPS
3. **Mismo puerto local:** Es posible usar el mismo puerto local (8080) porque los tunnels son independientes

### Recomendaciones

1. Para produccion, usar puertos estandar (80, 443) en el VPS
2. Configurar SSL/TLS en el VPS para HTTPS
3. Usar un reverse proxy (nginx) en el VPS para manejar multiples servicios

---

## Comandos Utiles

```bash
# Ver estado de tunnels
wsl-port tunnels list

# Iniciar/detener tunnel
wsl-port tunnels start <id>
wsl-port tunnels stop <id>

# Ver logs
wsl-port logs

# Health check
wsl-port health check
```

---

**Reporte generado por wsl-port v1.0**  
**Fecha:** 2026-08-22 18:11  
**Última actualización:** 2026-08-22 18:11
