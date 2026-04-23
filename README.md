# oapi2mcp

Convert any OpenAPI 3.x specification into a working MCP (Model Context Protocol) server — zero configuration, zero code.

[![PyPI](https://img.shields.io/pypi/v/oapi2mcp)](https://pypi.org/project/oapi2mcp/)
[![Python](https://img.shields.io/pypi/pyversions/oapi2mcp)](https://pypi.org/project/oapi2mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Quick Start

```bash
# Run directly with uvx — no install needed
uvx oapi2mcp --spec http://localhost:3000/openapi.json

# Or install with pip
pip install oapi2mcp
oapi2mcp --spec http://localhost:3000/openapi.json
```

That's it. Every endpoint in your OpenAPI spec is now available as an MCP tool.

## How It Works

1. **Parses** your OpenAPI 3.x spec (local file or remote URL)
2. **Resolves** all `$ref` references recursively
3. **Converts** every operation into an MCP tool with a proper `inputSchema`
4. **Serves** tools over stdio, SSE, or streamable-http
5. **Forwards** tool calls to the upstream API via HTTP

## Configuration

### CLI Options

```
oapi2mcp --spec <SPEC> [--transport TRANSPORT] [--host HOST] [--port PORT] [--base-url URL]
```

| Option         | Default     | Description                              |
| -------------- | ----------- | ---------------------------------------- |
| `--spec`       | *required*  | URL or local path to OpenAPI spec (JSON) |
| `--transport`  | `stdio`     | Transport: `stdio`, `sse`, `streamable-http` |
| `--host`       | `127.0.0.1` | Host for SSE/streamable-http             |
| `--port`       | `8000`      | Port for SSE/streamable-http             |
| `--base-url`   | *auto*      | Override base URL for upstream API calls  |

### Base URL Resolution

Base URL is resolved in this priority order:

1. `OPENAPI_BASE_URL` environment variable
2. `--base-url` CLI flag
3. Inferred from spec URL (strip last path segment)
4. `servers[0].url` from the spec itself

### Authentication

Set environment variables to inject auth headers into upstream requests:

```bash
# Bearer token (default)
export API_KEY=your-token-here

# API key header
export API_KEY=your-key-here
export API_AUTH_TYPE=api-key
```

## MCP Client Integration

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "my-api": {
      "command": "uvx",
      "args": ["oapi2mcp", "--spec", "https://api.example.com/openapi.json"],
      "env": {
        "API_KEY": "your-token"
      }
    }
  }
}
```

### SSE / Streamable HTTP

```bash
# SSE transport
oapi2mcp --spec https://api.example.com/openapi.json --transport sse --port 8000

# Streamable HTTP transport
oapi2mcp --spec https://api.example.com/openapi.json --transport streamable-http --port 8000
```

## Features

- **Recursive `$ref` resolution** — handles nested references in components
- **Collision detection** — renames body properties that conflict with path/query/header params
- **Fallback `operationId`** — auto-generates from method + path when missing
- **Error wrapping** — upstream HTTP errors surface as MCP errors with diagnostics
- **3 transports** — stdio (default), SSE, and streamable-http

## Requirements

- Python >= 3.10
- An OpenAPI 3.x spec in JSON format

## Disclaimer

This project was generated with the assistance of AI. While it has been tested, it may contain bugs or unexpected behavior. Use at your own risk. The author assumes no responsibility or liability for any damages or losses arising from the use of this software.

## License

[MIT](LICENSE)
