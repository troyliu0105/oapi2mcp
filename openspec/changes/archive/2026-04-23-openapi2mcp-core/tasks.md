## 1. Project Setup

- [x] 1.1 Update `pyproject.toml`: add `mcp>=1.27.0`, `httpx` as dependencies; add `pytest`, `pytest-asyncio` as dev dependencies; add `[project.scripts]` entrypoint `openapi2mcp = "openapi2mcp.cli:main"`; set `requires-python = ">=3.12"`
- [x] 1.2 Create `src/openapi2mcp/__init__.py` (empty package marker)
- [x] 1.3 Create `tests/conftest.py` with shared fixtures (sample OpenAPI spec dict, mock httpx client)

## 2. Data Model

- [x] 2.1 Create `src/openapi2mcp/models.py` with the `Operation` dataclass containing fields: `method`, `path`, `operation_id`, `summary`, `description`, `parameters`, `request_body_schema`, `responses`

## 3. Parser Module

- [x] 3.1 Implement `load_spec(source: str) -> dict` in `parser.py` — detect URL vs local path, use `httpx` for remote, `pathlib` for local
- [x] 3.2 Implement `resolve_refs(schema: dict, components: dict) -> dict` in `parser.py` — recursively replace `$ref` with resolved content, handle nested refs
- [x] 3.3 Implement `extract_operations(spec: dict) -> list[Operation]` in `parser.py` — iterate `paths`, create `Operation` per method, generate `operationId` fallback from method + path
- [x] 3.4 Implement `infer_base_url(source: str) -> str | None` in `parser.py` — strip last path segment from URL, return `None` for local paths
- [x] 3.5 Write `tests/test_parser.py`: test remote load (mock httpx), local load (tmp file), $ref resolution (simple + nested + unresolvable), operation extraction (with and without operationId), base URL inference

## 4. Converter Module

- [x] 4.1 Implement `build_input_schema(operation: Operation) -> dict` in `converter.py` — merge path/query/header params and body props into single JSON Schema object
- [x] 4.2 Implement collision detection in `build_input_schema` — when body prop name conflicts with path/query/header param, rename body prop with `_body` suffix
- [x] 4.3 Implement `operation_to_tool(operation: Operation) -> types.Tool` in `converter.py` — create MCP Tool with name=operationId, description (summary || description || fallback), and inputSchema
- [x] 4.4 Write `tests/test_converter.py`: test schema merging (path only, mixed, with body, no params), collision detection, tool name/description generation including fallback

## 5. Server Module

- [x] 5.1 Implement `create_server(operations, base_url) -> Server` in `server.py` — create low-level `Server` with `@server.list_tools()` and `@server.call_tool()` decorator registration
- [x] 5.2 Implement `on_list_tools` handler — return list of `types.Tool` from operations via `@server.list_tools()` decorator
- [x] 5.3 Implement `on_call_tool` handler — find operation by name (raise `McpError` if unknown), build URL with path param substitution, separate query/body args, send async HTTP request via `httpx.AsyncClient`, return `[types.TextContent(type="text", text=...)]`
- [x] 5.4 Implement error wrapping — catch non-2xx responses and httpx errors, raise `McpError(ErrorData(code=-32603, message=...))` from `mcp.shared.exceptions`
- [x] 5.5 Implement auth header injection — read `API_KEY` and `API_AUTH_TYPE` from env at request time, attach `Authorization` or `X-API-Key` header
- [x] 5.6 Write `tests/test_server.py`: test list_tools output, call_tool with mock HTTP (success GET/POST, path substitution, unknown tool name), error wrapping (400, 500, connection error), auth header injection

## 6. CLI Module

- [x] 6.1 Implement `cli.py` with argparse: `--spec` (required), `--transport` (default "stdio"), `--host` (default "127.0.0.1"), `--port` (default 8000), `--base-url` (optional)
- [x] 6.2 Wire CLI to parser → converter → server pipeline, resolve base URL priority (env var > CLI flag > inferred > spec servers > error)
- [x] 6.3 Implement transport dispatch: stdio via `stdio_server()` + `anyio.run`; SSE via `SseServerTransport` + Starlette + uvicorn; streamable-http via `StreamableHTTPSessionManager` + Starlette + uvicorn

## 7. Integration Verification

- [x] 7.1 Run `uv sync` and verify all dependencies install correctly
- [x] 7.2 Run `uvx openapi2mcp --help` and verify CLI is accessible
- [x] 7.3 Run full test suite with `uv run pytest` and ensure all tests pass
