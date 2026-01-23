"""EVOLVE-O-MART™ - MCP Server.

A store where products compete for favorites. Each product evolves after enough favorites.

Usage:
    uv run evolve-o-mart serve              # Run MCP server (stdio)
    uv run evolve-o-mart serve --http       # Run HTTP server for web frontend

Environment Variables:
    CORS_ORIGINS: Comma-separated list of allowed origins (default: "*")
    GOOGLE_API_KEY: Google Gemini API key for evolution
    FAVORITES_TO_EVOLVE: Number of favorites per product to trigger evolution (default: 5)
"""

import logging
import os

import click
from fastmcp import FastMCP
from fastmcp.server.middleware.logging import LoggingMiddleware
from fastmcp.utilities.logging import get_logger
from starlette.middleware.cors import CORSMiddleware

from evolve_o_mart.gemini.sampling import GoogleGenaiSamplingHandler
from evolve_o_mart.storage.elasticsearch import get_cache_backend
from evolve_o_mart.store import Store


def get_cors_origins() -> list[str]:
    """Get CORS origins from environment variable."""
    origins = os.environ.get("CORS_ORIGINS", "*")
    if origins == "*":
        return ["*"]
    return [o.strip() for o in origins.split(",") if o.strip()]


# ============ MCP SERVER ============

sampling_handler = GoogleGenaiSamplingHandler(default_model="gemini-3-flash-preview")

mcp_logger = get_logger(name="mcp")
mcp_logger.setLevel(logging.ERROR)

logging_middleware = LoggingMiddleware(logger=get_logger(name="evolve-o-mart"), include_payloads=True)

mcp = FastMCP(
    name="EvolvingStore",
    instructions="""An evolving product store where products compete for favorites.

Tools:
- get_store_state: Get all products and store state
- favorite_product: Add a favorite to a product
- evolve: Evolve a specific product (requires enough favorites)
- reset_store: Reset to initial seed products

Each product evolves independently after reaching the favorites threshold.
""",
    sampling_handler=sampling_handler,
    sampling_handler_behavior="always",
    middleware=[logging_middleware],
)

# Create store and register with MCP server
store = Store(get_cache_backend())
store.add_tools_to_server(mcp)
store.add_resources_to_server(mcp)


# ============ CLI ============


@click.group()
@click.version_option(version="1.0.0", prog_name="evolve-o-mart")
def cli() -> None:
    """EVOLVE-O-MART™ - Products That Grow With You."""


@cli.command()
@click.option("--http", "use_http", is_flag=True, help="Run as HTTP server")
@click.option("--port", default=8000, help="Port for HTTP server")
@click.option("--host", default="127.0.0.1", help="Host for HTTP server")
def serve(*, use_http: bool, port: int, host: str) -> None:
    """Start the MCP server."""
    if use_http:
        click.echo(f"🛒 Starting EVOLVE-O-MART HTTP server on {host}:{port}")
        click.echo(f"   MCP endpoint: http://{host}:{port}/mcp")

        cors_origins = get_cors_origins()
        click.echo(f"   CORS origins: {cors_origins}")

        app = mcp.http_app(path="/mcp")
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["Mcp-Session-Id"],
        )

        import uvicorn

        uvicorn.run(app, host=host, port=port, access_log=False)
    else:
        click.echo("🛒 Starting EVOLVE-O-MART MCP server (stdio)")
        mcp.run()


if __name__ == "__main__":
    cli()
