"""Tests for content_security module - Content Security Policy and XSS protection."""

from __future__ import annotations

import pytest
from personal_index.content_security import (
    ContentSecurityPolicy,
    InputValidator,
    SecurityAudit,
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


class TestInputValidator:
    """Tests for InputValidator class."""

    def test_valid_email(self):
        assert InputValidator.is_valid_email("user@example.com")

    def test_invalid_email_no_at(self):
        assert not InputValidator.is_valid_email("userexample.com")

    def test_valid_url(self):
        assert InputValidator.is_valid_url("https://example.com/path")

    def test_invalid_url_no_scheme(self):
        assert not InputValidator.is_valid_url("example.com")

    def test_max_length_valid(self):
        assert InputValidator.check_max_length("short", 100)

    def test_max_length_exceeded(self):
        assert not InputValidator.check_max_length("a" * 201, 200)

    def test_allowed_characters(self):
        assert InputValidator.check_allowed_chars("hello123", "abcdefghijklmnopqrstuvwxyz0123456789")

    def test_disallowed_characters(self):
        assert not InputValidator.check_allowed_chars("hello<script>", "abcdefghijklmnopqrstuvwxyz")


class TestSecurityAudit:
    """Tests for SecurityAudit class."""

    def test_audit_scan_all_headers_present(self):
        audit = SecurityAudit()
        headers = {
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "X-XSS-Protection": "1; mode=block",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }
        issues = audit.scan_headers(headers)
        assert len(issues) == 0

    def test_audit_scan_missing_headers(self):
        audit = SecurityAudit()
        headers = {}
        issues = audit.scan_headers(headers)
        assert len(issues) > 0

    def test_audit_scan_weak_csp(self):
        audit = SecurityAudit()
        headers = {"Content-Security-Policy": "default-src *"}
        issues = audit.scan_headers(headers)
        assert any("wildcard" in i.lower() or "*" in i for i in issues)

    def test_audit_report(self):
        audit = SecurityAudit()
        headers = {
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "X-XSS-Protection": "1; mode=block",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }
        report = audit.generate_report(headers)
        assert "issues" in report
        assert "score" in report
        assert report["score"] > 0


class TestSecurityHeadersIntegration:
    """Integration tests for security headers."""

    def test_full_security_stack(self):
        csp = ContentSecurityPolicy()
        csp.add_directive("script-src", "'self'")
        csp.add_directive("style-src", "'self'")
        csp.add_directive("img-src", "'self' data: https:")
        headers = SecurityHeaders(csp=csp)
        result = headers.get_headers()
        assert len(result) >= 5
        assert "Content-Security-Policy" in result
        assert "X-Frame-Options" in result
        assert "X-Content-Type-Options" in result


class TestSecurityMiddleware:
    """Tests for SecurityMiddleware class."""

    def test_default_headers(self):
        from personal_index.content_security import SecurityMiddleware
        middleware = SecurityMiddleware()
        headers = middleware.apply_headers()
        assert "Content-Security-Policy" in headers

    def test_sanitize_request(self):
        from personal_index.content_security import SecurityMiddleware
        middleware = SecurityMiddleware()
        params = {"name": "<script>alert(1)</script>", "email": "test@test.com"}
        result = middleware.sanitize_request(params)
        assert "<script>" not in result["name"]

    def test_blocked_path(self):
        from personal_index.content_security import SecurityMiddleware
        middleware = SecurityMiddleware(blocked_paths=["/admin"])
        assert middleware.is_path_blocked("/admin")
        assert not middleware.is_path_blocked("/public")

    def test_process_request_allowed(self):
        from personal_index.content_security import SecurityMiddleware
        middleware = SecurityMiddleware()
        allowed, headers, params = middleware.process_request("/page", {"q": "test"})
        assert allowed is True
        assert headers

    def test_process_request_blocked(self):
        from personal_index.content_security import SecurityMiddleware
        middleware = SecurityMiddleware(blocked_paths=["/admin"])
        allowed, headers, params = middleware.process_request("/admin", {})
        assert allowed is False


class TestCSPNonceManager:
    """Tests for CSPNonceManager class."""

    def test_generate_nonce(self):
        from personal_index.content_security import CSPNonceManager
        manager = CSPNonceManager()
        nonce = manager.generate_nonce("script-main")
        assert len(nonce) > 0
        assert isinstance(nonce, str)

    def test_nonce_uniqueness(self):
        from personal_index.content_security import CSPNonceManager
        manager = CSPNonceManager()
        n1 = manager.generate_nonce("script-1")
        n2 = manager.generate_nonce("script-2")
        assert n1 != n2

    def test_get_nonce(self):
        from personal_index.content_security import CSPNonceManager
        manager = CSPNonceManager()
        nonce = manager.generate_nonce("script-main")
        assert manager.get_nonce("script-main") == nonce
        assert manager.get_nonce("missing") is None

    def test_build_nonce_directive(self):
        from personal_index.content_security import CSPNonceManager
        manager = CSPNonceManager()
        manager.generate_nonce("script-1")
        manager.generate_nonce("script-2")
        directive = manager.build_nonce_directive()
        assert "script-src" in directive
        assert "'self'" in directive
        assert "nonce-" in directive

    def test_reset(self):
        from personal_index.content_security import CSPNonceManager
        manager = CSPNonceManager()
        manager.generate_nonce("script-1")
        manager.reset()
        assert len(manager.nonces) == 0
