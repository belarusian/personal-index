"""Tests for Swagger UI generation."""

from __future__ import annotations

import pytest
from personal_index.content_api_docs import generate_swagger_ui_html


class TestSwaggerUI:
    def test_generates_html(self):
        html = generate_swagger_ui_html()
        assert "<!DOCTYPE html>" in html

    def test_contains_swagger_ui(self):
        html = generate_swagger_ui_html()
        assert "swagger-ui" in html.lower()

    def test_contains_script(self):
        html = generate_swagger_ui_html()
        assert "SwaggerUIBundle" in html

    def test_custom_spec_url(self):
        html = generate_swagger_ui_html(spec_url="/custom/spec.json")
        assert "/custom/spec.json" in html

    def test_default_spec_url(self):
        html = generate_swagger_ui_html()
        assert "/api/docs/openapi.json" in html
