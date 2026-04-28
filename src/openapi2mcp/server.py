from __future__ import annotations

import os
import re

import httpx
from mcp.server.lowlevel import Server
from mcp.shared.exceptions import McpError
from mcp import types
from mcp.types import ErrorData

from openapi2mcp.converter import operation_to_tool
from openapi2mcp.models import Operation


def _build_auth_headers() -> dict[str, str]:
    api_key = os.environ.get("API_KEY")
    if not api_key:
        return {}
    auth_type = os.environ.get("API_AUTH_TYPE", "bearer").lower()
    if auth_type == "api-key":
        return {"X-API-Key": api_key}
    return {"Authorization": f"Bearer {api_key}"}


def create_server(operations: list[Operation], base_url: str) -> Server:
    server = Server("openapi2mcp")

    @server.list_tools()
    async def handle_list_tools():
        return [operation_to_tool(op) for op in operations]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict):
        operation = next((op for op in operations if op.operation_id == name), None)

        if operation is None:
            raise McpError(
                ErrorData(code=-32601, message=f"Unknown tool: {name}")
            )

        url_path = operation.path
        path_params: set[str] = set()
        for match in re.finditer(r"\{(\w+)\}", operation.path):
            param_name = match.group(1)
            path_params.add(param_name)
            if param_name in arguments:
                url_path = url_path.replace(
                    f"{{{param_name}}}", str(arguments[param_name])
                )

        body_keys: set[str] = set()
        if operation.request_body_schema and "properties" in operation.request_body_schema:
            body_keys = set(operation.request_body_schema["properties"].keys())

        query_params: dict = {}
        body_params: dict = {}
        for key, value in arguments.items():
            if key in path_params:
                continue
            if key in body_keys:
                body_params[key] = value
            else:
                query_params[key] = value

        headers = _build_auth_headers()
        url = f"{base_url.rstrip('/')}{url_path}"

        try:
            timeout = httpx.Timeout(connect=10.0, read=300.0, write=60.0, pool=10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                method = operation.method.upper()
                if method == "GET":
                    response = await client.request(
                        "GET", url, params=query_params, headers=headers
                    )
                else:
                    response = await client.request(
                        method,
                        url,
                        json=body_params or None,
                        params=query_params or None,
                        headers=headers,
                    )
        except httpx.HTTPError as exc:
            raise McpError(
                ErrorData(code=-32603, message=f"Connection error: {exc}")
            )

        if response.status_code >= 400:
            raise McpError(
                ErrorData(
                    code=-32603,
                    message=f"Upstream {response.status_code}: {response.text}",
                )
            )

        return [types.TextContent(type="text", text=response.text)]

    return server
