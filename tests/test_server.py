from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from mcp.types import (
    CallToolRequest,
    CallToolRequestParams,
    ListToolsRequest,
)

from openapi2mcp.models import Operation
from openapi2mcp.server import create_server


def _make_operations():
    return [
        Operation(
            method="get",
            path="/pets",
            operation_id="list_pets",
            summary="List pets",
            parameters=[
                {
                    "name": "limit",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "integer"},
                }
            ],
        ),
        Operation(
            method="post",
            path="/pets",
            operation_id="create_pet",
            summary="Create pet",
            request_body_schema={
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        ),
        Operation(
            method="get",
            path="/pets/{id}",
            operation_id="get_pet",
            summary="Get pet",
            parameters=[
                {
                    "name": "id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                }
            ],
        ),
    ]


def _mock_httpx_response(status_code: int = 200, text: str = "OK"):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    return resp


def _patch_async_client(response: MagicMock):
    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return patch("openapi2mcp.server.httpx.AsyncClient", return_value=mock_client), mock_client


@pytest.fixture
def server():
    return create_server(_make_operations(), "http://localhost:3000")


@pytest.fixture(autouse=True)
def _clean_env():
    keys = ["API_KEY", "API_AUTH_TYPE"]
    original = {k: os.environ.pop(k, None) for k in keys}
    yield
    for k, v in original.items():
        if v is not None:
            os.environ[k] = v
        else:
            os.environ.pop(k, None)

@pytest.mark.asyncio
async def test_list_tools_returns_correct_tools(server):
    handler = server.request_handlers[ListToolsRequest]
    result = await handler(ListToolsRequest(method="tools/list"))

    tools = result.root.tools
    assert len(tools) == 3
    names = {t.name for t in tools}
    assert names == {"list_pets", "create_pet", "get_pet"}

@pytest.mark.asyncio
async def test_call_tool_successful_get(server):
    response = _mock_httpx_response(200, '{"pets": []}')
    ctx, mock_client = _patch_async_client(response)

    with ctx:
        handler = server.request_handlers[CallToolRequest]
        result = await handler(
            CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name="list_pets", arguments={"limit": 10}
                ),
            )
        )

    assert result.root.isError is None or result.root.isError is False
    assert result.root.content[0].text == '{"pets": []}'
    mock_client.request.assert_awaited_once()
    call_kwargs = mock_client.request.call_args
    assert call_kwargs[0][0] == "GET"
    assert call_kwargs[1]["params"] == {"limit": 10}


@pytest.mark.asyncio
async def test_call_tool_successful_post(server):
    response = _mock_httpx_response(201, "Created")
    ctx, mock_client = _patch_async_client(response)

    with ctx:
        handler = server.request_handlers[CallToolRequest]
        result = await handler(
            CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name="create_pet", arguments={"name": "Fido"}
                ),
            )
        )

    assert result.root.isError is None or result.root.isError is False
    assert result.root.content[0].text == "Created"
    call_kwargs = mock_client.request.call_args
    assert call_kwargs[0][0] == "POST"
    assert call_kwargs[1]["json"] == {"name": "Fido"}


@pytest.mark.asyncio
async def test_call_tool_path_parameter_substitution(server):
    response = _mock_httpx_response(200, '{"id": 42}')
    ctx, mock_client = _patch_async_client(response)

    with ctx:
        handler = server.request_handlers[CallToolRequest]
        result = await handler(
            CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name="get_pet", arguments={"id": "42"}
                ),
            )
        )

    assert result.root.isError is None or result.root.isError is False
    call_url = mock_client.request.call_args[0][1]
    assert call_url == "http://localhost:3000/pets/42"

@pytest.mark.asyncio
async def test_call_tool_unknown_tool(server):
    handler = server.request_handlers[CallToolRequest]
    result = await handler(
        CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(name="nonexistent", arguments={}),
        )
    )

    assert result.root.isError is True
    assert "-32601" in result.root.content[0].text or "Unknown tool" in result.root.content[0].text

@pytest.mark.asyncio
async def test_upstream_400(server):
    response = _mock_httpx_response(400, "Bad Request")
    ctx, _ = _patch_async_client(response)

    with ctx:
        handler = server.request_handlers[CallToolRequest]
        result = await handler(
            CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name="list_pets", arguments={"limit": 1}
                ),
            )
        )

    assert result.root.isError is True
    assert "Upstream 400" in result.root.content[0].text


@pytest.mark.asyncio
async def test_upstream_500(server):
    response = _mock_httpx_response(500, "Internal Server Error")
    ctx, _ = _patch_async_client(response)

    with ctx:
        handler = server.request_handlers[CallToolRequest]
        result = await handler(
            CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name="list_pets", arguments={}
                ),
            )
        )

    assert result.root.isError is True
    assert "Upstream 500" in result.root.content[0].text


@pytest.mark.asyncio
async def test_connection_error(server):
    mock_client = AsyncMock()
    mock_client.request = AsyncMock(side_effect=httpx.ConnectError("refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    ctx = patch("openapi2mcp.server.httpx.AsyncClient", return_value=mock_client)

    with ctx:
        handler = server.request_handlers[CallToolRequest]
        result = await handler(
            CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name="list_pets", arguments={}
                ),
            )
        )

    assert result.root.isError is True
    assert "Connection error" in result.root.content[0].text

@pytest.mark.asyncio
async def test_bearer_auth_default(server):
    os.environ["API_KEY"] = "mykey"
    response = _mock_httpx_response(200, "OK")
    ctx, mock_client = _patch_async_client(response)

    with ctx:
        handler = server.request_handlers[CallToolRequest]
        await handler(
            CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name="list_pets", arguments={}
                ),
            )
        )

    headers = mock_client.request.call_args[1]["headers"]
    assert headers["Authorization"] == "Bearer mykey"


@pytest.mark.asyncio
async def test_api_key_auth(server):
    os.environ["API_KEY"] = "mykey"
    os.environ["API_AUTH_TYPE"] = "api-key"
    response = _mock_httpx_response(200, "OK")
    ctx, mock_client = _patch_async_client(response)

    with ctx:
        handler = server.request_handlers[CallToolRequest]
        await handler(
            CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name="list_pets", arguments={}
                ),
            )
        )

    headers = mock_client.request.call_args[1]["headers"]
    assert headers["X-API-Key"] == "mykey"
    assert "Authorization" not in headers


@pytest.mark.asyncio
async def test_no_auth(server):
    response = _mock_httpx_response(200, "OK")
    ctx, mock_client = _patch_async_client(response)

    with ctx:
        handler = server.request_handlers[CallToolRequest]
        await handler(
            CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name="list_pets", arguments={}
                ),
            )
        )

    headers = mock_client.request.call_args[1]["headers"]
    assert headers == {}
