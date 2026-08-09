"""Tests for rate limit store."""

from __future__ import annotations

import time
import pytest
from personal_index.content_api_rate_limit import RateLimitStore


class TestRateLimitStore:
    def test_create_new_window(self):
        store = RateLimitStore()
        window = store.get_or_create("key1", 10, 60)
        assert window.max_requests == 10
        assert window.request_count == 0

    def test_reuse_existing_window(self):
        store = RateLimitStore()
        w1 = store.get_or_create("key1", 10, 60)
        w1.record_request()
        w2 = store.get_or_create("key1", 10, 60)
        assert w2.request_count == 1

    def test_expired_window_reset(self):
        store = RateLimitStore()
        window = store.get_or_create("key1", 10, 0.01)
        window.record_request()
        time.sleep(0.02)
        window2 = store.get_or_create("key1", 10, 0.01)
        assert window2.request_count == 0

    def test_cleanup_removes_expired(self):
        store = RateLimitStore()
        store.get_or_create("key1", 10, 0.01)
        store.get_or_create("key2", 10, 60)
        time.sleep(0.02)
        removed = store.cleanup_expired()
        assert removed == 1
        assert store.size() == 1

    def test_store_empty(self):
        store = RateLimitStore()
        assert store.size() == 0
