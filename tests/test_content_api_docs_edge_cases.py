"""Edge case tests for docs module."""

from __future__ import annotations

import pytest
from personal_index.content_api_docs import (
    APIDocumentation, EndpointDoc, ParameterDoc,
    generate_openapi_spec, generate_markdown_docs,
)


class TestDocsEdgeCases:
    def test_empty_docs(self):
        docs = APIDocumentation()
        result = docs.generate()
        assert result["endpoints"] == []

    def test_many_endpoints(self):
        docs = APIDocumentation()
        for i in range(100):
            docs.add_endpoint(
                EndpointDoc(path=f"/items/{i}", method="GET", summary=f"Item {i}")
            )
        result = docs.generate()
        assert len(result["endpoints"]) == 100

    def test_openapi_empty(self):
        spec = generate_openapi_spec(endpoints=[])
        assert spec["paths"] == {}

    def test_markdown_empty(self):
        md = generate_markdown_docs(endpoints=[])
        assert "## Endpoints" in md

    def test_endpoint_no_responses(self):
        ep = EndpointDoc(path="/test", method="GET", summary="Test")
        d = ep.to_dict()
        assert "responses" not in d
