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


class TestCacheStatsDocstring541:
    """Pinning test for TICKET-541: docstring contract + non-obvious behaviors."""

    def test_hit_rate_docstring_states_contract(self):
        doc = CacheStats.hit_rate.fget.__doc__
        assert "hits / (hits + misses)" in doc
        assert "ZERO" in doc
        assert "0.0" in doc
        assert "10 decimal places" in doc
        assert "hit_rate + miss_rate == 1.0" in doc

    def test_miss_rate_docstring_states_contract(self):
        doc = CacheStats.miss_rate.fget.__doc__
        assert "misses / (hits + misses)" in doc
        assert "ZERO" in doc
        assert "0.0" in doc
        assert "10 decimal places" in doc
        assert "hit_rate + miss_rate == 1.0" in doc

    def test_reset_docstring_states_contract(self):
        doc = CacheStats.reset.__doc__
        assert "hits" in doc
        assert "misses" in doc
        assert "sets" in doc
        assert "evictions" in doc
        assert "current_size" in doc

    def test_zero_total_guard_no_exception(self):
        s = CacheStats()
        assert s.hit_rate == 0.0
        assert s.miss_rate == 0.0

    def test_rounding_to_10_decimal_places(self):
        # 1/3 is non-terminating; must be rounded to exactly 10 dp.
        s = CacheStats(hits=1, misses=2)
        assert s.hit_rate == 0.3333333333
        assert s.miss_rate == 0.6666666667

    def test_hit_rate_plus_miss_rate_is_one(self):
        s = CacheStats(hits=1, misses=2)
        assert s.hit_rate + s.miss_rate == 1.0
        s2 = CacheStats(hits=2, misses=3)
        assert s2.hit_rate + s2.miss_rate == 1.0

    def test_reset_zeroes_all_five_fields(self):
        s = CacheStats(hits=10, misses=5, sets=20, evictions=3, current_size=50)
        s.reset()
        assert s.hits == 0
        assert s.misses == 0
        assert s.sets == 0
        assert s.evictions == 0
        assert s.current_size == 0
        assert s.hit_rate == 0.0
        assert s.miss_rate == 0.0
