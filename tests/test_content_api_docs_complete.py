"""Complete docs module tests."""

from __future__ import annotations

import pytest
from personal_index.content_api_docs import (
    APIDocumentation, EndpointDoc, ParameterDoc, ResponseDoc,
    DocSection, DocumentationBuilder,
    generate_openapi_spec, generate_markdown_docs,
    generate_swagger_ui_html,
)


class TestDocsComplete:
    def test_all_exports(self):
        assert APIDocumentation is not None
        assert EndpointDoc is not None
        assert ParameterDoc is not None
        assert ResponseDoc is not None
        assert DocSection is not None
        assert DocumentationBuilder is not None

    def test_all_generators(self):
        spec = generate_openapi_spec()
        assert "openapi" in spec

        md = generate_markdown_docs()
        assert "# API Documentation" in md

        html = generate_swagger_ui_html()
        assert "<!DOCTYPE html>" in html

    def test_full_workflow(self):
        docs = APIDocumentation()
        docs.add_endpoint(
            EndpointDoc(
                path="/items", method="GET", summary="List items",
                parameters=[ParameterDoc(name="page", param_type="integer", required=False)],
                responses=[ResponseDoc(status_code=200, description="OK")],
            )
        )
        generated = docs.generate()
        assert len(generated["endpoints"]) == 1
        spec = generate_openapi_spec(docs.endpoints)
        assert "/items" in spec["paths"]
