"""Permite 'python -m src.cli' (seccion 19.3 del plan)."""

from __future__ import annotations

import sys

from wsl_port.vendor.port_forwarder.cli.cli import main

if __name__ == "__main__":
    sys.exit(main())
