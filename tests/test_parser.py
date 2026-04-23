from __future__ import annotations

import json
from unittest.mock import Mock, patch

import pytest

from openapi2mcp.parser import extract_operations, infer_base_url, load_spec, resolve_refs

class TestLoadSpec:
    def test_remote_load_returns_parsed_dict(self):
        spec = {"openapi": "3.1.0", "info": {"title": "X"}}
        mock_resp = Mock(status_code=200)
        mock_resp.json.return_value = spec
        with patch("openapi2mcp.parser.httpx.get", return_value=mock_resp) as mock_get:
            result = load_spec("https://api.example.com/openapi.json")
        mock_get.assert_called_once_with("https://api.example.com/openapi.json")
        assert result == spec

    def test_remote_non_200_raises_runtime_error(self):
        mock_resp = Mock(status_code=404, text="Not Found")
        with patch("openapi2mcp.parser.httpx.get", return_value=mock_resp):
            with pytest.raises(RuntimeError, match="HTTP 404"):
                load_spec("https://api.example.com/openapi.json")

    def test_local_load_returns_parsed_dict(self, tmp_path):
        spec = {"openapi": "3.1.0", "info": {"title": "Local"}}
        spec_file = tmp_path / "openapi.json"
        spec_file.write_text(json.dumps(spec), encoding="utf-8")
        result = load_spec(str(spec_file))
        assert result == spec

    def test_local_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError, match="Spec file not found"):
            load_spec("/nonexistent/path.json")

class TestResolveRefs:
    def test_simple_ref_resolves(self):
        schema = {"$ref": "#/components/schemas/Pet"}
        components = {"schemas": {"Pet": {"type": "object"}}}
        result = resolve_refs(schema, components)
        assert result == {"type": "object"}

    def test_nested_ref_resolves_recursively(self):
        schema = {
            "type": "object",
            "properties": {"pet": {"$ref": "#/components/schemas/Pet"}},
        }
        components = {"schemas": {"Pet": {"type": "object", "properties": {"name": {"type": "string"}}}}}
        result = resolve_refs(schema, components)
        assert result["properties"]["pet"] == {"type": "object", "properties": {"name": {"type": "string"}}}

    def test_unresolvable_ref_returns_original(self):
        schema = {"$ref": "#/components/schemas/Missing"}
        result = resolve_refs(schema, {})
        assert result == {"$ref": "#/components/schemas/Missing"}

class TestExtractOperations:
    def test_with_operation_id(self, sample_spec):
        ops = extract_operations(sample_spec)
        ids = {o.operation_id for o in ops}
        assert "list_pets" in ids
        assert "create_pet" in ids

    def test_without_operation_id_generates_fallback(self, sample_spec):
        ops = extract_operations(sample_spec)
        fallback = [o for o in ops if o.path == "/pets/{id}" and o.method == "get"]
        assert len(fallback) == 1
        assert fallback[0].operation_id == "get__pets_id"

    def test_request_body_ref_resolved(self, sample_spec):
        ops = extract_operations(sample_spec)
        create = next(o for o in ops if o.operation_id == "create_pet")
        assert create.request_body_schema is not None
        assert create.request_body_schema["type"] == "object"
        assert "name" in create.request_body_schema["properties"]

class TestInferBaseUrl:
    def test_url_with_path(self):
        assert infer_base_url("http://127.0.0.1:3000/openapi.json") == "http://127.0.0.1:3000"

    def test_url_with_nested_path(self):
        assert infer_base_url("https://api.example.com/v2/spec.json") == "https://api.example.com/v2"

    def test_local_path_returns_none(self):
        assert infer_base_url("/some/local/file.json") is None
