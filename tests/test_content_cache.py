"""Tests for content_cache module."""

from __future__ import annotations

import time
import pytest
from personal_index.content_cache import ContentCache


class TestContentCacheInit:
    def test_default_init(self):
        cache = ContentCache()
        assert cache.max_size == 1000
        assert cache.default_ttl == 3600.0
        assert cache.size == 0

    def test_custom_init(self):
        cache = ContentCache(max_size=500, default_ttl=1800.0)
        assert cache.max_size == 500
        assert cache.default_ttl == 1800.0
        assert cache.size == 0
