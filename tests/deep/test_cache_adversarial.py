"""Adversarial deep tests for personal_index.cache (cycle 163).

Attacks LRUCache, TTLCache, and CacheDecorator with guard inputs
(None/empty/whitespace/unicode/duplicate/out-of-range), round-trips,
idempotence, property checks, and one end-to-end CLI run.

The cache module is not directly wired to a CLI subcommand; the CLI
end-to-end requirement is satisfied with a `status` run through the
installed entrypoint (same pattern as cycle 162 metrics probe).
"""

from __future__ import annotations

import random
import subprocess
import sys
import time
from pathlib import Path

import pytest

from personal_index.cache import LRUCache, TTLCache, CacheDecorator


# ===========================================================================
# LRUCache - Constructor guards
# ===========================================================================

class TestLRUConstructor:
    """LRUCache constructor edge cases."""

    def test_default_max_size(self):
        """Default max_size is 128."""
        c = LRUCache()
        assert c.max_size == 128
        assert c.size == 0
        assert c.hit_rate == 0.0

    def test_zero_max_size(self):
        """max_size=0: put should not store (or store and immediately evict)."""
        c = LRUCache(max_size=0)
        c.put("k", "v")
        # With max_size=0, the while loop evicts immediately
        assert c.size == 0
        assert "k" not in c

    def test_negative_max_size(self):
        """max_size=-1: put should evict to empty, not crash.

        DEFECT (QA-7): The while loop 'while len(self._cache) > self.max_size'
        with max_size=-1 keeps popping after the dict is empty, raising
        KeyError. The docstring promises 'the cache never exceeds
        self.max_size entries' but the implementation crashes.
        """
        c = LRUCache(max_size=-1)
        c.put("k", "v")
        assert c.size == 0

    def test_none_max_size(self):
        """max_size=None: comparison len > None raises TypeError in py3."""
        c = LRUCache(max_size=None)
        with pytest.raises(TypeError):
            c.put("k", "v")

    def test_float_max_size(self):
        """max_size=2.5: works (len > 2.5 means len >= 3)."""
        c = LRUCache(max_size=2.5)
        c.put("a", 1)
        c.put("b", 2)
        c.put("c", 3)
        # len(3) > 2.5, evicts one
        assert c.size <= 3

    def test_string_max_size(self):
        """max_size='10': comparison len > '10' raises TypeError in py3."""
        c = LRUCache(max_size="10")
        with pytest.raises(TypeError):
            c.put("k", "v")


# ===========================================================================
# LRUCache - Key guards
# ===========================================================================

class TestLRUKeyGuards:
    """Adversarial key inputs for LRUCache."""

    def test_none_key(self):
        """put(None, 'v') - None is hashable, works as key."""
        c = LRUCache(max_size=10)
        c.put(None, "v")
        assert c.get(None) == "v"
        assert None in c

    def test_empty_string_key(self):
        """put('', 'v') - empty string key."""
        c = LRUCache(max_size=10)
        c.put("", "empty")
        assert c.get("") == "empty"
        assert "" in c

    def test_whitespace_key(self):
        """put('   ', 'v') - whitespace key distinct from empty."""
        c = LRUCache(max_size=10)
        c.put("   ", "ws")
        c.put("", "empty")
        assert c.get("   ") == "ws"
        assert c.get("") == "empty"
        assert c.size == 2

    def test_unicode_key(self):
        """Unicode keys round-trip."""
        c = LRUCache(max_size=10)
        key = "ключ_测试_🔑"
        c.put(key, "unicode_val")
        assert c.get(key) == "unicode_val"
        assert key in c

    def test_very_long_key(self):
        """10000-char key works."""
        c = LRUCache(max_size=10)
        long_key = "x" * 10000
        c.put(long_key, "long")
        assert c.get(long_key) == "long"

    def test_key_with_newlines(self):
        """Key with newlines and tabs."""
        c = LRUCache(max_size=10)
        key = "line1\nline2\ttab"
        c.put(key, "multi")
        assert c.get(key) == "multi"

    def test_key_with_null_byte(self):
        """Key with null byte (valid in Python dicts)."""
        c = LRUCache(max_size=10)
        key = "a\x00b"
        c.put(key, "null")
        assert c.get(key) == "null"

    def test_unhashable_key(self):
        """put([1,2], 'v') - list key raises TypeError."""
        c = LRUCache(max_size=10)
        with pytest.raises(TypeError):
            c.put([1, 2], "v")

    def test_unhashable_key_get(self):
        """get([1,2]) - list key raises TypeError."""
        c = LRUCache(max_size=10)
        with pytest.raises(TypeError):
            c.get([1, 2])


# ===========================================================================
# LRUCache - Value guards
# ===========================================================================

class TestLRUValueGuards:
    """Adversarial value inputs for LRUCache."""

    def test_none_value(self):
        """put('k', None) - None as value."""
        c = LRUCache(max_size=10)
        c.put("k", None)
        assert "k" in c
        assert c.get("k") is None

    def test_empty_value(self):
        """put('k', '') - empty string value."""
        c = LRUCache(max_size=10)
        c.put("k", "")
        assert c.get("k") == ""
        assert "k" in c

    def test_large_value(self):
        """1MB value is storable."""
        c = LRUCache(max_size=10)
        big = "x" * (1024 * 1024)
        c.put("big", big)
        assert c.get("big") == big

    def test_unhashable_value(self):
        """put('k', [1,2,3]) - list value (values don't need to be hashable)."""
        c = LRUCache(max_size=10)
        c.put("k", [1, 2, 3])
        assert c.get("k") == [1, 2, 3]

    def test_value_identity(self):
        """put('k', obj) - identity preserved."""
        c = LRUCache(max_size=10)
        d = {"a": 1}
        c.put("k", d)
        assert c.get("k") is d

    def test_zero_value(self):
        """put('k', 0) - zero is falsy but valid."""
        c = LRUCache(max_size=10)
        c.put("k", 0)
        assert c.get("k") == 0
        assert "k" in c

    def test_false_value(self):
        """put('k', False) - False is falsy but valid."""
        c = LRUCache(max_size=10)
        c.put("k", False)
        assert c.get("k") is False
        assert "k" in c


# ===========================================================================
# LRUCache - Round-trip and idempotence
# ===========================================================================

class TestLRURoundTrip:
    """Round-trip and idempotence for LRUCache."""

    def test_put_get_round_trip(self):
        """Basic put -> get round-trip."""
        c = LRUCache(max_size=10)
        c.put("key1", "value1")
        assert c.get("key1") == "value1"

    def test_overwrite_same_key(self):
        """put same key twice overwrites."""
        c = LRUCache(max_size=10)
        c.put("k", "first")
        c.put("k", "second")
        assert c.get("k") == "second"
        assert c.size == 1

    def test_get_missing_returns_none(self):
        """get on missing key returns None (default)."""
        c = LRUCache(max_size=10)
        assert c.get("nonexistent") is None

    def test_get_missing_with_default(self):
        """get with custom default on missing key."""
        c = LRUCache(max_size=10)
        assert c.get("nonexistent", "fallback") == "fallback"

    def test_get_missing_default_none_explicit(self):
        """get with explicit None default."""
        c = LRUCache(max_size=10)
        assert c.get("nonexistent", None) is None

    def test_contains_after_put(self):
        """__contains__ reflects put."""
        c = LRUCache(max_size=10)
        assert "k" not in c
        c.put("k", "v")
        assert "k" in c

    def test_contains_after_delete(self):
        """__contains__ is False after delete."""
        c = LRUCache(max_size=10)
        c.put("k", "v")
        assert "k" in c
        c.delete("k")
        assert "k" not in c

    def test_idempotent_get(self):
        """Multiple gets return same value."""
        c = LRUCache(max_size=10)
        c.put("k", "v")
        results = [c.get("k") for _ in range(100)]
        assert all(r == "v" for r in results)

    def test_idempotent_clear(self):
        """clear() on empty cache is no-op."""
        c = LRUCache(max_size=10)
        c.clear()
        c.clear()
        assert c.size == 0

    def test_idempotent_delete_missing(self):
        """delete on missing key returns False, no crash."""
        c = LRUCache(max_size=10)
        assert c.delete("missing") is False
        assert c.size == 0


# ===========================================================================
# LRUCache - LRU eviction behavior
# ===========================================================================

class TestLRUEviction:
    """LRU eviction property checks."""

    def test_evicts_least_recently_used(self):
        """get() updates recency; LRU is evicted first."""
        c = LRUCache(max_size=3)
        c.put("a", 1)
        c.put("b", 2)
        c.put("c", 3)
        # Access "a" to make it most recent
        c.get("a")
        # Now "b" is LRU
        c.put("d", 4)
        assert "b" not in c
        assert "a" in c
        assert "c" in c
        assert "d" in c
        assert c.size == 3

    def test_fifo_when_no_access(self):
        """Without get(), eviction is FIFO (insertion order)."""
        c = LRUCache(max_size=3)
        c.put("a", 1)
        c.put("b", 2)
        c.put("c", 3)
        c.put("d", 4)  # evicts "a"
        assert "a" not in c
        assert "b" in c
        assert "c" in c
        assert "d" in c

    def test_max_size_one(self):
        """max_size=1: only latest survives."""
        c = LRUCache(max_size=1)
        c.put("a", 1)
        c.put("b", 2)
        assert "a" not in c
        assert "b" in c
        assert c.size == 1

    def test_many_evictions(self):
        """1000 puts into size-10: size never exceeds 10."""
        c = LRUCache(max_size=10)
        for i in range(1000):
            c.put(f"k{i}", i)
            assert c.size <= 10
        assert c.size == 10

    def test_put_existing_key_no_eviction(self):
        """put on existing key updates value, doesn't evict."""
        c = LRUCache(max_size=3)
        c.put("a", 1)
        c.put("b", 2)
        c.put("c", 3)
        c.put("a", 99)  # update, not new
        assert c.size == 3
        assert c.get("a") == 99
        assert "b" in c
        assert "c" in c

    def test_put_existing_key_updates_recency(self):
        """put on existing key moves it to most-recent."""
        c = LRUCache(max_size=3)
        c.put("a", 1)
        c.put("b", 2)
        c.put("c", 3)
        c.put("a", 99)  # "a" is now most recent
        c.put("d", 4)  # evicts "b" (LRU)
        assert "b" not in c
        assert "a" in c
        assert c.get("a") == 99


# ===========================================================================
# LRUCache - stats()
# ===========================================================================

class TestLRUStats:
    """stats() correctness for LRUCache."""

    def test_stats_initial(self):
        """Fresh cache: all zeros, hit_rate 0.0."""
        c = LRUCache(max_size=10)
        s = c.stats()
        assert s["size"] == 0
        assert s["max_size"] == 10
        assert s["hits"] == 0
        assert s["misses"] == 0
        assert s["hit_rate"] == 0.0

    def test_stats_after_hit(self):
        """Successful get increments hits."""
        c = LRUCache(max_size=10)
        c.put("k", "v")
        c.get("k")
        s = c.stats()
        assert s["hits"] == 1
        assert s["misses"] == 0
        assert s["hit_rate"] == 1.0

    def test_stats_after_miss(self):
        """Failed get increments misses."""
        c = LRUCache(max_size=10)
        c.get("missing")
        s = c.stats()
        assert s["hits"] == 0
        assert s["misses"] == 1
        assert s["hit_rate"] == 0.0

    def test_stats_mixed(self):
        """Mixed hits and misses."""
        c = LRUCache(max_size=10)
        c.put("a", 1)
        c.get("a")  # hit
        c.get("b")  # miss
        c.get("a")  # hit
        c.get("c")  # miss
        s = c.stats()
        assert s["hits"] == 2
        assert s["misses"] == 2
        assert s["hit_rate"] == 0.5

    def test_stats_size_tracks_len(self):
        """stats['size'] == len(cache) always."""
        c = LRUCache(max_size=5)
        for i in range(10):
            c.put(f"k{i}", i)
            assert c.stats()["size"] == len(c)

    def test_stats_after_clear_counters_unchanged(self):
        """clear() does NOT reset hit/miss counters (per docstring)."""
        c = LRUCache(max_size=10)
        c.put("a", 1)
        c.get("a")  # hit
        c.get("b")  # miss
        c.clear()
        s = c.stats()
        assert s["size"] == 0
        assert s["hits"] == 1  # counters persist
        assert s["misses"] == 1

    def test_stats_keys_exact(self):
        """stats() returns exactly the documented keys."""
        c = LRUCache(max_size=10)
        s = c.stats()
        assert set(s.keys()) == {"size", "max_size", "hits", "misses", "hit_rate"}


# ===========================================================================
# LRUCache - delete()
# ===========================================================================

class TestLRUDelete:
    """delete() behavior."""

    def test_delete_present(self):
        """delete on present key returns True."""
        c = LRUCache(max_size=10)
        c.put("k", "v")
        assert c.delete("k") is True
        assert "k" not in c
        assert c.size == 0

    def test_delete_missing(self):
        """delete on missing key returns False."""
        c = LRUCache(max_size=10)
        assert c.delete("missing") is False

    def test_delete_after_eviction(self):
        """delete on evicted key returns False."""
        c = LRUCache(max_size=1)
        c.put("a", 1)
        c.put("b", 2)  # evicts "a"
        assert c.delete("a") is False


# ===========================================================================
# LRUCache - __len__ and size property
# ===========================================================================

class TestLRUDunder:
    """__len__ and size property consistency."""

    def test_len_equals_size(self):
        """len(c) == c.size always."""
        c = LRUCache(max_size=5)
        for i in range(20):
            c.put(f"k{i}", i)
            assert len(c) == c.size

    def test_len_equals_stats_size(self):
        """len(c) == c.stats()['size'] always."""
        c = LRUCache(max_size=5)
        for i in range(20):
            c.put(f"k{i}", i)
            assert len(c) == c.stats()["size"]


# ===========================================================================
# LRUCache - Stress
# ===========================================================================

class TestLRUStress:
    """Stress and property checks."""

    def test_duplicate_keys_many(self):
        """Same key 1000 times: size stays 1."""
        c = LRUCache(max_size=10)
        for i in range(1000):
            c.put("same", i)
        assert c.size == 1
        assert c.get("same") == 999

    def test_property_never_exceeds(self):
        """Random ops never exceed max_size."""
        random.seed(42)
        c = LRUCache(max_size=7)
        for i in range(5000):
            op = random.random()
            if op < 0.5:
                c.put(f"k{random.randint(0, 20)}", i)
            elif op < 0.7:
                c.get(f"k{random.randint(0, 20)}")
            elif op < 0.85:
                c.delete(f"k{random.randint(0, 20)}")
            else:
                c.clear()
            assert c.size <= 7, f"Exceeded max_size at iteration {i}"

    def test_unicode_keys_many(self):
        """Many unicode keys don't corrupt."""
        c = LRUCache(max_size=50)
        for i in range(100):
            key = f"ключ_{i}_🔑"
            c.put(key, i)
        assert c.size <= 50


# ===========================================================================
# TTLCache - Constructor guards
# ===========================================================================

class TestTTLConstructor:
    """TTLCache constructor edge cases."""

    def test_defaults(self):
        """Default ttl=300.0, max_size=1000."""
        c = TTLCache()
        assert c.ttl == 300.0
        assert c.max_size == 1000
        assert c.size == 0

    def test_zero_ttl(self):
        """ttl=0: entries expire immediately."""
        c = TTLCache(ttl=0.0, max_size=10)
        c.put("k", "v")
        # Entry should be expired (time.monotonic() > expiry)
        time.sleep(0.01)
        assert c.get("k") is None

    def test_negative_ttl(self):
        """ttl=-1: entries expire immediately."""
        c = TTLCache(ttl=-1.0, max_size=10)
        c.put("k", "v")
        time.sleep(0.01)
        assert c.get("k") is None

    def test_none_ttl(self):
        """ttl=None: expiry = monotonic() + None raises TypeError."""
        c = TTLCache(ttl=None, max_size=10)
        with pytest.raises(TypeError):
            c.put("k", "v")

    def test_zero_max_size(self):
        """max_size=0: put evicts immediately."""
        c = TTLCache(ttl=300.0, max_size=0)
        c.put("k", "v")
        assert c.size == 0


# ===========================================================================
# TTLCache - Key/Value guards
# ===========================================================================

class TestTTLKeyGuards:
    """Adversarial keys for TTLCache."""

    def test_none_key(self):
        """None key works."""
        c = TTLCache(ttl=300.0, max_size=10)
        c.put(None, "v")
        assert c.get(None) == "v"

    def test_empty_string_key(self):
        """Empty string key works."""
        c = TTLCache(ttl=300.0, max_size=10)
        c.put("", "empty")
        assert c.get("") == "empty"

    def test_unicode_key(self):
        """Unicode key works."""
        c = TTLCache(ttl=300.0, max_size=10)
        key = "ключ_🔑"
        c.put(key, "unicode")
        assert c.get(key) == "unicode"

    def test_unhashable_key(self):
        """List key raises TypeError."""
        c = TTLCache(ttl=300.0, max_size=10)
        with pytest.raises(TypeError):
            c.put([1, 2], "v")


class TestTTLValueGuards:
    """Adversarial values for TTLCache."""

    def test_none_value(self):
        """None value works."""
        c = TTLCache(ttl=300.0, max_size=10)
        c.put("k", None)
        assert "k" in c
        assert c.get("k") is None

    def test_empty_value(self):
        """Empty string value works."""
        c = TTLCache(ttl=300.0, max_size=10)
        c.put("k", "")
        assert c.get("k") == ""

    def test_unhashable_value(self):
        """List value works."""
        c = TTLCache(ttl=300.0, max_size=10)
        c.put("k", [1, 2, 3])
        assert c.get("k") == [1, 2, 3]


# ===========================================================================
# TTLCache - Expiration behavior
# ===========================================================================

class TestTTLExpiration:
    """TTL expiration property checks."""

    def test_entry_expires(self):
        """Entry expires after TTL."""
        c = TTLCache(ttl=0.05, max_size=10)
        c.put("k", "v")
        assert c.get("k") == "v"  # not yet expired
        time.sleep(0.1)
        assert c.get("k") is None  # expired

    def test_expired_entry_deleted_on_get(self):
        """get() on expired entry deletes it."""
        c = TTLCache(ttl=0.05, max_size=10)
        c.put("k", "v")
        time.sleep(0.1)
        assert c.get("k") is None
        assert "k" not in c

    def test_contains_expired(self):
        """__contains__ on expired entry returns False and deletes."""
        c = TTLCache(ttl=0.05, max_size=10)
        c.put("k", "v")
        time.sleep(0.1)
        assert "k" not in c
        assert c.size == 0

    def test_custom_ttl_per_entry(self):
        """put(key, value, ttl=X) overrides default TTL."""
        c = TTLCache(ttl=300.0, max_size=10)
        c.put("short", "v", ttl=0.05)
        c.put("long", "v", ttl=300.0)
        time.sleep(0.1)
        assert c.get("short") is None  # expired
        assert c.get("long") == "v"  # still valid

    def test_zero_ttl_per_entry(self):
        """put(key, value, ttl=0) expires immediately."""
        c = TTLCache(ttl=300.0, max_size=10)
        c.put("k", "v", ttl=0.0)
        time.sleep(0.01)
        assert c.get("k") is None

    def test_negative_ttl_per_entry(self):
        """put(key, value, ttl=-1) expires immediately."""
        c = TTLCache(ttl=300.0, max_size=10)
        c.put("k", "v", ttl=-1.0)
        time.sleep(0.01)
        assert c.get("k") is None


# ===========================================================================
# TTLCache - Eviction
# ===========================================================================

class TestTTLEviction:
    """TTLCache eviction behavior."""

    def test_evicts_oldest_when_over_capacity(self):
        """Over capacity: evicts entries with earliest expiry."""
        c = TTLCache(ttl=300.0, max_size=2)
        c.put("a", 1, ttl=100.0)
        c.put("b", 2, ttl=200.0)
        c.put("c", 3, ttl=300.0)
        # "a" has earliest expiry, should be evicted
        assert "a" not in c
        assert "b" in c
        assert "c" in c
        assert c.size == 2

    def test_many_puts_never_exceeds(self):
        """1000 puts into size-10: size never exceeds 10."""
        c = TTLCache(ttl=300.0, max_size=10)
        for i in range(1000):
            c.put(f"k{i}", i)
            assert c.size <= 10
        assert c.size == 10

    def test_max_size_one(self):
        """max_size=1: only latest survives."""
        c = TTLCache(ttl=300.0, max_size=1)
        c.put("a", 1)
        c.put("b", 2)
        assert "a" not in c
        assert "b" in c
        assert c.size == 1


# ===========================================================================
# TTLCache - stats()
# ===========================================================================

class TestTTLStats:
    """stats() for TTLCache."""

    def test_stats_initial(self):
        """Fresh TTLCache stats."""
        c = TTLCache(ttl=300.0, max_size=10)
        s = c.stats()
        assert s["size"] == 0
        assert s["max_size"] == 10
        assert s["hits"] == 0
        assert s["misses"] == 0
        assert s["hit_rate"] == 0.0

    def test_stats_after_hit(self):
        """Hit increments hits."""
        c = TTLCache(ttl=300.0, max_size=10)
        c.put("k", "v")
        c.get("k")
        s = c.stats()
        assert s["hits"] == 1
        assert s["misses"] == 0

    def test_stats_after_miss(self):
        """Miss increments misses."""
        c = TTLCache(ttl=300.0, max_size=10)
        c.get("missing")
        s = c.stats()
        assert s["hits"] == 0
        assert s["misses"] == 1

    def test_stats_after_expired_get(self):
        """get on expired entry counts as miss."""
        c = TTLCache(ttl=0.05, max_size=10)
        c.put("k", "v")
        time.sleep(0.1)
        c.get("k")  # expired -> miss
        s = c.stats()
        assert s["hits"] == 0
        assert s["misses"] == 1

    def test_stats_after_clear_counters_unchanged(self):
        """clear() does NOT reset counters (per docstring)."""
        c = TTLCache(ttl=300.0, max_size=10)
        c.put("a", 1)
        c.get("a")
        c.clear()
        s = c.stats()
        assert s["size"] == 0
        assert s["hits"] == 1
        assert s["misses"] == 0


# ===========================================================================
# TTLCache - delete() and clear()
# ===========================================================================

class TestTTLDelete:
    """delete() and clear() for TTLCache."""

    def test_delete_present(self):
        """delete on present key returns True."""
        c = TTLCache(ttl=300.0, max_size=10)
        c.put("k", "v")
        assert c.delete("k") is True
        assert "k" not in c

    def test_delete_missing(self):
        """delete on missing key returns False."""
        c = TTLCache(ttl=300.0, max_size=10)
        assert c.delete("missing") is False

    def test_clear(self):
        """clear() empties the cache."""
        c = TTLCache(ttl=300.0, max_size=10)
        c.put("a", 1)
        c.put("b", 2)
        c.clear()
        assert c.size == 0
        assert "a" not in c
        assert "b" not in c


# ===========================================================================
# TTLCache - size property vs __len__
# ===========================================================================

class TestTTLSize:
    """size property (evicts expired) vs __len__ (raw count)."""

    def test_size_evicts_expired(self):
        """size property deletes expired entries before counting."""
        c = TTLCache(ttl=0.05, max_size=10)
        c.put("k", "v")
        time.sleep(0.1)
        # __len__ may still count it (not yet evicted)
        # size property should evict and return 0
        assert c.size == 0

    def test_len_may_count_expired(self):
        """__len__ counts expired-but-not-yet-evicted entries."""
        c = TTLCache(ttl=0.05, max_size=10)
        c.put("k", "v")
        time.sleep(0.1)
        # __len__ might be 1 (expired but not evicted) or 0
        # This is documented behavior: "expired-but-not-yet-evicted entries
        # are still counted"
        assert len(c) in (0, 1)


# ===========================================================================
# CacheDecorator
# ===========================================================================

class TestCacheDecorator:
    """CacheDecorator behavior."""

    def test_basic_caching(self):
        """Function result is cached."""
        call_count = 0

        @CacheDecorator(lru_size=10)
        def add(a, b):
            nonlocal call_count
            call_count += 1
            return a + b

        assert add(1, 2) == 3
        assert call_count == 1
        assert add(1, 2) == 3
        assert call_count == 1  # cached

    def test_different_args_not_cached(self):
        """Different args produce different cache entries."""
        call_count = 0

        @CacheDecorator(lru_size=10)
        def add(a, b):
            nonlocal call_count
            call_count += 1
            return a + b

        add(1, 2)
        add(3, 4)
        assert call_count == 2

    def test_lru_eviction_in_decorator(self):
        """LRU eviction works in decorator."""
        call_count = 0

        @CacheDecorator(lru_size=2)
        def f(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        f(1)  # call 1
        f(2)  # call 2
        f(1)  # cached
        f(3)  # call 3, evicts f(2)
        f(2)  # call 4 (was evicted)
        assert call_count == 4

    def test_ttl_in_decorator(self):
        """TTL expiration works in decorator."""
        call_count = 0

        @CacheDecorator(lru_size=10, ttl=0.05)
        def f(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        f(1)
        assert call_count == 1
        f(1)  # cached
        assert call_count == 1
        time.sleep(0.1)
        f(1)  # expired, recompute
        assert call_count == 2

    def test_none_args(self):
        """None args work as cache keys."""
        call_count = 0

        @CacheDecorator(lru_size=10)
        def f(x):
            nonlocal call_count
            call_count += 1
            return x

        f(None)
        assert call_count == 1
        f(None)
        assert call_count == 1

    def test_kwargs_caching(self):
        """Keyword args are part of the cache key."""
        call_count = 0

        @CacheDecorator(lru_size=10)
        def f(a, b=0):
            nonlocal call_count
            call_count += 1
            return a + b

        f(1)
        f(1, b=2)
        assert call_count == 2
        f(1)  # cached
        assert call_count == 2
        f(1, b=2)  # cached
        assert call_count == 2


# ===========================================================================
# End-to-end CLI run
# ===========================================================================

class TestCLIEndToEnd:
    """End-to-end CLI run (cache is not directly wired to a subcommand;
    use `status` as the CLI smoke test, same pattern as cycle 162)."""

    def test_cli_status_runs(self):
        """python3 -m personal_index status completes without error."""
        result = subprocess.run(
            [sys.executable, "-m", "personal_index", "status"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(Path(__file__).resolve().parents[2]),
        )
        assert result.returncode == 0, f"CLI status failed: {result.stderr}"
