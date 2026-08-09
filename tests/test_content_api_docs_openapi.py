"""Tests for OpenAPI spec generation."""

from __future__ import annotations

import pytest
from personal_index.content_api_docs import (
    generate_openapi_spec,
    EndpointDoc,
    ParameterDoc,
    ResponseDoc,
)


class TestOpenAPISpec:
    def test_spec_version(self):
        spec = generate_openapi_spec()
        assert spec["openapi"] == "3.0.3"

    def test_spec_info(self):
        spec = generate_openapi_spec()
        assert spec["info"]["title"] == "Personal Index API"
        assert spec["info"]["version"] == "1.0.0"

    def test_spec_security_scheme(self):
        spec = generate_openapi_spec()
        assert "ApiKeyAuth" in spec["components"]["securitySchemes"]

    def test_spec_with_get_endpoint(self):
        endpoints = [
            EndpointDoc(
                path="/items", method="GET", summary="List items",
                responses=[ResponseDoc(status_code=200, description="OK")],
            )
        ]
        spec = generate_openapi_spec(endpoints=endpoints)
        assert "get" in spec["paths"]["/items"]

    def test_spec_with_post_endpoint(self):
        endpoints = [
            EndpointDoc(
                path="/items", method="POST", summary="Create item",
                responses=[ResponseDoc(status_code=201, description="Created")],
            )
        ]
        spec = generate_openapi_spec(endpoints=endpoints)
        assert "post" in spec["paths"]["/items"]

    def test_spec_with_parameters(self):
        endpoints = [
            EndpointDoc(
                path="/items", method="GET", summary="List",
                parameters=[ParameterDoc(name="page", param_type="integer", required=False)],
                responses=[ResponseDoc(status_code=200, description="OK")],
            )
        ]
        spec = generate_openapi_spec(endpoints=endpoints)
        params = spec["paths"]["/items"]["get"]["parameters"]
        assert len(params) == 1
        assert params[0]["name"] == "page"

    def test_spec_with_auth(self):
        endpoints = [
            EndpointDoc(
                path="/items", method="GET", summary="List",
                auth_required=True,
                responses=[ResponseDoc(status_code=200, description="OK")],
            )
        ]
        spec = generate_openapi_spec(endpoints=endpoints)
        assert "security" in spec["paths"]["/items"]["get"]
