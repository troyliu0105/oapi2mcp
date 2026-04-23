from __future__ import annotations

import argparse
import contextlib
import os

import anyio
import uvicorn
from mcp.server.sse import SseServerTransport
from mcp.server.stdio import stdio_server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.routing import Mount, Route

from openapi2mcp.parser import extract_operations, infer_base_url, load_spec
from openapi2mcp.server import create_server


def main():
    parser = argparse.ArgumentParser(
        prog="oapi2mcp",
        description="Serve an OpenAPI spec as an MCP server",
    )
    parser.add_argument("--spec", required=True, help="URL or local path to OpenAPI spec")
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "sse", "streamable-http"],
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    parser.add_argument("--base-url", default=None, help="Override base URL for API calls")
    args = parser.parse_args()

    spec = load_spec(args.spec)
    operations = extract_operations(spec)

    base_url = (
        os.environ.get("OPENAPI_BASE_URL")
        or args.base_url
        or infer_base_url(args.spec)
        or spec.get("servers", [{}])[0].get("url")
    )
    if not base_url:
        print("Error: could not determine base URL. Use --base-url or set OPENAPI_BASE_URL.")
        raise SystemExit(1)

    server = create_server(operations, base_url)

    if args.transport == "stdio":

        async def run_stdio():
            async with stdio_server() as (read, write):
                await server.run(read, write, server.create_initialization_options())

        anyio.run(run_stdio)

    elif args.transport == "sse":
        sse = SseServerTransport("/messages/")

        async def handle_sse(scope, receive, send):
            async with sse.connect_sse(scope, receive, send) as streams:
                await server.run(
                    streams[0], streams[1], server.create_initialization_options()
                )

        app = Starlette(
            routes=[
                Route("/sse", endpoint=handle_sse),
                Route("/messages/", endpoint=sse.handle_post_message, methods=["POST"]),
            ],
        )
        uvicorn.run(app, host=args.host, port=args.port)

    elif args.transport == "streamable-http":
        session_manager = StreamableHTTPSessionManager(app=server)

        @contextlib.asynccontextmanager
        async def lifespan(app):
            async with session_manager.run():
                yield

        app = Starlette(
            lifespan=lifespan,
            routes=[Mount("/", app=session_manager.handle_request)],
        )
        uvicorn.run(app, host=args.host, port=args.port)
