"""OpenAPI specification loading and parsing."""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from openapi2mcp.models import Operation


def load_spec(source: str) -> dict:
    if source.startswith(("http://", "https://")):
        response = httpx.get(source)
        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to fetch spec from {source}: HTTP {response.status_code}"
            )
        return response.json()

    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Spec file not found: {source}")
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_refs(
    schema: dict, components: dict, _visited: set[str] | None = None
) -> dict:
    if not isinstance(schema, dict):
        return schema

    if _visited is None:
        _visited = set()

    if "$ref" in schema:
        ref = schema["$ref"]
        if ref.startswith("#/components/schemas/"):
            if ref in _visited:
                return schema
            name = ref.split("/")[-1]
            resolved = components.get("schemas", {}).get(name)
            if resolved is not None:
                return resolve_refs(resolved, components, _visited | {ref})
        return schema

    result = {}
    for key, value in schema.items():
        if isinstance(value, dict):
            result[key] = resolve_refs(value, components, _visited)
        elif isinstance(value, list):
            result[key] = [
                resolve_refs(item, components, _visited)
                if isinstance(item, dict)
                else item
                for item in value
            ]
        else:
            result[key] = value
    return result


def extract_operations(spec: dict) -> list[Operation]:
    methods = {"get", "post", "put", "patch", "delete"}
    components = spec.get("components", {})
    operations: list[Operation] = []

    for path, path_item in spec.get("paths", {}).items():
        for method in methods:
            operation = path_item.get(method)
            if operation is None:
                continue

            operation_id = operation.get("operationId") or _generate_operation_id(
                method, path
            )

            request_body_schema = None
            request_body = operation.get("requestBody")
            if request_body:
                content = request_body.get("content", {})
                json_content = content.get("application/json", {})
                raw_schema = json_content.get("schema")
                if raw_schema:
                    request_body_schema = resolve_refs(raw_schema, components)

            operations.append(
                Operation(
                    method=method,
                    path=path,
                    operation_id=operation_id,
                    summary=operation.get("summary"),
                    description=operation.get("description"),
                    parameters=operation.get("parameters", []),
                    request_body_schema=request_body_schema,
                    responses=operation.get("responses", {}),
                )
            )

    return operations


def _generate_operation_id(method: str, path: str) -> str:
    return f"{method}_{path}".replace("/", "_").replace("{", "").replace("}", "").strip("_")


def infer_base_url(source: str) -> str | None:
    if not source.startswith(("http://", "https://")):
        return None
    stripped = source.split("://", 1)
    scheme = stripped[0]
    rest = stripped[1]
    if "/" not in rest:
        return source
    return source.rsplit("/", 1)[0]
