"""Tests for content_api_rate_limit module - API rate limiting."""

from __future__ import annotations

import time
import pytest
from personal_index.content_api_rate_limit import (
    RateLimiter,
    RateLimitConfig,
    RateLimitMiddleware,
    RateLimitWindow,
    RateLimitResult,
    RateLimitStore,
    create_rate_limiter,
    create_rate_limit_middleware,
    check_rate_limit,
    SlidingWindowLimiter,
    FixedWindowLimiter,
    TokenBucketLimiter,
)


class TestRateLimitConfig:
    def test_config_defaults(self):
        config = RateLimitConfig()
        assert config.max_requests == 100
        assert config.window_seconds == 60

    def test_config_custom(self):
        config = RateLimitConfig(max_requests=50, window_seconds=30)
        assert config.max_requests == 50
        assert config.window_seconds == 30

    def test_config_per_endpoint(self):
        config = RateLimitConfig(
            max_requests=100,
            window_seconds=60,
            per_endpoint_limits={"search": 20},
        )
        assert config.per_endpoint_limits["search"] == 20

    def test_config_to_dict(self):
        config = RateLimitConfig()
        d = config.to_dict()
        assert d["max_requests"] == 100


class TestRateLimitWindow:
    def test_window_init(self):
        w = RateLimitWindow(max_requests=10, window_seconds=60)
        assert w.max_requests == 10
        assert w.window_seconds == 60

    def test_window_record_request(self):
        w = RateLimitWindow(max_requests=10, window_seconds=60)
        w.record_request()
        assert w.request_count == 1

    def test_window_reset(self):
        w = RateLimitWindow(max_requests=10, window_seconds=60)
        w.record_request()
        w.record_request()
        w.reset()
        assert w.request_count == 0

    def test_window_is_expired(self):
        w = RateLimitWindow(max_requests=10, window_seconds=0.01)
        time.sleep(0.02)
        assert w.is_expired() is True

    def test_window_not_expired(self):
        w = RateLimitWindow(max_requests=10, window_seconds=60)
        assert w.is_expired() is False


class TestRateLimitResult:
    def test_result_allowed(self):
        r = RateLimitResult(allowed=True, remaining=9, limit=10)
        assert r.allowed is True
        assert r.remaining == 9
        assert r.limit == 10

    def test_result_denied(self):
        r = RateLimitResult(allowed=False, remaining=0, limit=10, retry_after=30)
        assert r.allowed is False
        assert r.remaining == 0
        assert r.retry_after == 30

    def test_result_to_dict(self):
        r = RateLimitResult(allowed=True, remaining=5, limit=10)
        d = r.to_dict()
        assert d["allowed"] is True
        assert d["remaining"] == 5

    def test_result_headers(self):
        r = RateLimitResult(allowed=True, remaining=5, limit=10, reset=60)
        headers = r.to_headers()
        assert "X-RateLimit-Limit" in headers
        assert "X-RateLimit-Remaining" in headers


class TestRateLimitStore:
    def test_store_init(self):
        store = RateLimitStore()
        assert store is not None

    def test_store_get_or_create(self):
        store = RateLimitStore()
        window = store.get_or_create("key1", 10, 60)
        assert window.max_requests == 10

    def test_store_returns_existing(self):
        store = RateLimitStore()
        w1 = store.get_or_create("key1", 10, 60)
        w2 = store.get_or_create("key1", 20, 30)
        assert w1 is w2

    def test_store_cleanup_expired(self):
        store = RateLimitStore()
        store.get_or_create("key1", 10, 0.01)
        time.sleep(0.02)
        store.cleanup_expired()
        assert "key1" not in store._windows

    def test_store_size(self):
        store = RateLimitStore()
        store.get_or_create("key1", 10, 60)
        store.get_or_create("key2", 10, 60)
        assert store.size() == 2


class TestRateLimiter:
    def test_limiter_init(self):
        limiter = RateLimiter()
        assert limiter is not None

    def test_limiter_check_allowed(self):
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        result = limiter.check("user1")
        assert result.allowed is True

    def test_limiter_check_denied(self):
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        limiter.check("user1")
        limiter.check("user1")
        result = limiter.check("user1")
        assert result.allowed is False

    def test_limiter_different_keys(self):
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        r1 = limiter.check("user1")
        r2 = limiter.check("user2")
        assert r1.allowed is True
        assert r2.allowed is True

    def test_limiter_window_reset(self):
        limiter = RateLimiter(max_requests=1, window_seconds=0.01)
        limiter.check("user1")
        time.sleep(0.02)
        result = limiter.check("user1")
        assert result.allowed is True

    def test_limiter_get_remaining(self):
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        limiter.check("user1")
        remaining = limiter.get_remaining("user1")
        assert remaining == 4

    def test_limiter_reset(self):
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        limiter.check("user1")
        limiter.reset("user1")
        result = limiter.check("user1")
        assert result.allowed is True


class TestSlidingWindowLimiter:
    def test_init(self):
        limiter = SlidingWindowLimiter(max_requests=10, window_seconds=60)
        assert limiter is not None

    def test_check_allowed(self):
        limiter = SlidingWindowLimiter(max_requests=5, window_seconds=60)
        result = limiter.check("user1")
        assert result.allowed is True

    def test_check_denied(self):
        limiter = SlidingWindowLimiter(max_requests=2, window_seconds=60)
        limiter.check("user1")
        limiter.check("user1")
        result = limiter.check("user1")
        assert result.allowed is False

    def test_sliding_window(self):
        limiter = SlidingWindowLimiter(max_requests=2, window_seconds=0.1)
        limiter.check("user1")
        time.sleep(0.06)
        limiter.check("user1")
        time.sleep(0.06)
        result = limiter.check("user1")
        assert result.allowed is True


class TestFixedWindowLimiter:
    def test_init(self):
        limiter = FixedWindowLimiter(max_requests=10, window_seconds=60)
        assert limiter is not None

    def test_check_allowed(self):
        limiter = FixedWindowLimiter(max_requests=5, window_seconds=60)
        result = limiter.check("user1")
        assert result.allowed is True

    def test_check_denied(self):
        limiter = FixedWindowLimiter(max_requests=1, window_seconds=60)
        limiter.check("user1")
        result = limiter.check("user1")
        assert result.allowed is False


class TestTokenBucketLimiter:
    def test_init(self):
        limiter = TokenBucketLimiter(rate=10, capacity=10)
        assert limiter is not None

    def test_check_allowed(self):
        limiter = TokenBucketLimiter(rate=5, capacity=5)
        result = limiter.check("user1")
        assert result.allowed is True

    def test_check_denied(self):
        limiter = TokenBucketLimiter(rate=1, capacity=1)
        limiter.check("user1")
        result = limiter.check("user1")
        assert result.allowed is False

    def test_token_refill(self):
        limiter = TokenBucketLimiter(rate=100, capacity=1)
        limiter.check("user1")
        time.sleep(0.02)
        result = limiter.check("user1")
        assert result.allowed is True


class TestRateLimitMiddleware:
    def test_middleware_init(self):
        mw = RateLimitMiddleware()
        assert mw is not None

    def test_middleware_process_allowed(self):
        mw = RateLimitMiddleware(max_requests=10, window_seconds=60)
        result = mw.process_request({"client_ip": "127.0.0.1"})
        assert result["allowed"] is True

    def test_middleware_process_denied(self):
        mw = RateLimitMiddleware(max_requests=1, window_seconds=60)
        mw.process_request({"client_ip": "127.0.0.1"})
        result = mw.process_request({"client_ip": "127.0.0.1"})
        assert result["allowed"] is False

    def test_middleware_different_ips(self):
        mw = RateLimitMiddleware(max_requests=1, window_seconds=60)
        r1 = mw.process_request({"client_ip": "10.0.0.1"})
        r2 = mw.process_request({"client_ip": "10.0.0.2"})
        assert r1["allowed"] is True
        assert r2["allowed"] is True

    def test_middleware_headers(self):
        mw = RateLimitMiddleware(max_requests=10, window_seconds=60)
        result = mw.process_request({"client_ip": "127.0.0.1"})
        assert "headers" in result


class TestCreateRateLimiter:
    def test_create_returns_limiter(self):
        limiter = create_rate_limiter()
        assert limiter is not None


class TestCreateRateLimitMiddleware:
    def test_create_returns_middleware(self):
        mw = create_rate_limit_middleware()
        assert mw is not None


class TestCheckRateLimit:
    def test_check_allowed(self):
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        result = check_rate_limit(limiter, "user1")
        assert result.allowed is True

    def test_check_denied(self):
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        limiter.check("user1")
        result = check_rate_limit(limiter, "user1")
        assert result.allowed is False
