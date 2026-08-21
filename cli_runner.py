"""Ejecuta el CLI de wsl-port (python cli_runner.py <comando>)."""
import sys

from wsl_port.cli import main

if __name__ == "__main__":
    sys.exit(main())