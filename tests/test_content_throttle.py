"""Tests for content_throttle module."""

from __future__ import annotations

import time
import threading
import pytest
from personal_index.content_throttle import (
    ContentThrottle,
    ThrottleConfig,
    ThrottleResult,
)


class TestThrottleConfig:
    def test_default_config(self):
        config = ThrottleConfig()
        assert config.max_concurrent == 5
        assert config.timeout_seconds == 30.0
        assert config.queue_size == 100

    def test_custom_config(self):
        config = ThrottleConfig(max_concurrent=10, timeout_seconds=60.0, queue_size=200)
        assert config.max_concurrent == 10
        assert config.timeout_seconds == 60.0
        assert config.queue_size == 200


class TestThrottleResult:
    def test_acquired_result(self):
        result = ThrottleResult(acquired=True, wait_time=0.0)
        assert result.acquired is True
        assert result.wait_time == 0.0

    def test_waiting_result(self):
        result = ThrottleResult(acquired=False, wait_time=5.0)
        assert result.acquired is False
        assert result.wait_time == 5.0


class TestContentThrottleInit:
    def test_default_init(self):
        throttle = ContentThrottle()
        assert throttle._default_config.max_concurrent == 5

    def test_custom_config_init(self):
        config = ThrottleConfig(max_concurrent=10)
        throttle = ContentThrottle(default_config=config)
        assert throttle._default_config.max_concurrent == 10


class TestContentThrottleAcquire:
    def test_acquire_within_limit(self):
        config = ThrottleConfig(max_concurrent=5)
        throttle = ContentThrottle(default_config=config)
        result = throttle.acquire("extract")
        assert result.acquired is True
        throttle.release("extract")

    def test_acquire_multiple_within_limit(self):
        config = ThrottleConfig(max_concurrent=3)
        throttle = ContentThrottle(default_config=config)
        results = []
        for _ in range(3):
            results.append(throttle.acquire("extract"))
        for r in results:
            assert r.acquired is True
        for _ in range(3):
            throttle.release("extract")

    def test_acquire_exceeds_limit(self):
        config = ThrottleConfig(max_concurrent=2, timeout_seconds=0.1)
        throttle = ContentThrottle(default_config=config)
        throttle.acquire("extract")
        throttle.acquire("extract")
        result = throttle.acquire("extract")
        assert result.acquired is False
        throttle.release("extract")
        throttle.release("extract")

    def test_acquire_independent_operations(self):
        config = ThrottleConfig(max_concurrent=1)
        throttle = ContentThrottle(default_config=config)
        r1 = throttle.acquire("extract")
        r2 = throttle.acquire("index")
        assert r1.acquired is True
        assert r2.acquired is True
        throttle.release("extract")
        throttle.release("index")

    def test_acquire_timeout(self):
        config = ThrottleConfig(max_concurrent=1, timeout_seconds=0.1)
        throttle = ContentThrottle(default_config=config)
        throttle.acquire("extract")
        result = throttle.acquire("extract")
        assert result.acquired is False
        assert result.wait_time > 0
        throttle.release("extract")


class TestContentThrottleRelease:
    def test_release_allows_new_acquire(self):
        config = ThrottleConfig(max_concurrent=1, timeout_seconds=1.0)
        throttle = ContentThrottle(default_config=config)
        throttle.acquire("extract")
        throttle.release("extract")
        result = throttle.acquire("extract")
        assert result.acquired is True
        throttle.release("extract")


class TestContentThrottleActiveCount:
    def test_active_count_increases(self):
        throttle = ContentThrottle()
        throttle.acquire("extract")
        assert throttle.get_active_count("extract") == 1
        throttle.release("extract")
        assert throttle.get_active_count("extract") == 0

    def test_available_slots(self):
        config = ThrottleConfig(max_concurrent=3)
        throttle = ContentThrottle(default_config=config)
        assert throttle.get_available_slots("extract") == 3
        throttle.acquire("extract")
        assert throttle.get_available_slots("extract") == 2
        throttle.release("extract")


class TestContentThrottlePerOpConfig:
    def test_set_config(self):
        throttle = ContentThrottle()
        strict = ThrottleConfig(max_concurrent=1)
        throttle.set_config("strict_op", strict)
        throttle.acquire("strict_op")
        result = throttle.acquire("strict_op")
        assert result.acquired is False
        throttle.release("strict_op")


class TestContentThrottleAcquireOrWait:
    def test_acquire_or_wait_success(self):
        throttle = ContentThrottle()
        assert throttle.acquire_or_wait("extract") is True
        throttle.release("extract")

    def test_acquire_or_wait_timeout(self):
        config = ThrottleConfig(max_concurrent=1, timeout_seconds=0.1)
        throttle = ContentThrottle(default_config=config)
        throttle.acquire("extract")
        result = throttle.acquire_or_wait("extract")
        assert result is False
        throttle.release("extract")


class TestContentThrottleStats:
    def test_stats_specific(self):
        throttle = ContentThrottle()
        throttle.acquire("extract")
        stats = throttle.stats("extract")
        assert stats["operation"] == "extract"
        assert stats["active"] == 1
        throttle.release("extract")

    def test_stats_all(self):
        throttle = ContentThrottle()
        throttle.acquire("extract")
        throttle.acquire("index")
        stats = throttle.stats()
        assert stats["tracked_operations"] == 2
        assert "extract" in stats["operations"]
        throttle.release("extract")
        throttle.release("index")

    def test_stats_unknown(self):
        throttle = ContentThrottle()
        stats = throttle.stats("unknown")
        assert stats["operation"] == "unknown"
        assert stats["active"] == 0


class TestContentThrottleReset:
    def test_reset_operation(self):
        config = ThrottleConfig(max_concurrent=1)
        throttle = ContentThrottle(default_config=config)
        throttle.acquire("extract")
        throttle.reset("extract")
        result = throttle.acquire("extract")
        assert result.acquired is True
        throttle.release("extract")

    def test_reset_all(self):
        config = ThrottleConfig(max_concurrent=1)
        throttle = ContentThrottle(default_config=config)
        throttle.acquire("extract")
        throttle.acquire("index")
        throttle.reset_all()
        assert throttle.acquire("extract").acquired is True
        assert throttle.acquire("index").acquired is True
        throttle.release("extract")
        throttle.release("index")


class TestContentThrottleConcurrency:
    def test_concurrent_access(self):
        config = ThrottleConfig(max_concurrent=2)
        throttle = ContentThrottle(default_config=config)
        results = []
        errors = []

        def worker():
            try:
                r = throttle.acquire("extract", timeout=2.0)
                results.append(r.acquired)
                time.sleep(0.05)
                throttle.release("extract")
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert sum(results) == 2  # Only 2 should succeed
        assert len(results) == 6
