"""Servidor MCP sobre stdio (seccion 21.4). Import lazy de 'mcp'."""
from __future__ import annotations

import time

from src.cli.common import CliContext


def run_stdio(ctx: CliContext) -> None:
    """Transporte stdio: NO requiere autenticacion (canal local)."""
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore
    except ImportError as e:
        raise RuntimeError("falta el paquete 'mcp'. Instala: pip install mcp") from e

    from src.mcp.tools import McpTools, get_tool_defs

    tools = McpTools(ctx)
    mcp = FastMCP("wsl-manager")

    for definition in get_tool_defs():
        name = definition["name"]

        def make_tool(fn_name: str = name):
            def tool(arguments: dict | None = None) -> dict:
                return tools.call(fn_name, arguments)

            tool.__name__ = fn_name
            tool.__doc__ = definition["description"]
            return tool

        mcp.tool()(make_tool())

    mcp.run(transport="stdio")


def _verify_mcp_token(ctx: CliContext, token: str) -> bool:
    """Verifica un token Bearer contra la DB. Devuelve True si es valido."""
    if not token:
        return False
    row = ctx.metrics.verify_token(token)
    if row is None:
        return False
    # Verificar expiracion
    if row["expires"] and row["expires"] < time.time():
        return False
    return True


def create_http_app(ctx: CliContext):
    """App ASGI para transporte HTTP (P2): usa FastMCP con streamable_http.

    Incluye middleware de autenticacion Bearer cuando mcp.token_required=True.
    """
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore
    except ImportError as e:
        raise RuntimeError("falta el paquete 'mcp'. Instala: pip install mcp") from e

    from src.mcp.tools import McpTools, get_tool_defs

    tools = McpTools(ctx)
    mcp = FastMCP("wsl-manager")
    for definition in get_tool_defs():
        name = definition["name"]

        def make_tool(fn_name: str = name):
            def tool(arguments: dict | None = None) -> dict:
                return tools.call(fn_name, arguments)

            tool.__name__ = fn_name
            tool.__doc__ = definition["description"]
            return tool

        mcp.tool()(make_tool())

    app = mcp.streamable_http_app()

    # --- Auth middleware: solo para transporte HTTP -------------------------
    if ctx.config.mcp.token_required:
        from starlette.middleware import Middleware
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.requests import Request
        from starlette.responses import JSONResponse

        class McpAuthMiddleware(BaseHTTPMiddleware):
            """Valida Authorization: Bearer <token> o X-MCP-Token en cada request."""

            async def dispatch(self, request: Request, call_next):
                # 1. Extraer token de headers
                auth_header = request.headers.get("Authorization", "")
                token = ""
                if auth_header.lower().startswith("bearer "):
                    token = auth_header[7:].strip()
                if not token:
                    token = request.headers.get("X-MCP-Token", "")

                # 2. Verificar contra la DB
                if not _verify_mcp_token(ctx, token):
                    ctx.metrics.log_event(
                        "mcp_denied",
                        message=f"401 MCP token invalido desde {request.client.host if request.client else '?'}",
                    )
                    return JSONResponse(
                        status_code=401,
                        content={"error": "token MCP invalido o ausente"},
                    )

                # 3. Token valido: continuar
                return await call_next(request)

        # Starlette mount() returns a new Mount that IS an ASGI app,
        # and middleware must be added via the app's add_middleware.
        app.add_middleware(McpAuthMiddleware)  # type: ignore[union-attr]

    return app
