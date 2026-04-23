"""Internal data model for openapi2mcp."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Operation:
    """Normalized representation of a single OpenAPI operation."""

    method: str
    path: str
    operation_id: str
    summary: str | None = None
    description: str | None = None
    parameters: list[dict] = field(default_factory=list)
    request_body_schema: dict | None = None
    responses: dict = field(default_factory=dict)
