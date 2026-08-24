"""Debug script to check wsl-port functionality."""
import sys
sys.path.insert(0, '.')

from wsl_port import core

print("=== Distros ===")
ds = core.distros()
for d in ds:
    print(f"  {d['name']}: state={d['state']}, ip={d.get('ip')}, running={d.get('running')}")

print("\n=== IP for Debian ===")
ip = core.get_ip('Debian')
print(f"  IP: {ip}")

print("\n=== Status ===")
st = core.status()
print(f"  Keys: {list(st.keys())}")
print(f"  Distros: {len(st.get('distros', []))}")
print(f"  Tunnels: {len(st.get('tunnels', []))}")
print(f"  Forwards: {len(st.get('forwards', []))}")
print(f"  VPS: {len(st.get('vps', []))}")

print("\n=== Tunnels ===")
tuns = core.tunnels()
for t in tuns:
    print(f"  {t['id']}: state={t['state']}, vps={t.get('vps_id')}")

print("\n=== VPS ===")
vps = core.vps_list()
for v in vps:
    print(f"  {v['id']}: host={v['host']}, port={v['port']}")
