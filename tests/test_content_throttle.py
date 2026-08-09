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
