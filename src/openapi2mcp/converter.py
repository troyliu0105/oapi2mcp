from __future__ import annotations

from mcp import types

from openapi2mcp.models import Operation


def build_input_schema(operation: Operation) -> dict:
    properties: dict = {}
    required: list[str] = []

    for param in operation.parameters:
        name = param["name"]
        properties[name] = param.get("schema", {"type": "string"})
        if param.get("required"):
            required.append(name)

    if operation.request_body_schema and "properties" in operation.request_body_schema:
        body_required = set(operation.request_body_schema.get("required", []))
        for prop_name, prop_schema in operation.request_body_schema["properties"].items():
            key = prop_name if prop_name not in properties else f"{prop_name}_body"
            properties[key] = prop_schema
            if prop_name in body_required:
                required.append(key)

    schema: dict = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def operation_to_tool(operation: Operation) -> types.Tool:
    description = operation.summary or operation.description or f"{operation.method.upper()} {operation.path}"
    return types.Tool(
        name=operation.operation_id,
        description=description,
        inputSchema=build_input_schema(operation),
    )
