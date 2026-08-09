"""Tests for rate limit middleware."""

from __future__ import annotations

import pytest
from personal_index.content_api_rate_limit import RateLimitMiddleware


class TestRateLimitMiddleware:
    def test_default_key_extractor(self):
        mw = RateLimitMiddleware(max_requests=10, window_seconds=60)
        result = mw.process_request({"client_ip": "1.2.3.4"})
        assert result["allowed"] is True

    def test_custom_key_extractor(self):
        mw = RateLimitMiddleware(
            max_requests=10, window_seconds=60, key_extractor="api_key"
        )
        result = mw.process_request({"api_key": "key123"})
        assert result["allowed"] is True

    def test_headers_in_response(self):
        mw = RateLimitMiddleware(max_requests=10, window_seconds=60)
        result = mw.process_request({"client_ip": "1.2.3.4"})
        headers = result["headers"]
        assert "X-RateLimit-Limit" in headers
        assert "X-RateLimit-Remaining" in headers

    def test_error_on_exceeded(self):
        mw = RateLimitMiddleware(max_requests=1, window_seconds=60)
        mw.process_request({"client_ip": "1.2.3.4"})
        result = mw.process_request({"client_ip": "1.2.3.4"})
        assert result["allowed"] is False
        assert "error" in result
