## Why

There is no simple, framework-agnostic Python library that converts an OpenAPI specification into a working MCP (Model Context Protocol) server. Existing solutions either lock you into the FastMCP framework, are configuration-heavy, or are not written in Python. We need a lean tool that parses any OpenAPI 3.x spec, dynamically registers every endpoint as an MCP tool, and serves them over stdio, SSE, or streamable-http — runnable via `uvx` with zero setup.

## What Changes

- Add a complete `openapi2mcp` Python package with CLI entrypoint (`openapi2mcp` command)
- Implement OpenAPI spec parsing with `$ref` resolution, supporting both local file paths and remote URLs
- Convert every OpenAPI operation (path + method) into an MCP tool with a proper `inputSchema` built from path, query, header, and body parameters
- Serve tools via the low-level MCP `Server` API, supporting stdio, SSE, and streamable-http transports
- Forward MCP tool calls to the upstream API using `httpx.AsyncClient` with environment-variable-based authentication
- Wrap upstream HTTP errors as MCP errors with diagnostic information
- Provide comprehensive unit tests using pytest + pytest-asyncio with both mocks and real HTTP stubs
- Make the tool installable and runnable via `uvx openapi2mcp`

## Capabilities

### New Capabilities

- `spec-loading`: Load and parse OpenAPI specs from local files or remote URLs, with recursive `$ref` resolution and automatic base URL inference from the spec URL
- `tool-conversion`: Convert OpenAPI operations into MCP tools by flattening path, query, header, and body parameters into a single `inputSchema` object, with collision detection for duplicate parameter names
- `mcp-server`: Create and run an MCP server using the low-level SDK `Server` API, serving all converted tools over stdio, SSE, or streamable-http transports, with async HTTP forwarding and error wrapping

### Modified Capabilities

(none — this is a new project)

## Impact

- **New files**: `src/openapi2mcp/` package with `cli.py`, `parser.py`, `converter.py`, `server.py`, `models.py`
- **New files**: `tests/` directory with `conftest.py`, `test_parser.py`, `test_converter.py`, `test_server.py`
- **Modified files**: `pyproject.toml` — add dependencies (`mcp>=1.27.0`, `httpx`), entrypoint, test deps
- **Dependencies**: `mcp>=1.27.0` (MCP SDK, low-level Server API), `httpx` (async HTTP client)
- **Runtime**: Python >=3.12, managed by `uv`
- **Distribution**: Published to PyPI, runnable via `uvx openapi2mcp`
