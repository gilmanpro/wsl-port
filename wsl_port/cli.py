"""CLI integrado de wsl-port: areas de ambas aplicaciones + 'publish'."""
from __future__ import annotations

import argparse
import json
import sys
import webbrowser

from . import core
from . import publish as pub


def _out(data, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
    elif isinstance(data, list):
        for row in data:
            print(json.dumps(row, ensure_ascii=False, default=str))
    else:
        print(data)


def _fmt_bytes(n) -> str:
    n = float(n or 0)
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or u == "TB":
            return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} TB"


def cmd_status(args) -> int:
    st = core.status()
    if args.json:
        _out(st, True)
        return 0
    up = sum(1 for d in st["distros"] if d.get("running"))
    tun_ok = sum(1 for t in st["tunnels"] if t.get("state") == "running")
    print(f"Supervisor (PF): {'RUNNING' if st['supervisor_running'] else 'idle'} "
          f"· admin={st['admin']} · maintenance={st['maintenance']}")
    print(f"Distros WSL: {up}/{len(st['distros'])} en marcha")
    for d in st["distros"]:
        print(f"  distro {d.get('name','?'):<18} {d.get('state','?'):<9} "
              f"ip={d.get('ip') or '-'}")
    print(f"Forwards: {len(st['forwards'])}  Tunnels: {tun_ok}/{len(st['tunnels'])}")
    for t in st["tunnels"]:
        tf = t.get("traffic")
        tr = (f"  rx {_fmt_bytes(tf['rx_bytes'])} tx {_fmt_bytes(tf['tx_bytes'])}"
              f" vel r:{_fmt_bytes(tf['rx_rate_bps'])}/s t:{_fmt_bytes(tf['tx_rate_bps'])}/s"
              if tf else "")
        print(f"  tun {t.get('id','?'):<18} {t.get('state','?'):<9} "
              f"local={t.get('local')} remote={','.join(t.get('remote') or [])}{tr}")
    for f in st["forwards"]:
        print(f"  fwd {f.get('id','?'):<18} :{f.get('listen_port','?'):<6} "
              f"{f.get('state','?'):<8} ip={f.get('ip') or '-'}")
    print(f"VPS registrados: {len(st['vps'])}")
    for v in st["vps"]:
        print(f"  vps {v.get('id','?'):<18} {v.get('host','?')}:{v.get('port',22)}")
    return 0


def cmd_publish(args) -> int:
    try:
        r = pub.publish(args.distro, args.wsl_port, args.vps,
                        args.public_port, bind=args.bind, start=not args.no_start)
    except (ValueError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if args.json:
        _out(r, True)
    else:
        print(f"Tunel '{r['tunnel_id']}' corriendo")
        print(f"  local : {r['local']}  (servicio de la distro {args.distro})")
        print(f"  publico: {r['public_url']}")
        if not args.no_open:
            webbrowser.open(r["public_url"])
    return 0


def cmd_unpublish(args) -> int:
    ok = pub.unpublish(args.tunnel)
    print("tunel eliminado" if ok else f"no se pudo eliminar '{args.tunnel}'")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="wsl-port", description="WSL Manager + Port Forwarding integrados")
    p.add_argument("--json", action="store_true", help="salida JSON")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("status", help="estado integrado (distros + tunnels + forwards + vps)")
    s.set_defaults(fn=cmd_status)

    pu = sub.add_parser("publish", help="publicar un servicio de WSL en Internet via el VPS")
    pu.add_argument("--distro", required=True)
    pu.add_argument("--wsl-port", type=int, required=True)
    pu.add_argument("--vps", required=True)
    pu.add_argument("--public-port", type=int, required=True)
    pu.add_argument("--bind", default="0.0.0.0")
    pu.add_argument("--no-start", action="store_true")
    pu.add_argument("--no-open", action="store_true")
    pu.set_defaults(fn=cmd_publish)

    u = sub.add_parser("unpublish", help="detener y eliminar un tunel publicado")
    u.add_argument("tunnel")
    u.set_defaults(fn=cmd_unpublish)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())