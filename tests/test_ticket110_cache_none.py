"""Test TICKET-110: Fix CacheDecorator to handle None return values"""

from personal_index.cache import CacheDecorator


def test_cache_decorator_handles_none_return():
    """Verify CacheDecorator correctly caches and retrieves None values."""
    call_count = 0

    @CacheDecorator(lru_size=10)
    def returns_none(x):
        nonlocal call_count
        call_count += 1

    # First call should execute the function
    result1 = returns_none(1)
    assert result1 is None
    assert call_count == 1

    # Second call should hit the cache (not re-execute)
    result2 = returns_none(1)
    assert result2 is None
    assert call_count == 1  # Should still be 1, cached


def test_cache_decorator_handles_non_none_return():
    """Verify CacheDecorator still works with non-None values."""
    call_count = 0

    @CacheDecorator(lru_size=10)
    def returns_value(x):
        nonlocal call_count
        call_count += 1
        return x * 2

    assert returns_value(5) == 10
    assert call_count == 1
    assert returns_value(5) == 10
    assert call_count == 1  # Cached


def test_cache_decorator_different_args():
    """Verify different args produce different cache entries."""
    call_count = 0

    @CacheDecorator(lru_size=10)
    def returns_none(x):
        nonlocal call_count
        call_count += 1

    returns_none(1)
    assert call_count == 1
    returns_none(2)
    assert call_count == 2  # Different arg, not cached
    returns_none(1)
    assert call_count == 2  # Same arg as first call, cached
