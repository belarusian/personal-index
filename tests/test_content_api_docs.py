"""Tests for content_api_docs module - API documentation."""

from __future__ import annotations

import pytest
from personal_index.content_api_docs import (
    APIDocumentation,
    EndpointDoc,
    ParameterDoc,
    ResponseDoc,
    generate_openapi_spec,
    generate_markdown_docs,
    generate_swagger_ui_html,
    DocumentationBuilder,
    DocSection,
)


class TestParameterDoc:
    def test_parameter_doc_basic(self):
        p = ParameterDoc(name="id", param_type="string", required=True)
        assert p.name == "id"
        assert p.param_type == "string"
        assert p.required is True

    def test_parameter_doc_optional(self):
        p = ParameterDoc(name="page", param_type="integer", required=False, default=1)
        assert p.required is False
        assert p.default == 1

    def test_parameter_doc_with_description(self):
        p = ParameterDoc(
            name="query",
            param_type="string",
            required=True,
            description="Search query string",
        )
        assert p.description == "Search query string"

    def test_parameter_doc_to_dict(self):
        p = ParameterDoc(name="limit", param_type="integer", required=False, default=20)
        d = p.to_dict()
        assert d["name"] == "limit"
        assert d["type"] == "integer"


class TestResponseDoc:
    def test_response_doc_basic(self):
        r = ResponseDoc(status_code=200, description="Success")
        assert r.status_code == 200
        assert r.description == "Success"

    def test_response_doc_with_schema(self):
        r = ResponseDoc(
            status_code=200,
            description="Success",
            schema={"type": "object", "properties": {"data": "object"}},
        )
        assert r.schema == {"type": "object", "properties": {"data": "object"}}

    def test_response_doc_to_dict(self):
        r = ResponseDoc(status_code=404, description="Not found")
        d = r.to_dict()
        assert d["status_code"] == 404
        assert d["description"] == "Not found"


class TestEndpointDoc:
    def test_endpoint_doc_basic(self):
        e = EndpointDoc(
            path="/api/v1/content/items",
            method="GET",
            summary="List content items",
        )
        assert e.path == "/api/v1/content/items"
        assert e.method == "GET"
        assert e.summary == "List content items"

    def test_endpoint_doc_with_params(self):
        params = [ParameterDoc(name="page", param_type="integer", required=False)]
        e = EndpointDoc(
            path="/api/v1/content/items",
            method="GET",
            summary="List items",
            parameters=params,
        )
        assert len(e.parameters) == 1

    def test_endpoint_doc_with_responses(self):
        responses = [ResponseDoc(status_code=200, description="Success")]
        e = EndpointDoc(
            path="/api/v1/content/items",
            method="GET",
            summary="List items",
            responses=responses,
        )
        assert len(e.responses) == 1

    def test_endpoint_doc_to_dict(self):
        e = EndpointDoc(path="/test", method="GET", summary="Test")
        d = e.to_dict()
        assert d["path"] == "/test"
        assert d["method"] == "GET"


class TestDocSection:
    def test_doc_section_basic(self):
        s = DocSection(title="Authentication", content="Use API keys")
        assert s.title == "Authentication"
        assert s.content == "Use API keys"

    def test_doc_section_with_endpoints(self):
        endpoints = [EndpointDoc(path="/auth", method="POST", summary="Authenticate")]
        s = DocSection(title="Auth", content="", endpoints=endpoints)
        assert len(s.endpoints) == 1

    def test_doc_section_to_dict(self):
        s = DocSection(title="Test", content="Test content")
        d = s.to_dict()
        assert d["title"] == "Test"


class TestAPIDocumentation:
    def test_init(self):
        docs = APIDocumentation()
        assert docs is not None

    def test_add_endpoint(self):
        docs = APIDocumentation()
        docs.add_endpoint(EndpointDoc(path="/test", method="GET", summary="Test"))
        assert len(docs.endpoints) == 1

    def test_add_section(self):
        docs = APIDocumentation()
        docs.add_section(DocSection(title="Test", content="Test"))
        assert len(docs.sections) == 1

    def test_get_endpoint_by_path(self):
        docs = APIDocumentation()
        ep = EndpointDoc(path="/test", method="GET", summary="Test")
        docs.add_endpoint(ep)
        found = docs.get_endpoint_by_path("/test")
        assert found == ep

    def test_get_endpoint_not_found(self):
        docs = APIDocumentation()
        found = docs.get_endpoint_by_path("/missing")
        assert found is None

    def test_generate_full_docs(self):
        docs = APIDocumentation()
        result = docs.generate()
        assert isinstance(result, dict)


class TestDocumentationBuilder:
    def test_builder_init(self):
        builder = DocumentationBuilder()
        assert builder is not None

    def test_builder_add_endpoint(self):
        builder = DocumentationBuilder()
        builder.add_endpoint(EndpointDoc(path="/test", method="GET", summary="Test"))
        assert len(builder.endpoints) == 1

    def test_builder_build(self):
        builder = DocumentationBuilder()
        result = builder.build()
        assert isinstance(result, dict)


class TestGenerateOpenAPISpec:
    def test_generate_spec(self):
        spec = generate_openapi_spec()
        assert "openapi" in spec
        assert "info" in spec
        assert "paths" in spec

    def test_generate_spec_with_endpoints(self):
        endpoints = [
            EndpointDoc(path="/items", method="GET", summary="List items"),
        ]
        spec = generate_openapi_spec(endpoints=endpoints)
        assert "/items" in spec["paths"]


class TestGenerateMarkdownDocs:
    def test_generate_markdown(self):
        md = generate_markdown_docs()
        assert isinstance(md, str)
        assert "# API Documentation" in md

    def test_generate_markdown_with_endpoints(self):
        endpoints = [
            EndpointDoc(path="/items", method="GET", summary="List items"),
        ]
        md = generate_markdown_docs(endpoints=endpoints)
        assert "/items" in md


class TestGenerateSwaggerUIHTML:
    def test_generate_html(self):
        html = generate_swagger_ui_html()
        assert isinstance(html, str)
        assert "<!DOCTYPE html>" in html or "<html" in html.lower()
