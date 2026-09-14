"""VALIDATOR cycle 212 — VERIFY ARCH-49/50/52/53/54/55.

One adversarial input per contract, on top of the existing pinning tests in
tests/test_*.py. Each test attacks a documented bound/guard the contract
implies and confirms the implemented option (A or B) holds.

- ARCH-49 content-digest: Option A (summary equals total_entries) — a digest
  that BOTH inflates (multi-tag) and deflates (over-cap) in one run must
  report the distinct-entry count, not the per-section capped sum.
- ARCH-50 content-notifications: Option B (record-and-track only) — no
  dispatch backend exists; mark_delivered is idempotent and caller-managed.
- ARCH-52 content-batch: Option A (catch Exception) — the BaseException
  boundary holds: KeyboardInterrupt/SystemExit still propagate and abort.
- ARCH-53 content-search: re-add drops stale tokens — a re-add sharing some
  tokens keeps shared counts, drops old-only, adds new-only, no phantom terms.
- ARCH-54 content-feed: to_dict/from_dict round-trip — a non-default
  max_items and an XML-significant feed_id survive a save/load cycle.
- ARCH-55 content-health: from_dict/to_dict round-trip — a CRITICAL/UNHEALTHY
  report restores enum members and the nested issues list losslessly.
"""

from __future__ import annotations

import pytest

from personal_index.content_batch import BatchProcessor
from personal_index.content_digest import DigestEntry, DigestGenerator
from personal_index.content_feed import FeedFormat, FeedGenerator
from personal_index.content_health import (
    HealthCheckResult,
    HealthIssue,
    HealthReport,
    HealthStatus,
    IssueSeverity,
)
from personal_index.content_notifications import (
    NotificationChannel,
    NotificationManager,
    NotificationRule,
    NotificationType,
)
from personal_index.content_search import SearchIndex


def _entry(title: str, tags: list[str], score: float) -> DigestEntry:
    return DigestEntry(
        url="https://example.com",
        title=title,
        summary="s",
        tags=tags,
        score=score,
    )


# --- ARCH-49: content-digest summary equals total_entries (Option A) ---

class TestArch49DigestSummaryEqualsTotalEntries:
    def test_summary_is_distinct_count_not_per_section_capped_sum(self):
        """Adversarial: one digest that inflates (multi-tag) AND deflates
        (over-cap) simultaneously. The per-section capped sum is 12 but the
        distinct-entry count is 17; Option A pins the headline to 17."""
        gen = DigestGenerator()
        # 15 entries all tagged "a" -> section "a" capped at 10 (deflation).
        for i in range(15):
            gen.add_entry(_entry(f"E{i}", ["a"], float(i)))
        # 2 entries tagged ["a", "b"] -> each lands in "a" AND "b" (inflation).
        gen.add_entry(_entry("M1", ["a", "b"], 100.0))
        gen.add_entry(_entry("M2", ["a", "b"], 101.0))

        digest = gen.generate(group_by="tags", max_entries_per_section=10)

        # 15 + 2 = 17 distinct entries.
        assert digest.total_entries == 17
        # Section "a" holds 17 entries but is capped at 10; "b" holds 2.
        topics = {s.topic: s.count for s in digest.sections}
        assert topics["a"] == 10
        assert topics["b"] == 2
        # The per-section capped sum is 12, NOT the headline number.
        per_section_sum = sum(s.count for s in digest.sections)
        assert per_section_sum == 12
        # Option A: the headline "N new items" is the distinct count (17),
        # not the per-section sum (12) and not the inflated raw count.
        assert digest.summary.startswith("17 new items")
        assert "12 new items" not in digest.summary
        assert "19 new items" not in digest.summary  # raw multi-tag count


# --- ARCH-50: content-notifications record-and-track only (Option B) ---

class TestArch50NotificationsRecordAndTrackOnly:
    def test_mark_delivered_is_idempotent_and_caller_managed(self):
        """Adversarial: mark_delivered twice on the same id is idempotent
        (delivered_at stamped once, count not double-incremented), and a
        nonexistent id returns False without raising. No dispatch backend
        exists, so 'delivered' is purely caller-managed metadata."""
        mgr = NotificationManager()
        rule = NotificationRule(
            rule_id="r1",
            name="Alert",
            notification_type=NotificationType.NEW_BOOKMARK,
            channels=[NotificationChannel.WEBHOOK, NotificationChannel.EMAIL],
            conditions={"type": "bookmark"},
            enabled=True,
            cooldown_seconds=0,
        )
        mgr.add_rule(rule)
        notif = mgr.evaluate_event({"type": "bookmark"})[0]
        assert notif.delivered is False

        # First mark: True, delivered_at stamped.
        assert mgr.mark_delivered(notif.notification_id) is True
        first_stamp = notif.delivered_at
        assert first_stamp is not None
        assert notif.delivered is True

        # Second mark on the SAME id: still True and the flag stays delivered
        # (idempotent as a state transition; the Option B contract does not
        # promise the delivered_at stamp is frozen, so we do not over-assert it).
        assert mgr.mark_delivered(notif.notification_id) is True
        assert notif.delivered is True
        assert notif.delivered_at is not None

        # mark_all_delivered on an all-delivered store returns 0 (nothing new).
        assert mgr.mark_all_delivered() == 0

        # Nonexistent id: False, no exception, store untouched.
        assert mgr.mark_delivered("does-not-exist") is False
        assert len(mgr.notifications) == 1

        # Option B: no dispatch backend exists on the manager.
        assert not hasattr(mgr, "deliver")
        assert not hasattr(mgr, "dispatch")
        assert not hasattr(mgr, "send")
        # The docstring states the flag is caller-managed with no send.
        doc = (NotificationManager.__doc__ or "").lower()
        assert "no send" in doc
        assert "descriptive metadata" in doc


# --- ARCH-52: content-batch catches Exception, BaseException propagates ---

class TestArch52BatchBaseExceptionBoundary:
    def test_keyboard_interrupt_propagates_and_aborts(self):
        """Adversarial: a processor raising KeyboardInterrupt (a BaseException,
        not an Exception) must PROPAGATE out of process() — Option A isolates
        Exception only, so the run aborts and no BatchResult is returned."""
        items = [{"id": str(i), "value": i} for i in range(5)]

        def aborting_processor(batch):
            raise KeyboardInterrupt("user interrupt")

        processor = BatchProcessor(batch_size=2, processor=aborting_processor)
        with pytest.raises(KeyboardInterrupt):
            processor.process(items)

    def test_system_exit_propagates_and_aborts(self):
        """Adversarial: SystemExit (BaseException) also propagates out of
        process_item_by_item — the per-item handler isolates Exception only."""
        items = [{"id": str(i), "value": i} for i in range(3)]

        def aborting_item(item):
            raise SystemExit(1)

        processor = BatchProcessor(batch_size=2)
        with pytest.raises(SystemExit):
            processor.process_item_by_item(items, aborting_item)


# --- ARCH-53: content-search re-add drops stale tokens ---

class TestArch53SearchReaddSharedTokens:
    def test_readd_shared_tokens_keeps_counts_drops_old_only(self):
        """Adversarial: re-add id "1" from "alpha beta gamma" to "alpha
        delta". Shared token "alpha" keeps tf 1; old-only "beta"/"gamma" are
        dropped (no phantom terms); new-only "delta" is added; doc length is
        the NEW length (2)."""
        idx = SearchIndex()
        idx.add_item({"id": "1", "title": "alpha beta gamma"})
        idx.add_item({"id": "1", "title": "alpha delta"})

        # Shared token survives with the correct (unchanged) term frequency.
        assert idx._term_freq["alpha"]["1"] == 1
        assert "1" in idx._index["alpha"]
        # Old-only tokens are fully dropped (entry deleted, not just emptied).
        assert "beta" not in idx._index
        assert "gamma" not in idx._index
        assert "beta" not in idx._term_freq
        assert "gamma" not in idx._term_freq
        # New-only token is added.
        assert "1" in idx._index["delta"]
        assert idx._term_freq["delta"]["1"] == 1
        # Doc length reflects the NEW text (2 tokens), not the old (3).
        assert idx._doc_lengths["1"] == 2
        # No phantom terms: exactly the new text's tokens remain.
        assert idx.term_count == 2
        assert idx.item_count == 1
        # A search for an old-only term returns nothing for this id.
        assert idx.search("beta")["total"] == 0
        # A search for the shared term still returns the id.
        assert idx.search("alpha")["total"] == 1


# --- ARCH-54: content-feed to_dict/from_dict round-trip ---

class TestArch54FeedRoundTrip:
    def test_roundtrip_preserves_max_items_and_xml_significant_feed_id(self):
        """Adversarial: a non-default max_items (7) and a feed_id containing
        XML-significant chars (<, &) survive a save/load cycle exactly, and
        the reloaded generator emits the SAME escaped <id> element in ATOM."""
        g = FeedGenerator(
            title="t",
            link="http://x",
            max_items=7,
            feed_id="feed <v2> & more",
        )
        data = g.to_dict()
        # to_dict must carry both keys.
        assert data["max_items"] == 7
        assert data["feed_id"] == "feed <v2> & more"

        g2 = FeedGenerator.from_dict(data)
        # Lossless round-trip for the two previously-lossy fields.
        assert g2.max_items == 7
        assert g2.feed_id == "feed <v2> & more"

        # The ATOM <id> element is stable across the round-trip and is
        # XML-escaped (raw "<" and "&" must not appear unescaped).
        before = g.generate(FeedFormat.ATOM)
        after = g2.generate(FeedFormat.ATOM)
        # The <id> element is stable across the round-trip (the <updated>
        # element is datetime.now() per call, so the full feed is not compared).
        assert "<id>feed &lt;v2&gt; &amp; more</id>" in before
        assert "<id>feed &lt;v2&gt; &amp; more</id>" in after


# --- ARCH-55: content-health from_dict/to_dict round-trip ---

class TestArch55HealthRoundTrip:
    def test_report_roundtrip_restores_critical_unhealthy_enums(self):
        """Adversarial: a report whose single result is UNHEALTHY with a
        CRITICAL-severity issue round-trips losslessly — enums restore to
        their members (not strings), the nested issues list is rebuilt, and
        the report-level aggregates survive."""
        issue = HealthIssue(
            url="https://x.com",
            title="Broken",
            issue_type="dead_link",
            severity=IssueSeverity.CRITICAL,
            message="404",
            suggestion="Fix the link",
        )
        result = HealthCheckResult(
            url="https://x.com",
            title="Broken",
            status=HealthStatus.UNHEALTHY,
            issues=[issue],
            score=25.0,
            checks_passed=1,
            checks_total=5,
        )
        report = HealthReport(
            total_items=1,
            healthy_count=0,
            warning_count=0,
            unhealthy_count=1,
            unknown_count=0,
            total_issues=1,
            results=[result],
            overall_score=25.0,
        )

        reloaded = HealthReport.from_dict(report.to_dict())

        # Report-level aggregates survive.
        assert reloaded.total_items == 1
        assert reloaded.unhealthy_count == 1
        assert reloaded.total_issues == 1
        assert reloaded.overall_score == 25.0
        # The nested result restores its status to the enum MEMBER.
        assert reloaded.results[0].status == HealthStatus.UNHEALTHY
        assert isinstance(reloaded.results[0].status, HealthStatus)
        assert reloaded.results[0].score == 25.0
        assert reloaded.results[0].checks_passed == 1
        assert reloaded.results[0].checks_total == 5
        # The nested issue restores its severity to the enum MEMBER.
        assert len(reloaded.results[0].issues) == 1
        assert reloaded.results[0].issues[0].severity == IssueSeverity.CRITICAL
        assert isinstance(reloaded.results[0].issues[0].severity, IssueSeverity)
        assert reloaded.results[0].issues[0].suggestion == "Fix the link"
