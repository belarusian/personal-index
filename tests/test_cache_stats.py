"""Tests for cache statistics tracking."""

from personal_index.content_cache.cache_stats import CacheStats


class TestCacheStats:
    def test_default_values(self):
        s = CacheStats()
        assert s.hits == 0
        assert s.misses == 0
        assert s.sets == 0
        assert s.evictions == 0
        assert s.current_size == 0

    def test_hit_rate_zero_total(self):
        s = CacheStats()
        assert s.hit_rate == 0.0

    def test_hit_rate_perfect(self):
        s = CacheStats(hits=10, misses=0)
        assert s.hit_rate == 1.0

    def test_hit_rate_half(self):
        s = CacheStats(hits=5, misses=5)
        assert s.hit_rate == 0.5

    def test_miss_rate_zero_total(self):
        s = CacheStats()
        assert s.miss_rate == 0.0

    def test_miss_rate_perfect(self):
        s = CacheStats(hits=0, misses=10)
        assert s.miss_rate == 1.0

    def test_miss_rate_half(self):
        s = CacheStats(hits=5, misses=5)
        assert s.miss_rate == 0.5

    def test_hit_rate_plus_miss_rate(self):
        s = CacheStats(hits=3, misses=7)
        assert round(s.hit_rate + s.miss_rate, 10) == 1.0

    def test_reset(self):
        s = CacheStats(hits=10, misses=5, sets=20, evictions=3, current_size=50)
        s.reset()
        assert s.hits == 0
        assert s.misses == 0
        assert s.sets == 0
        assert s.evictions == 0
        assert s.current_size == 0

    def test_custom_values(self):
        s = CacheStats(hits=100, misses=25, sets=200, evictions=10, current_size=180)
        assert s.hit_rate == 0.8
        assert s.miss_rate == 0.2
