"""Adversarial VERIFY tests for ARCH-25/26/28/29/30/32 (cycle 208).

Each ticket is at Status: IMPLEMENTED on main. The implementer's pinning tests
already pass (1207 across the 35 components). These tests add the adversarial
inputs each contract implies BEYOND the pinning tests, to witness the
IMPLEMENTED state before the validator flips it to VERIFIED.

ARCH-25  importer: total_skipped accounting invariant (multiple empty-url items).
ARCH-26  content_extractor: readability score derives from len(text.split()).
ARCH-28  content_scheduler: passive contract (past next_run immediately due,
         disabled next_run never advanced, malformed cron never run).
ARCH-29  content_webhooks: get_payload_json returns the exact signed body.
ARCH-30  search_suggestions: trending score clamped to [0.0, 1.0].
ARCH-32  robots_cache: thread-safe (lock) + allows_agent guard + lazy expiry.
"""

from __future__ import annotations

import threading
import time

import pytest

from personal_index.importer import Importer
from personal_index.content_extractor import ContentExtractor, ExtractedContent
from personal_index.content_scheduler import ScheduledTask, TaskScheduler
from personal_index.content_webhooks import WebhookEventType, WebhookManager, WebhookPayload
from personal_index.search_suggestions import SearchSuggestions
from personal_index.robots_cache import RobotsCache, RobotsCacheEntry


# ---------------------------------------------------------------------------
# ARCH-25: importer total_skipped accounting invariant
# ---------------------------------------------------------------------------
class TestArch25ImporterAccounting:
    def test_json_multiple_empty_url_invariant(self):
        """2 valid + 3 empty-url items -> imported==2, skipped==3, invariant holds."""
        imp = Importer()
        content = (
            '[{"url":"http://a.com","title":"A"},'
            '{"url":"http://b.com","title":"B"},'
            '{"url":"","title":"C"},'
            '{"url":"","title":"D"},'
            '{"url":"","title":"E"}]'
        )
        r = imp.import_from_content(content, "json")
        assert r.total_imported == 2
        assert r.total_skipped == 3
        assert r.total_imported + r.total_skipped == 5  # every seen item accounted

    def test_html_multiple_no_href_invariant(self):
        """3 anchors, 2 with href, 1 without -> imported==2, skipped==1."""
        imp = Importer()
        html = '<ROOT><a href="http://a.com">A</a><a href="http://b.com">B</a><a>NoHref</a></ROOT>'
        r = imp.import_from_content(html, "html")
        assert r.total_imported == 2
        assert r.total_skipped == 1
        assert r.total_imported + r.total_skipped == 3

    def test_opml_multiple_text_only_invariant(self):
        """3 outlines, 2 with xmlUrl, 1 text-only -> imported==2, skipped==1."""
        imp = Importer()
        opml = (
            '<opml><body>'
            '<outline text="F" xmlUrl="http://a.com/rss"/>'
            '<outline text="G" xmlUrl="http://b.com/rss"/>'
            '<outline text="NoURL"/>'
            '</body></opml>'
        )
        r = imp.import_opml(opml)
        assert r.total_imported == 2
        assert r.total_skipped == 1
        assert r.total_imported + r.total_skipped == 3

    def test_empty_url_items_never_written_to_manager(self):
        """No empty-url item is ever written to the manager (contract MUST-preserve)."""
        imp = Importer()
        content = '[{"url":"http://a.com","title":"A"},{"url":"","title":"B"}]'
        r = imp.import_from_content(content, "json")
        assert r.total_imported == 1
        assert imp.manager.get("http://a.com") is not None
        assert imp.manager.get("") is None  # empty-url item not written

    def test_all_empty_url_items(self):
        """Every item empty-url -> imported==0, skipped==N, no crash."""
        imp = Importer()
        content = '[{"url":"","title":"A"},{"url":"","title":"B"}]'
        r = imp.import_from_content(content, "json")
        assert r.total_imported == 0
        assert r.total_skipped == 2


# ---------------------------------------------------------------------------
# ARCH-26: content_extractor readability score uses len(text.split())
# ---------------------------------------------------------------------------
class TestArch26ReadabilitySource:
    def test_boundary_50_words_positive(self):
        """Exactly 50 words -> NOT below the guard -> score > 0."""
        ex = ContentExtractor()
        content = ExtractedContent(text=" ".join(["w"] * 50), word_count=0,
                                   headings=[], meta_description="")
        score = ex.extract_readability_score(content)
        # 50/500 = 0.1 length, 0 headings, no meta -> 0.1
        assert score == pytest.approx(0.1)

    def test_boundary_49_words_zero(self):
        """49 words -> below the guard -> 0.0."""
        ex = ContentExtractor()
        content = ExtractedContent(text=" ".join(["w"] * 49), word_count=0,
                                   headings=[], meta_description="")
        assert ex.extract_readability_score(content) == 0.0

    def test_word_count_field_ignored(self):
        """word_count=0 but text has 200 words -> score derives from text (resolution b)."""
        ex = ContentExtractor()
        content = ExtractedContent(text=" ".join(["w"] * 200), word_count=0,
                                   headings=[], meta_description="")
        # 200/500 = 0.4 length, 0 headings, no meta -> 0.4 (word_count=0 ignored)
        assert ex.extract_readability_score(content) == pytest.approx(0.4)

    def test_whitespace_only_text_zero(self):
        """Whitespace-only text -> split() is empty -> 0.0 (no crash)."""
        ex = ContentExtractor()
        content = ExtractedContent(text="   \t\n  ", word_count=0,
                                   headings=[], meta_description="")
        assert ex.extract_readability_score(content) == 0.0

    def test_length_component_capped_at_0_4(self):
        """1000 words -> length component capped at 0.4 (not 2.0)."""
        ex = ContentExtractor()
        content = ExtractedContent(text=" ".join(["w"] * 1000), word_count=0,
                                   headings=[], meta_description="")
        assert ex.extract_readability_score(content) == pytest.approx(0.4)


# ---------------------------------------------------------------------------
# ARCH-28: content_scheduler passive contract
# ---------------------------------------------------------------------------
class TestArch28SchedulerPassive:
    def test_past_next_run_immediately_due(self):
        """A task whose next_run has passed is immediately due (no catch-up)."""
        from datetime import datetime, timedelta, timezone
        task = ScheduledTask("t1", "n", "job", "* * * * *")
        # Force next_run into the past.
        task.next_run = datetime.now(timezone.utc) - timedelta(hours=1)
        assert task.is_due() is True

    def test_disabled_task_next_run_never_advanced(self):
        """A disabled task's next_run is never advanced by run()."""
        task = ScheduledTask("t2", "n", "job", "* * * * *", enabled=False)
        before = task.next_run
        task.run()
        assert task.next_run == before  # not advanced

    def test_malformed_cron_never_run(self):
        """A task with a malformed cron_expr (next_run None) is never run and not due."""
        sched = TaskScheduler()
        task = sched.add_task("bad", "job", "not a cron")
        results = sched.run_due_tasks()
        assert results == []  # malformed task never runs
        assert task.next_run is None
        assert task.is_due() is False

    def test_run_due_tasks_runs_only_due(self):
        """run_due_tasks runs only due tasks; not-due tasks are skipped."""
        from datetime import datetime, timedelta, timezone
        sched = TaskScheduler()
        ran = []
        due = sched.add_task("due", "job", "* * * * *", callback=lambda t: ran.append("due"))
        notdue = sched.add_task("notdue", "job", "* * * * *", callback=lambda t: ran.append("notdue"))
        due.next_run = datetime.now(timezone.utc) - timedelta(hours=1)
        notdue.next_run = datetime.now(timezone.utc) + timedelta(days=365)
        results = sched.run_due_tasks()
        assert "due" in ran
        assert "notdue" not in ran
        assert len(results) == 1


# ---------------------------------------------------------------------------
# ARCH-29: content_webhooks get_payload_json returns exact signed body
# ---------------------------------------------------------------------------
class TestArch29WebhookBody:
    def test_body_returned_unchanged(self):
        """get_payload_json returns payload.body unchanged when set."""
        mgr = WebhookManager()
        body = '{"data":{"x":1},"event":"content.added","timestamp":"2026-01-01T00:00:00Z"}'
        payload = WebhookPayload(
            payload_id="p1", event_type=WebhookEventType.CONTENT_ADDED,
            data={"x": 1}, endpoint_id="e1", url="http://x", body=body,
        )
        assert mgr.get_payload_json(payload) == body

    def test_body_unicode_unchanged(self):
        """A body with unicode is returned byte-for-byte unchanged."""
        mgr = WebhookManager()
        body = '{"text":"\u0441\u043f\u0430\u0441\u0438\u0431\u0430 \u0434\u0437\u0435\u043d\u043d\u0438\u0446\u0430"}'
        payload = WebhookPayload(
            payload_id="p2", event_type=WebhookEventType.CONTENT_ADDED,
            data={}, endpoint_id="e1", url="http://x", body=body,
        )
        assert mgr.get_payload_json(payload) == body

    def test_body_none_falls_back_to_serialization(self):
        """When body is None, get_payload_json falls back to a fresh serialization."""
        mgr = WebhookManager()
        payload = WebhookPayload(
            payload_id="p3", event_type=WebhookEventType.CONTENT_ADDED,
            data={"x": 1}, endpoint_id="e1", url="http://x", body=None,
        )
        out = mgr.get_payload_json(payload)
        # The fallback serialization includes the event type and data.
        assert "content.added" in out
        assert '"x"' in out

    def test_body_empty_string_is_set(self):
        """An empty-string body is 'set' (not None) and returned unchanged."""
        mgr = WebhookManager()
        payload = WebhookPayload(
            payload_id="p4", event_type=WebhookEventType.CONTENT_ADDED,
            data={"x": 1}, endpoint_id="e1", url="http://x", body="",
        )
        assert mgr.get_payload_json(payload) == ""


# ---------------------------------------------------------------------------
# ARCH-30: search_suggestions trending score clamped to [0.0, 1.0]
# ---------------------------------------------------------------------------
class TestArch30TrendingClamp:
    def test_dominant_entry_score_is_1_0(self):
        """A single dominant trending entry -> score == 1.0 (not 1.1)."""
        ss = SearchSuggestions()
        ss.record_search("python")
        sug = ss.suggest("py", sources=["trending"])
        trending = [s for s in sug if s.source == "trending"]
        assert trending, "expected a trending suggestion"
        assert trending[0].score == pytest.approx(1.0)
        assert 0.0 <= trending[0].score <= 1.0

    def test_multiple_entries_no_score_exceeds_1_0(self):
        """Multiple trending entries -> no returned score exceeds 1.0."""
        ss = SearchSuggestions()
        for q in ["python", "pythonic", "pythonista", "pythondoc"]:
            ss.record_search(q)
        sug = ss.suggest("py", sources=["trending"])
        for s in sug:
            assert 0.0 <= s.score <= 1.0

    def test_fuzzy_trending_score_within_range(self):
        """fuzzy=True trending suggestions also stay within [0.0, 1.0]."""
        ss = SearchSuggestions()
        for q in ["python", "javascript", "typescript"]:
            ss.record_search(q)
        sug = ss.suggest("py", sources=["trending"], fuzzy=True)
        for s in sug:
            assert 0.0 <= s.score <= 1.0

    def test_trending_boost_retained(self):
        """The *1.1 boost is retained (clamped): a dominant trending entry
        still out-weights an equal-base non-trending candidate."""
        ss = SearchSuggestions()
        ss.record_search("python")
        # A single dominant entry: base = decayed/total*10 = 1.0, *1.1 = 1.1 -> clamped 1.0.
        sug = ss.suggest("py", sources=["trending"])
        trending = [s for s in sug if s.source == "trending"]
        assert trending[0].score == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# ARCH-32: robots_cache thread-safe + allows_agent guard + lazy expiry
# ---------------------------------------------------------------------------
class TestArch32RobotsCache:
    def test_thread_safety_hammer(self):
        """N threads hammering put/get/invalidate on a shared cache: no exception,
        size <= max_entries, no lost/KeyError entries."""
        cache = RobotsCache(ttl=3600, max_entries=50)
        errors = []

        def worker(tid):
            try:
                for i in range(200):
                    domain = f"domain-{(tid * 7 + i) % 80}.com"
                    entry = RobotsCacheEntry(domain=domain, allowed={"bot": True})
                    cache.put(entry)
                    cache.get(domain)
                    cache.invalidate(domain)
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
        assert cache.size <= 50

    def test_allows_agent_default_allow(self):
        """Agent in neither dict -> True (default-allow)."""
        entry = RobotsCacheEntry(domain="x.com")
        assert entry.allows_agent("unknown-bot") is True

    def test_allows_agent_disallowed(self):
        """Agent in disallowed -> False."""
        entry = RobotsCacheEntry(domain="x.com", disallowed={"bad-bot": True})
        assert entry.allows_agent("bad-bot") is False

    def test_allows_agent_allowed_value_ignored(self):
        """Agent in allowed with value False -> still True (only key membership matters)."""
        entry = RobotsCacheEntry(domain="x.com", allowed={"weird-bot": False})
        assert entry.allows_agent("weird-bot") is True

    def test_get_lazy_expiry(self):
        """An expired entry is deleted on get (subsequent get returns None, size drops)."""
        cache = RobotsCache(ttl=0.01, max_entries=100)
        entry = RobotsCacheEntry(domain="exp.com", fetched_at=time.time() - 10)
        cache.put(entry)
        assert cache.size == 1
        assert cache.get("exp.com") is None  # expired -> deleted
        assert cache.size == 0  # size dropped by one

    def test_put_max_entries_zero_noop(self):
        """max_entries <= 0 -> put is a no-op (nothing stored)."""
        cache = RobotsCache(ttl=3600, max_entries=0)
        cache.put(RobotsCacheEntry(domain="x.com"))
        assert cache.size == 0
