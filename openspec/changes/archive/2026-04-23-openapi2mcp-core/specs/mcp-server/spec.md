## ADDED Requirements

### Requirement: Create MCP server from operations
The system SHALL create a low-level `mcp.server.lowlevel.Server` instance with `@server.list_tools()` and `@server.call_tool()` decorator-based handler registration.

#### Scenario: Server creation with multiple operations
- **WHEN** a list of operations and a base URL are provided
- **THEN** the server SHALL be configured with all operations as tools and store the base URL for request forwarding

### Requirement: List all tools
The `on_list_tools` handler SHALL return a `types.ListToolsResult` containing all converted `types.Tool` objects.

#### Scenario: List tools returns correct tools
- **WHEN** the MCP client requests the tool list
- **THEN** the server SHALL return a `ListToolsResult` with one `types.Tool` per operation, each with correct `name`, `description`, and `inputSchema`

### Requirement: Execute tool call via HTTP forwarding
The `on_call_tool` handler SHALL forward the tool invocation as an HTTP request to the upstream API and return a `types.CallToolResult`.

#### Scenario: Successful GET request
- **WHEN** a tool is called for a GET operation with query parameters
- **THEN** the server SHALL build the URL with path parameters filled, send query parameters, and return a `CallToolResult` containing `TextContent` with the response body

#### Scenario: Successful POST request with body
- **WHEN** a tool is called for a POST operation with request body
- **THEN** the server SHALL send the JSON body to the correct URL and return a `CallToolResult` containing `TextContent` with the response

#### Scenario: Path parameter substitution
- **WHEN** the operation path is `/users/{id}` and arguments contain `id=42`
- **THEN** the server SHALL substitute to produce `/users/42` in the final URL

#### Scenario: Unknown tool name
- **WHEN** `call_tool` receives a tool name that does not match any operation
- **THEN** the server SHALL raise `McpError` with a method-not-found error

### Requirement: Wrap upstream errors as MCP errors
The system SHALL wrap non-2xx upstream responses as `McpError` (from `mcp.shared.exceptions`) with an `ErrorData(code=..., message=...)` object as the constructor argument.

#### Scenario: Upstream returns 400
- **WHEN** the upstream API returns a 400 status code
- **THEN** the server SHALL raise `McpError(ErrorData(code=-32603, message=...))` with message containing `"Upstream 400"` and the response body

#### Scenario: Upstream returns 500
- **WHEN** the upstream API returns a 500 status code
- **THEN** the server SHALL raise `McpError(ErrorData(code=-32603, message=...))` with message containing `"Upstream 500"` and the response body

#### Scenario: Upstream is unreachable
- **WHEN** the HTTP request fails due to a connection error
- **THEN** the server SHALL raise `McpError(ErrorData(code=-32603, message=...))` with a message describing the connection failure

### Requirement: Inject authentication headers
The system SHALL inject authentication headers into upstream requests based on environment variables.

#### Scenario: Bearer auth (default)
- **WHEN** `API_KEY` is set and `API_AUTH_TYPE` is `bearer` (or unset)
- **THEN** all upstream requests SHALL include `Authorization: Bearer <API_KEY>` header

#### Scenario: API key auth
- **WHEN** `API_KEY` is set and `API_AUTH_TYPE` is `api-key`
- **THEN** all upstream requests SHALL include `X-API-Key: <API_KEY>` header

#### Scenario: No auth
- **WHEN** `API_KEY` is not set
- **THEN** no authentication headers SHALL be added

### Requirement: Support stdio transport
The server SHALL run on stdio transport when `--transport stdio` is specified (default), using `mcp.server.stdio.stdio_server()` to obtain read/write streams and passing them to `server.run()`.

#### Scenario: Default stdio mode
- **WHEN** no transport is specified
- **THEN** the server SHALL use `stdio_server()` context manager to get read/write streams and call `await server.run(read, write, init_options)`

### Requirement: Support SSE transport
The server SHALL run on SSE transport when `--transport sse` is specified, using `SseServerTransport` to create a Starlette app with SSE endpoints, run via `uvicorn`.

#### Scenario: SSE with host and port
- **WHEN** `--transport sse --host 0.0.0.0 --port 8000` is specified
- **THEN** the server SHALL create a `SseServerTransport`, mount Starlette routes (`/sse` for GET, `/messages/` for POST), and start `uvicorn` listening on `0.0.0.0:8000`

### Requirement: Support streamable-http transport
The server SHALL run on streamable-http transport when `--transport streamable-http` is specified, using `StreamableHTTPSessionManager(app=server)` to create a session manager, mounted as a Starlette app with lifespan, run via `uvicorn`.

#### Scenario: Streamable HTTP with host and port
- **WHEN** `--transport streamable-http --host 0.0.0.0 --port 8000` is specified
- **THEN** the server SHALL create a `StreamableHTTPSessionManager(app=server)`, mount its `handle_request` on a Starlette app with an async lifespan context, and start `uvicorn` listening on `0.0.0.0:8000`
