"""Adversarial deep tests for personal_index.content_cache (CacheStore/CacheStats/CachePolicy).

Cycle 165 PROBE: content_cache subpackage was never probed. Attacks guard inputs
(None/empty/whitespace/unicode/duplicate/out-of-range), TTL expiry, LRU eviction,
round-trips, idempotence, property checks, plus one end-to-end CLI run.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

from personal_index.content_cache import (
    CachePolicy,
    CacheStats,
    CacheStore,
    EvictionPolicy,
)


# ---------------------------------------------------------------------------
# CacheStore: round-trip + guard inputs
# ---------------------------------------------------------------------------
class TestCacheStoreRoundTrip:
    def test_set_get_roundtrip(self) -> None:
        s = CacheStore()
        s.set("k", "v")
        assert s.get("k") == "v"

    def test_get_missing_returns_default(self) -> None:
        s = CacheStore()
        assert s.get("nope") is None
        assert s.get("nope", "dflt") == "dflt"

    def test_empty_key_distinct_from_whitespace(self) -> None:
        s = CacheStore()
        s.set("", "empty")
        s.set("   ", "ws")
        assert s.get("") == "empty"
        assert s.get("   ") == "ws"
        assert s.size() == 2

    def test_unicode_key_roundtrip(self) -> None:
        s = CacheStore()
        s.set("ключ-🚀", "value")
        assert s.get("ключ-🚀") == "value"

    def test_duplicate_key_overwrites(self) -> None:
        s = CacheStore()
        s.set("k", 1)
        s.set("k", 2)
        assert s.get("k") == 2
        assert s.size() == 1

    def test_none_value_stored(self) -> None:
        s = CacheStore()
        s.set("k", None)
        assert s.has("k") is True
        assert s.get("k") is None


# ---------------------------------------------------------------------------
# CacheStore: TTL expiry (deterministic via monkeypatched clock)
# ---------------------------------------------------------------------------
class TestCacheStoreTTL:
    def test_expired_entry_is_miss_and_lazy_deleted(self, monkeypatch) -> None:
        s = CacheStore(default_ttl=None)
        now = [1000.0]
        monkeypatch.setattr(time, "time", lambda: now[0])
        s.set("k", "v", ttl=10.0)
        assert s.get("k") == "v"
        # advance past TTL
        now[0] = 1011.0
        assert s.get("k") is None
        # lazily deleted -> size/has reflect removal
        assert s.has("k") is False
        assert s.size() == 0
        assert "k" not in s.keys()

    def test_none_ttl_never_expires(self, monkeypatch) -> None:
        s = CacheStore(default_ttl=None)
        now = [0.0]
        monkeypatch.setattr(time, "time", lambda: now[0])
        s.set("k", "v", ttl=None)
        now[0] = 1e9
        assert s.get("k") == "v"

    def test_negative_ttl_expires_immediately(self, monkeypatch) -> None:
        s = CacheStore(default_ttl=None)
        now = [1000.0]
        monkeypatch.setattr(time, "time", lambda: now[0])
        s.set("k", "v", ttl=-5.0)
        # created_at + (-5) < now -> expired
        assert s.get("k") is None
        assert s.size() == 0


# ---------------------------------------------------------------------------
# CacheStore: LRU eviction
# ---------------------------------------------------------------------------
class TestCacheStoreEviction:
    def test_evicts_least_recently_used(self) -> None:
        s = CacheStore(max_size=2, default_ttl=None)
        s.set("a", 1)
        s.set("b", 2)
        # touch a so b becomes LRU
        s.get("a")
        s.set("c", 3)  # over max_size -> evict LRU (b)
        assert s.has("a") is True
        assert s.has("b") is False
        assert s.has("c") is True
        assert s.size() == 2

    def test_max_size_one(self) -> None:
        s = CacheStore(max_size=1, default_ttl=None)
        s.set("a", 1)
        s.set("b", 2)
        assert s.size() == 1
        assert s.has("b") is True
        assert s.has("a") is False

    def test_max_size_zero_evicts_everything(self) -> None:
        s = CacheStore(max_size=0, default_ttl=None)
        s.set("a", 1)
        # len(_entries)=1 > max_size=0 -> evict -> empty
        assert s.size() == 0


# ---------------------------------------------------------------------------
# CacheStore: delete / clear / idempotence
# ---------------------------------------------------------------------------
class TestCacheStoreIdempotence:
    def test_delete_present_then_absent(self) -> None:
        s = CacheStore()
        s.set("k", "v")
        assert s.delete("k") is True
        assert s.delete("k") is False

    def test_clear_idempotent(self) -> None:
        s = CacheStore()
        s.set("a", 1)
        s.set("b", 2)
        s.clear()
        s.clear()
        assert s.size() == 0
        assert s.keys() == []

    def test_keys_excludes_expired(self, monkeypatch) -> None:
        s = CacheStore(default_ttl=None)
        now = [0.0]
        monkeypatch.setattr(time, "time", lambda: now[0])
        s.set("live", "x", ttl=100.0)
        s.set("dead", "y", ttl=1.0)
        now[0] = 2.0
        assert s.keys() == ["live"]
        assert s.size() == 1


# ---------------------------------------------------------------------------
# CacheStats: rate properties + guard inputs
# ---------------------------------------------------------------------------
class TestCacheStats:
    def test_zero_total_guard(self) -> None:
        st = CacheStats()
        assert st.hit_rate == 0.0
        assert st.miss_rate == 0.0

    def test_hit_plus_miss_equals_one(self) -> None:
        st = CacheStats(hits=3, misses=1)
        assert st.hit_rate + st.miss_rate == 1.0
        assert st.hit_rate == pytest.approx(0.75)
        assert st.miss_rate == pytest.approx(0.25)

    def test_all_hits(self) -> None:
        st = CacheStats(hits=5, misses=0)
        assert st.hit_rate == 1.0
        assert st.miss_rate == 0.0

    def test_all_misses(self) -> None:
        st = CacheStats(hits=0, misses=7)
        assert st.hit_rate == 0.0
        assert st.miss_rate == 1.0

    def test_reset_zeroes_all(self) -> None:
        st = CacheStats(hits=1, misses=2, sets=3, evictions=4, current_size=5)
        st.reset()
        assert (st.hits, st.misses, st.sets, st.evictions, st.current_size) == (0, 0, 0, 0, 0)
        assert st.hit_rate == 0.0
        assert st.miss_rate == 0.0

    def test_negative_counters_no_crash(self) -> None:
        # out-of-range: negative counters must not raise; rate stays a float
        st = CacheStats(hits=-1, misses=-1)
        assert isinstance(st.hit_rate, float)
        assert isinstance(st.miss_rate, float)


# ---------------------------------------------------------------------------
# CachePolicy: defaults + enum
# ---------------------------------------------------------------------------
class TestCachePolicy:
    def test_defaults(self) -> None:
        p = CachePolicy()
        assert p.eviction_policy is EvictionPolicy.LRU
        assert p.max_size == 1000
        assert p.default_ttl == 3600.0
        assert p.enable_stats is True

    def test_all_policies_present(self) -> None:
        assert {e.value for e in EvictionPolicy} == {"lru", "lfu", "fifo", "ttl"}


# ---------------------------------------------------------------------------
# End-to-end CLI run (installed entry point)
# ---------------------------------------------------------------------------
class TestCliEndToEnd:
    def test_cli_status_runs(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "personal_index", "status"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(Path(__file__).resolve().parents[2]),
        )
        assert result.returncode == 0, f"CLI status failed: {result.stderr}"
