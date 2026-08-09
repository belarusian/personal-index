"""Tests for documentation sections."""

from __future__ import annotations

import pytest
from personal_index.content_api_docs import DocSection, DocumentationBuilder, EndpointDoc


class TestDocSection:
    def test_section_with_endpoints(self):
        s = DocSection(title="Content", content="Content endpoints")
        assert s.title == "Content"
        assert len(s.endpoints) == 0

    def test_section_serialization(self):
        s = DocSection(title="Auth", content="Auth endpoints")
        d = s.to_dict()
        assert d["title"] == "Auth"
        assert d["content"] == "Auth endpoints"


class TestDocumentationBuilder:
    def test_fluent_add_endpoint(self):
        builder = DocumentationBuilder()
        result = builder.add_endpoint(
            EndpointDoc(path="/test", method="GET", summary="Test")
        )
        assert result is builder

    def test_fluent_add_section(self):
        builder = DocumentationBuilder()
        result = builder.add_section(
            DocSection(title="Test", content="Test section")
        )
        assert result is builder

    def test_build_empty(self):
        builder = DocumentationBuilder()
        result = builder.build()
        assert result["endpoints"] == []
        assert result["sections"] == []

    def test_build_with_data(self):
        builder = DocumentationBuilder()
        builder.add_endpoint(
            EndpointDoc(path="/items", method="GET", summary="List")
        )
        result = builder.build()
        assert len(result["endpoints"]) == 1
