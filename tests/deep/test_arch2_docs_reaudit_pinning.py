"""ARCH-2 VERIFY pinning (cycle 193) — docs re-audit PR#1231@a1a5bc2 (cycle 220).

ARCH-2 (docs/ pages for core subsystems) was stamped IMPLEMENTED by the
architect's cycle-220 re-audit, which re-audited three pages against current
code and marked three contract holes RESOLVED:

  1. docs/robots-cache.md  — "Thread-safe" claim RESOLVED (cycle 219 lock);
     new `put` guard path: max_entries<=0 -> no-op.
  2. docs/search-index.md  — add_page "Returns page id." drift RESOLVED
     (docstring now "NOT a page id"); search blanket docstring RESOLVED
     (now enumerates guard paths + scoring formula).
  3. docs/content-model.md — line refs corrected Page 330->371,
     PipelineStats 461->502.

This file pins the CODE-side facts those doc claims rest on, so a regression
that re-breaks the code (removes the lock, drops the put guard, reverts a
docstring, or shifts the class line refs) reopens the ticket. It is a VERIFY
pin, not a new probe: behavior is already covered by
test_robots_cache_adversarial.py and test_search_index_adversarial.py.
"""

from __future__ import annotations

import inspect
import re
import threading
import time

import personal_index.robots_cache as rc
from personal_index.robots_cache import RobotsCache, RobotsCacheEntry
from personal_index.index import SearchIndex
import personal_index.models as models


# ---------------------------------------------------------------------------
# 1. robots-cache: "Thread-safe" claim is now backed by a real lock
# ---------------------------------------------------------------------------
class TestRobotsCacheThreadSafetyClaim:
    def test_module_imports_threading(self):
        """The doc claims thread-safety; the module must import threading."""
        assert "threading" in dir(rc), "robots_cache must import threading"

    def test_class_docstring_still_claims_thread_safe(self):
        """The re-audit KEEPS the 'Thread-safe' claim (option a), so the
        docstring must still say it — the code now delivers it."""
        doc = RobotsCache.__doc__ or ""
        assert "Thread-safe" in doc, (
            f"RobotsCache docstring must keep the 'Thread-safe' claim, got: {doc!r}"
        )

    def test_init_creates_a_threading_lock(self):
        c = RobotsCache(ttl=3600, max_entries=4)
        assert hasattr(c, "_lock"), "RobotsCache.__init__ must create self._lock"
        assert type(c._lock).__name__ == "lock", (
            f"self._lock must be a threading.Lock, got {type(c._lock).__name__}"
        )

    def test_every_public_mutating_method_holds_the_lock(self):
        """get/put/invalidate/invalidate_all must each wrap their body in
        `with self._lock:` — the re-audit's resolution is per-method locking."""
        for name in ("get", "put", "invalidate", "invalidate_all"):
            src = inspect.getsource(getattr(RobotsCache, name))
            assert "with self._lock:" in src, (
                f"RobotsCache.{name} must acquire self._lock"
            )

    def test_concurrent_put_get_no_lost_updates(self):
        """End-to-end concurrency: 8 threads x 200 puts must never let size
        exceed max_entries and must never raise (the lock serializes)."""
        c = RobotsCache(ttl=3600, max_entries=50)
        errors: list[BaseException] = []

        def worker(n: int) -> None:
            try:
                for i in range(200):
                    c.put(RobotsCacheEntry(domain=f"d{n}-{i}.com", fetched_at=time.time()))
            except BaseException as exc:  # pragma: no cover - defensive
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(k,)) for k in range(8)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        assert not errors, f"concurrent put raised: {errors}"
        assert c.size <= 50, f"size={c.size} exceeded max_entries=50"


# ---------------------------------------------------------------------------
# 1b. robots-cache: new put guard path (max_entries <= 0 -> no-op)
# ---------------------------------------------------------------------------
class TestRobotsCachePutGuard:
    def test_max_entries_zero_put_is_noop(self):
        c = RobotsCache(ttl=3600, max_entries=0)
        c.put(RobotsCacheEntry(domain="a.com", fetched_at=time.time()))
        assert c.size == 0
        assert c.get("a.com") is None

    def test_max_entries_negative_put_is_noop(self):
        c = RobotsCache(ttl=3600, max_entries=-1)
        c.put(RobotsCacheEntry(domain="a.com", fetched_at=time.time()))
        assert c.size == 0
        assert c.get("a.com") is None

    def test_put_guard_source_is_le_zero(self):
        """The doc says the guard is `max_entries <= 0`; pin the exact bound."""
        src = inspect.getsource(RobotsCache.put)
        assert re.search(r"max_entries\s*<=\s*0", src), (
            "put() guard must be `if self._max_entries <= 0: return`"
        )


# ---------------------------------------------------------------------------
# 2. search-index: add_page + search docstrings now match the code
# ---------------------------------------------------------------------------
class TestSearchIndexDocstrings:
    def test_add_page_docstring_says_not_a_page_id(self):
        doc = SearchIndex.add_page.__doc__ or ""
        assert "NOT a page id" in doc, (
            f"add_page docstring must state 'NOT a page id', got: {doc!r}"
        )
        assert "Returns page id." not in doc, (
            "add_page docstring must not still claim 'Returns page id.'"
        )

    def test_add_page_returns_page_count_not_id(self):
        """Behavior pin: add_page returns len(self._pages) (a count), not an id."""
        idx = SearchIndex()
        from personal_index.models import IndexedPage
        idx.add_page(IndexedPage(url="http://a.com", title="A", content="alpha beta"))
        first = idx.add_page(IndexedPage(url="http://b.com", title="B", content="beta gamma"))
        assert first == 2, f"add_page must return the new page count (2), got {first}"

    def test_search_docstring_enumerates_guard_paths(self):
        doc = SearchIndex.search.__doc__ or ""
        # The re-audit reworded the blanket line to enumerate the guards.
        assert "limit" in doc and "<=" in doc, (
            f"search docstring must enumerate the limit<=0 guard, got: {doc!r}"
        )
        assert "3.0" in doc and "0.5" in doc, (
            "search docstring must state the scoring formula (title*3.0 + content*1.0 + score*0.5)"
        )

    def test_search_limit_zero_and_negative_return_empty(self):
        idx = SearchIndex()
        from personal_index.models import IndexedPage
        idx.add_page(IndexedPage(url="http://a.com", title="A", content="alpha beta"))
        assert idx.search("alpha", limit=0) == []
        assert idx.search("alpha", limit=-1) == []


# ---------------------------------------------------------------------------
# 3. content-model: corrected line refs (Page 330->371, PipelineStats 461->502)
# ---------------------------------------------------------------------------
class TestContentModelLineRefs:
    def _line_of(self, cls) -> int:
        """Line of the `class <Name>:` statement (not the @dataclass decorator)."""
        src_lines, start = inspect.getsourcelines(cls)
        for i, line in enumerate(src_lines):
            if re.match(rf"class {cls.__name__}\b", line):
                return start + i
        raise AssertionError(f"could not find `class {cls.__name__}:` in source")

    def test_page_class_at_line_371(self):
        assert self._line_of(models.Page) == 371, (
            f"docs/content-model.md pins Page at line 371, actual {self._line_of(models.Page)}"
        )

    def test_pipelinestats_class_at_line_502(self):
        assert self._line_of(models.PipelineStats) == 502, (
            f"docs/content-model.md pins PipelineStats at line 502, actual {self._line_of(models.PipelineStats)}"
        )
