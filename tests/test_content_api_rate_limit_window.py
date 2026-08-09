"""Tests for rate limit window."""

from __future__ import annotations

import time
import pytest
from personal_index.content_api_rate_limit import RateLimitWindow


class TestRateLimitWindow:
    def test_new_window_count(self):
        w = RateLimitWindow(max_requests=10, window_seconds=60)
        assert w.request_count == 0

    def test_record_increments(self):
        w = RateLimitWindow(max_requests=10, window_seconds=60)
        w.record_request()
        w.record_request()
        assert w.request_count == 2

    def test_reset_clears(self):
        w = RateLimitWindow(max_requests=10, window_seconds=60)
        w.record_request()
        w.reset()
        assert w.request_count == 0

    def test_not_expired_immediately(self):
        w = RateLimitWindow(max_requests=10, window_seconds=60)
        assert w.is_expired() is False

    def test_expired_after_time(self):
        w = RateLimitWindow(max_requests=10, window_seconds=0.01)
        time.sleep(0.02)
        assert w.is_expired() is True
