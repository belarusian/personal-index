"""Integration tests for docs module."""

from __future__ import annotations

import pytest
from personal_index.content_api_docs import (
    APIDocumentation, EndpointDoc, ParameterDoc, ResponseDoc,
    DocSection, DocumentationBuilder,
    generate_openapi_spec, generate_markdown_docs,
)


class TestDocsIntegration:
    def test_full_documentation(self):
        docs = APIDocumentation()
        docs.add_endpoint(
            EndpointDoc(
                path="/items", method="GET", summary="List items",
                parameters=[ParameterDoc(name="page", param_type="integer", required=False)],
                responses=[ResponseDoc(status_code=200, description="OK")],
            )
        )
        docs.add_section(DocSection(title="Content", content="Content API"))
        result = docs.generate()
        assert len(result["endpoints"]) == 1
        assert len(result["sections"]) == 1

    def test_openapi_from_docs(self):
        docs = APIDocumentation()
        docs.add_endpoint(
            EndpointDoc(
                path="/items", method="GET", summary="List",
                responses=[ResponseDoc(status_code=200, description="OK")],
            )
        )
        spec = generate_openapi_spec(docs.endpoints)
        assert "/items" in spec["paths"]

    def test_markdown_from_docs(self):
        docs = APIDocumentation()
        docs.add_endpoint(
            EndpointDoc(path="/items", method="GET", summary="List")
        )
        md = generate_markdown_docs(docs.endpoints)
        assert "### GET /items" in md

    def test_builder_to_openapi(self):
        builder = DocumentationBuilder()
        builder.add_endpoint(
            EndpointDoc(
                path="/items", method="GET", summary="List",
                responses=[ResponseDoc(status_code=200, description="OK")],
            )
        )
        built = builder.build()
        spec = generate_openapi_spec(builder.endpoints)
        assert "/items" in spec["paths"]
