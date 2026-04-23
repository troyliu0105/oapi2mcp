"""Shared test fixtures for openapi2mcp."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def sample_spec() -> dict:
    """A minimal but realistic OpenAPI 3.1 spec with $ref usage."""
    return {
        "openapi": "3.1.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "servers": [{"url": "http://localhost:3000"}],
        "paths": {
            "/pets": {
                "get": {
                    "operationId": "list_pets",
                    "summary": "List all pets",
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer"},
                        }
                    ],
                    "responses": {"200": {"description": "OK"}},
                },
                "post": {
                    "operationId": "create_pet",
                    "summary": "Create a pet",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Pet"}
                            }
                        },
                        "required": True,
                    },
                    "responses": {"201": {"description": "Created"}},
                },
            },
            "/pets/{id}": {
                "get": {
                    "summary": "Get a pet by ID",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {"200": {"description": "OK"}},
                }
            },
        },
        "components": {
            "schemas": {
                "Pet": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "tag": {"type": "string"},
                    },
                    "required": ["name"],
                },
                "NestedRef": {
                    "type": "object",
                    "properties": {
                        "pet": {"$ref": "#/components/schemas/Pet"},
                    },
                },
            }
        },
    }


@pytest.fixture
def mock_httpx_response():
    """Factory fixture to build a mock httpx.Response."""

    def _make(
        status_code: int = 200,
        text: str = "OK",
        json_data: object = None,
    ) -> AsyncMock:
        resp = AsyncMock()
        resp.status_code = status_code
        resp.text = text
        if json_data is not None:
            resp.json.return_value = json_data
        return resp

    return _make
