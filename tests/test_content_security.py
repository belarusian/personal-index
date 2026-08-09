"""Tests for content_security module - Content Security Policy and XSS protection."""

from __future__ import annotations

import pytest
from personal_index.content_security import (
    ContentSecurityPolicy,
    SecurityHeaders,
    XssSanitizer,
)


class TestContentSecurityPolicy:
    """Tests for ContentSecurityPolicy class."""

    def test_default_policy(self):
        policy = ContentSecurityPolicy()
        header = policy.build_header()
        assert "default-src" in header
        assert "'self'" in header

    def test_custom_directives(self):
        policy = ContentSecurityPolicy()
        policy.add_directive("script-src", "'self' https://cdn.example.com")
        header = policy.build_header()
        assert "script-src" in header
        assert "cdn.example.com" in header

    def test_report_only_mode(self):
        policy = ContentSecurityPolicy(report_only=True)
        header = policy.build_header()
        assert "default-src" in header
        assert "'self'" in header

    def test_add_multiple_directives(self):
        policy = ContentSecurityPolicy()
        policy.add_directive("img-src", "'self' data:")
        policy.add_directive("style-src", "'self' 'unsafe-inline'")
        header = policy.build_header()
        assert "img-src" in header
        assert "style-src" in header
        assert "data:" in header


class TestSecurityHeaders:
    """Tests for SecurityHeaders class."""

    def test_default_headers(self):
        headers = SecurityHeaders()
        result = headers.get_headers()
        assert "X-Frame-Options" in result
        assert result["X-Frame-Options"] == "DENY"
        assert "X-Content-Type-Options" in result
        assert result["X-Content-Type-Options"] == "nosniff"

    def test_headers_with_csp(self):
        csp = ContentSecurityPolicy()
        csp.add_directive("script-src", "'self'")
        headers = SecurityHeaders(csp=csp)
        result = headers.get_headers()
        assert "Content-Security-Policy" in result
        assert "script-src" in result["Content-Security-Policy"]

    def test_custom_x_frame_options(self):
        headers = SecurityHeaders(x_frame_options="SAMEORIGIN")
        result = headers.get_headers()
        assert result["X-Frame-Options"] == "SAMEORIGIN"

    def test_permissions_policy(self):
        headers = SecurityHeaders()
        result = headers.get_headers()
        assert "Permissions-Policy" in result
        assert "camera=()" in result["Permissions-Policy"]


class TestXssSanitizer:
    """Tests for XssSanitizer class."""

    def test_strip_tags_basic(self):
        html = "<p>Hello <b>World</b></p>"
        result = XssSanitizer.strip_tags(html)
        assert result == "Hello World"

    def test_strip_tags_nested(self):
        html = "<div><p><span>Nested</span></p></div>"
        result = XssSanitizer.strip_tags(html)
        assert result == "Nested"

    def test_remove_dangerous_tags(self):
        html = "<p>Safe</p><script>alert('xss')</script>"
        result = XssSanitizer.remove_dangerous_tags(html)
        assert "<script>" not in result
        assert "<p>Safe</p>" in result

    def test_sanitize_input_basic(self):
        text = '<script>alert("xss")</script>'
        result = XssSanitizer.sanitize_input(text)
        assert "<" not in result
        assert "&lt;" in result

    def test_sanitize_input_ampersand(self):
        text = "foo & bar"
        result = XssSanitizer.sanitize_input(text)
        assert "&amp;" in result
        assert "& bar" not in result

    def test_sanitize_input_quotes(self):
        text = 'He said "hello"'
        result = XssSanitizer.sanitize_input(text)
        assert "&quot;" in result
