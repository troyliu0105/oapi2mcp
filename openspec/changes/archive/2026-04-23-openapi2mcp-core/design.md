## Context

This is a greenfield Python project managed by `uv` (Python >=3.12). The codebase currently contains only a skeleton `main.py` and an empty `pyproject.toml` with no dependencies. There are no existing patterns to follow — we establish conventions here.

The tool converts an OpenAPI 3.x specification (local file or remote URL) into an MCP server that exposes every API endpoint as a tool. MCP clients (Claude Desktop, Cursor, etc.) connect via stdio, SSE, or streamable-http and invoke tools that transparently forward calls to the upstream API.

The official MCP Python SDK (`mcp` package, v1.27.0 on PyPI) provides both a high-level `FastMCP` API and a low-level `Server` API. We use the **low-level `Server`** because OpenAPI already gives us complete JSON Schemas — there is no need to manufacture typed Python functions just to have the SDK re-derive schemas from type hints.

## Goals / Non-Goals

**Goals:**

- Parse any valid OpenAPI 3.0/3.1 spec (JSON) from a local path or remote URL
- Resolve all `$ref` references recursively so tool schemas are self-contained
- Convert every operation into an MCP tool with a correct `inputSchema`
- Forward tool calls to the upstream API via `httpx.AsyncClient`
- Support stdio, SSE, and streamable-http transports
- Run via `uvx openapi2mcp` with zero configuration beyond the spec URL
- Comprehensive unit tests (pytest + pytest-asyncio)

**Non-Goals:**

- YAML spec support (JSON only for v1)
- OAuth2 flows with token refresh
- Schema validation beyond what is needed for conversion
- Request/response transformation hooks
- Tool filtering by tags or path patterns (future enhancement)
- Streaming responses from upstream API
- Code generation (this is a runtime proxy, not a codegen tool)

## Decisions

### Decision 1: Low-level `Server` API over `FastMCP`

**Choice**: Use `mcp.server.lowlevel.Server` with decorator-based handler registration (`@server.list_tools()` and `@server.call_tool()`).

**Rationale**: OpenAPI specs already contain complete JSON Schemas for parameters. Using `FastMCP.add_tool()` would require creating dummy Python functions with matching type hints so the SDK can introspect them — an unnecessary indirection. The low-level API lets us provide `inputSchema` directly, which is simpler and avoids `exec()` or dynamic function generation.

```python
server = Server("openapi2mcp")

@server.list_tools()
async def handle_list_tools():
    ...

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    ...
```

**Alternative considered**: `FastMCP.add_tool()` with closures — rejected because it adds complexity without benefit for our use case.

### Decision 2: `src/` layout with `src/openapi2mcp/` package

**Choice**: Use the `src` layout convention where the package lives under `src/openapi2mcp/`.

**Rationale**: This is the recommended Python packaging layout. It prevents accidental imports from the project root and works correctly with `uvx` / `pip install`.

### Decision 3: Dataclass-based internal model

**Choice**: A single `Operation` dataclass in `models.py` holds the normalized representation of an OpenAPI operation.

```python
@dataclass
class Operation:
    method: str              # "get", "post", etc.
    path: str                # "/users/{id}"
    operation_id: str        # "get_user"
    summary: str | None
    description: str | None
    parameters: list[dict]   # [{name, in, required, schema}]
    request_body_schema: dict | None  # resolved JSON Schema for body
    responses: dict          # kept for future use
```

**Rationale**: A flat dataclass is simpler than a Pydantic model for internal data transfer. No serialization needed — this never crosses a boundary.

### Decision 4: Parameter flattening with collision detection

**Choice**: All OpenAPI parameters (path, query, header) and request body properties are merged into a single `inputSchema` object. If a body property name collides with a path/query/header parameter name, the body property gets a `_body` suffix.

**Rationale**: MCP tools accept a single JSON object as arguments. The flattening approach is universal across all existing openapi-to-mcp tools. Collision detection prevents silent overwrites.

**Priority order** for same-name resolution: path > query > header > body (path wins, body renames).

### Decision 5: Base URL inference from spec URL

**Choice**: When the spec is loaded from a URL, the base URL is derived by stripping the last path segment (e.g., `http://host:3000/openapi.json` → `http://host:3000`).

**Priority**: `OPENAPI_BASE_URL` env var > inferred from spec URL > `servers[0].url` from spec > error (local file with no base URL specified).

### Decision 6: Authentication via environment variables

**Choice**: `API_KEY` env var is injected into requests. `API_AUTH_TYPE` controls the header format: `bearer` (default) sends `Authorization: Bearer <key>`, `api-key` sends `X-API-Key: <key>`.

**Rationale**: Environment variables work naturally with `uvx` and MCP client configs (e.g., Claude Desktop's `env` field). No CLI flags for secrets.

### Decision 7: Error wrapping

**Choice**: When the upstream API returns a non-2xx response, the tool raises `McpError` from `mcp.shared.exceptions` with the HTTP status code and response body as the error message.

```python
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData

raise McpError(
    ErrorData(code=-32603, message=f"Upstream {response.status_code}: {response.text}")
)
```

Note: The SDK's `McpError` takes an `ErrorData` object as its constructor argument. Use `ErrorData(code=..., message=...)` to construct it.

**Rationale**: MCP clients need to know a tool call failed and why. Wrapping preserves the upstream error details without leaking internal implementation.

### Decision 8: Module structure (4 core modules + CLI)

```
src/openapi2mcp/
├── __init__.py       # Package marker
├── cli.py            # argparse CLI, entrypoint
├── parser.py         # load_spec, resolve_refs, extract_operations, infer_base_url
├── converter.py      # build_input_schema, operation_to_tool
├── server.py         # create_server (low-level Server with handlers)
└── models.py         # Operation dataclass
```

**Rationale**: Each module has a single responsibility. The pipeline is linear: parse → convert → serve. No circular dependencies.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Large specs (100+ endpoints) may overwhelm MCP client context windows | Out of scope for v1; document as known limitation |
| `$ref` resolution may be incomplete for exotic OpenAPI features | Support standard `#/components/schemas/` refs; log warnings for unresolvable refs |
| No YAML support limits usability | Document JSON-only in v1; add YAML in future if requested |
| Async httpx in stdio mode adds complexity | stdio is request-response; async still works correctly with `anyio` event loop |
| Parameter name collisions in deeply nested body schemas | Only flatten top-level body properties; nested objects stay as-is |

### Decision 9: Transport wiring for low-level Server

**Choice**: Each transport requires manual wiring since the low-level `Server` does not have a unified `.run(transport=...)` method like `FastMCP`.

| Transport | Wiring |
|-----------|--------|
| **stdio** | `async with stdio_server() as (read, write): await server.run(read, write, init_opts)` |
| **SSE** | Create `SseServerTransport("/messages/")`, build Starlette routes (`/sse` GET + `/messages/` POST), run via `uvicorn` |
| **streamable-http** | Create `StreamableHTTPSessionManager(app=server)`, mount `session_manager.handle_request` on Starlette with async lifespan, run via `uvicorn` |

**Rationale**: Using the low-level Server API means we must handle transport wiring ourselves. This is explicit and debuggable, unlike FastMCP's magic. The SSE transport requires `sse-starlette` (pulled in as a transitive dependency of `mcp`).
