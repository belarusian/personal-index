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
