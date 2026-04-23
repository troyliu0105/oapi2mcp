from __future__ import annotations

from openapi2mcp.converter import build_input_schema, operation_to_tool
from openapi2mcp.models import Operation


class TestBuildInputSchema:
    def test_path_params_only(self):
        op = Operation(
            method="get",
            path="/pets/{id}",
            operation_id="get_pet",
            parameters=[{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
        )
        schema = build_input_schema(op)

        assert schema == {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}

    def test_query_params_only(self):
        op = Operation(
            method="get",
            path="/pets",
            operation_id="list_pets",
            parameters=[{"name": "limit", "in": "query", "required": False, "schema": {"type": "integer"}}],
        )
        schema = build_input_schema(op)

        assert schema["properties"]["limit"] == {"type": "integer"}
        assert "required" not in schema

    def test_mixed_params(self):
        op = Operation(
            method="get",
            path="/pets/{id}",
            operation_id="get_pet_with_limit",
            parameters=[
                {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}},
                {"name": "limit", "in": "query", "required": False, "schema": {"type": "integer"}},
            ],
        )
        schema = build_input_schema(op)

        assert "id" in schema["properties"]
        assert "limit" in schema["properties"]
        assert schema["required"] == ["id"]

    def test_with_body(self):
        op = Operation(
            method="post",
            path="/pets",
            operation_id="create_pet",
            parameters=[],
            request_body_schema={
                "type": "object",
                "properties": {"name": {"type": "string"}, "tag": {"type": "string"}},
                "required": ["name"],
            },
        )
        schema = build_input_schema(op)

        assert schema["properties"]["name"] == {"type": "string"}
        assert schema["properties"]["tag"] == {"type": "string"}
        assert "name" in schema["required"]

    def test_collision_detection(self):
        op = Operation(
            method="put",
            path="/pets/{id}",
            operation_id="update_pet",
            parameters=[{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
            request_body_schema={
                "type": "object",
                "properties": {"id": {"type": "integer"}, "name": {"type": "string"}},
                "required": ["id"],
            },
        )
        schema = build_input_schema(op)

        assert schema["properties"]["id"] == {"type": "string"}
        assert schema["properties"]["id_body"] == {"type": "integer"}
        assert "id_body" in schema["required"]

    def test_no_params(self):
        op = Operation(method="get", path="/health", operation_id="health_check")
        schema = build_input_schema(op)

        assert schema == {"type": "object", "properties": {}}


class TestOperationToTool:
    def test_with_summary(self):
        op = Operation(method="get", path="/pets", operation_id="list_pets", summary="List all pets")
        tool = operation_to_tool(op)

        assert tool.description == "List all pets"

    def test_with_description_no_summary(self):
        op = Operation(method="get", path="/pets", operation_id="list_pets", description="Returns pets")
        tool = operation_to_tool(op)

        assert tool.description == "Returns pets"

    def test_no_summary_or_description(self):
        op = Operation(method="post", path="/pets", operation_id="create_pet")
        tool = operation_to_tool(op)

        assert tool.description == "POST /pets"

    def test_tool_name(self):
        op = Operation(method="get", path="/pets", operation_id="list_pets", summary="List")
        tool = operation_to_tool(op)

        assert tool.name == "list_pets"

    def test_input_schema(self):
        op = Operation(
            method="get",
            path="/pets/{id}",
            operation_id="get_pet",
            summary="Get pet",
            parameters=[{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
        )
        tool = operation_to_tool(op)
        expected = build_input_schema(op)

        assert tool.inputSchema == expected
