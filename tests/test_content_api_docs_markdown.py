"""Tests for Markdown documentation generation."""

from __future__ import annotations

import pytest
from personal_index.content_api_docs import (
    generate_markdown_docs,
    EndpointDoc,
    ParameterDoc,
    ResponseDoc,
)


class TestMarkdownDocs:
    def test_markdown_has_title(self):
        md = generate_markdown_docs()
        assert "# API Documentation" in md

    def test_markdown_has_version(self):
        md = generate_markdown_docs()
        assert "Version 1.0.0" in md

    def test_markdown_has_auth_section(self):
        md = generate_markdown_docs()
        assert "## Authentication" in md

    def test_markdown_with_endpoint(self):
        endpoints = [
            EndpointDoc(path="/items", method="GET", summary="List items"),
        ]
        md = generate_markdown_docs(endpoints=endpoints)
        assert "### GET /items" in md

    def test_markdown_with_parameters(self):
        endpoints = [
            EndpointDoc(
                path="/items", method="GET", summary="List",
                parameters=[ParameterDoc(name="page", param_type="integer", required=False, default=1)],
            ),
        ]
        md = generate_markdown_docs(endpoints=endpoints)
        assert "| page | integer | No | 1 |" in md

    def test_markdown_with_responses(self):
        endpoints = [
            EndpointDoc(
                path="/items", method="GET", summary="List",
                responses=[ResponseDoc(status_code=200, description="OK")],
            ),
        ]
        md = generate_markdown_docs(endpoints=endpoints)
        assert "**200**: OK" in md
