"""Adversarial deep tests for personal_index/content_digest.py (cycle 253).

content_digest.py is a never-probed subsystem (no prior tests/deep file).
This file attacks the documented contract in docs/content-digest.md:

  - DigestEntry.to_dict: exact key set/order, tags-list aliasing (documented
    hole), round-trip.
  - DigestSection.count: a @property, not a method.
  - ContentDigest.to_dict: nested deep-copy of entries (no live aliasing),
    but per-entry tags list still aliased (documented hole).
  - format_markdown vs format_text divergence: markdown emits full summary +
    Tags line; text truncates summary to 100 chars and omits tags (documented
    divergence).
  - DigestGenerator.generate:
      * ARCH-49 Option A contract: the summary's "N new items" figure ALWAYS
        equals total_entries (distinct-entry count), NOT the sum of the
        per-section (capped) counts. Multi-tag entries must NOT inflate it and
        the per-section cap must NOT deflate it.
      * sort by score descending (stable for equal scores).
      * max_entries_per_section clamped to 0 for negative values (documented).
      * group_by dispatch: "none" -> single "All Content" section; "source" ->
        per-source (falsy source -> "Unknown"); anything else -> tag grouping.
      * empty input -> sections=[], total_entries=0, "No new content found."
      * period_start/period_end passed through verbatim when truthy, never
        parsed (documented hole).
  - idempotence: two identical generate() calls produce equal digests.
  - unicode round-trip through to_dict.
  - end-to-end CLI run through the installed `personal-index` group (the
    digest module has no CLI command of its own, so the e2e run exercises the
    CLI group's guard path: an empty index search returns the documented
    "No indexed content found" message with exit code 0).
"""

from __future__ import annotations

import json
import re

from click.testing import CliRunner

from personal_index.cli import main
from personal_index.content_digest import (
    ContentDigest,
    DigestEntry,
    DigestGenerator,
    DigestSection,
)


def _entry(url="https://x.test/a", title="T", summary="S", tags=None,
           score=0.0, source="") -> DigestEntry:
    return DigestEntry(url=url, title=title, summary=summary,
                       tags=list(tags or []), score=score, source=source)


# ---------------------------------------------------------------------------
# DigestEntry.to_dict
# ---------------------------------------------------------------------------
class TestDigestEntryToDict:
    def test_exact_keys_and_order(self):
        e = _entry(url="u", title="t", summary="s", tags=["a", "b"],
                   score=1.5, source="src")
        d = e.to_dict()
        assert list(d.keys()) == ["url", "title", "summary", "tags",
                                  "score", "timestamp", "source"]
        assert d["url"] == "u" and d["title"] == "t" and d["summary"] == "s"
        assert d["tags"] == ["a", "b"] and d["score"] == 1.5
        assert d["source"] == "src" and d["timestamp"] == ""

    def test_tags_list_is_aliased_not_copied(self):
        """Documented hole: to_dict returns the SAME list object."""
        e = _entry(tags=["a", "b"])
        d = e.to_dict()
        d["tags"].append("c")
        assert e.tags == ["a", "b", "c"], "to_dict must alias the tags list"

    def test_round_trip_json(self):
        e = _entry(url="https://x.test/ünïcode", title="Титл",
                   summary="суммаризация", tags=["тэг", "tag"])
        d = e.to_dict()
        rt = json.loads(json.dumps(d, ensure_ascii=False))
        assert rt["url"] == e.url and rt["title"] == e.title
        assert rt["summary"] == e.summary and rt["tags"] == e.tags


# ---------------------------------------------------------------------------
# DigestSection.count
# ---------------------------------------------------------------------------
class TestDigestSectionCount:
    def test_count_is_property(self):
        s = DigestSection(topic="t", entries=[_entry(), _entry(), _entry()])
        assert s.count == 3
        # It is a property, not a method: calling it must fail.
        try:
            s.count()  # type: ignore[misc]
        except TypeError:
            pass
        else:
            raise AssertionError("count must be a property, not a method")

    def test_count_empty(self):
        assert DigestSection(topic="t").count == 0


# ---------------------------------------------------------------------------
# ContentDigest.to_dict
# ---------------------------------------------------------------------------
class TestContentDigestToDict:
    def test_nested_entries_deep_copied(self):
        e = _entry(url="u", title="t", summary="s", tags=["a"])
        sec = DigestSection(topic="t", entries=[e])
        d = ContentDigest(title="D", generated_at="g", period_start="p0",
                          period_end="p1", sections=[sec],
                          total_entries=1, summary="1 new items").to_dict()
        # The nested entry dict is a fresh dict, not the live object.
        assert isinstance(d["sections"][0]["entries"][0], dict)
        # But the per-entry tags list is still aliased (documented hole).
        d["sections"][0]["entries"][0]["tags"].append("z")
        assert e.tags == ["a", "z"]

    def test_keys(self):
        d = ContentDigest(title="D", generated_at="g", period_start="p0",
                          period_end="p1").to_dict()
        assert list(d.keys()) == ["title", "generated_at", "period_start",
                                  "period_end", "sections", "total_entries",
                                  "summary"]


# ---------------------------------------------------------------------------
# format_markdown vs format_text divergence
# ---------------------------------------------------------------------------
class TestFormatDivergence:
    def test_markdown_full_summary_and_tags(self):
        e = _entry(url="u", title="t", summary="S" * 200, tags=["a", "b"])
        sec = DigestSection(topic="t", entries=[e])
        d = ContentDigest(title="D", generated_at="g", period_start="p0",
                          period_end="p1", sections=[sec],
                          total_entries=1, summary="1 new items")
        md = d.format_markdown()
        assert "### [t](u)" in md
        assert "S" * 200 in md, "markdown must emit the FULL summary"
        assert "Tags: a, b" in md

    def test_text_truncates_summary_and_omits_tags(self):
        e = _entry(url="u", title="t", summary="S" * 200, tags=["a", "b"])
        sec = DigestSection(topic="t", entries=[e])
        d = ContentDigest(title="D", generated_at="g", period_start="p0",
                          period_end="p1", sections=[sec],
                          total_entries=1, summary="1 new items")
        txt = d.format_text()
        assert "S" * 100 in txt, "text must truncate summary to 100 chars"
        assert "S" * 101 not in txt, "text must NOT emit more than 100 chars"
        assert "Tags:" not in txt, "text must omit the tags line"

    def test_markdown_no_escaping(self):
        """Documented hole: no escaping applied to any field."""
        e = _entry(url="u", title="**bold**", summary="a # heading")
        sec = DigestSection(topic="t", entries=[e])
        d = ContentDigest(title="D", generated_at="g", period_start="p0",
                          period_end="p1", sections=[sec],
                          total_entries=1, summary="")
        md = d.format_markdown()
        assert "**bold**" in md, "markdown applies no escaping"


# ---------------------------------------------------------------------------
# DigestGenerator.generate — ARCH-49 Option A (summary == total_entries)
# ---------------------------------------------------------------------------
class TestGenerateSummaryContract:
    def test_multitag_does_not_inflate(self):
        """ARCH-49 Option A: a 2-tag entry must NOT make the summary say 2."""
        g = DigestGenerator()
        g.add_entry(_entry(url="u1", tags=["a", "b"], score=1.0))
        d = g.generate()
        assert d.total_entries == 1
        assert d.summary.startswith("1 new items"), d.summary

    def test_cap_does_not_deflate(self):
        """ARCH-49 Option A: 15 entries under one tag, cap 10 -> still 15."""
        g = DigestGenerator()
        for i in range(15):
            g.add_entry(_entry(url=f"u{i}", tags=["a"], score=float(i)))
        d = g.generate(max_entries_per_section=10)
        assert d.total_entries == 15
        # The per-section cap truncates the section, but the headline figure
        # must still equal the distinct-entry count.
        assert d.summary.startswith("15 new items"), d.summary
        # And the section itself IS capped (the cap still applies to display).
        assert d.sections[0].count == 10

    def test_summary_equals_total_entries_property(self):
        """Property check across random-ish inputs: N in summary == total."""
        g = DigestGenerator()
        entries = [
            _entry(url=f"u{i}", tags=[f"t{i % 3}"], score=float(i % 5))
            for i in range(23)
        ]
        g.add_entries(entries)
        d = g.generate()
        m = re.match(r"^(\d+) new items", d.summary)
        assert m, d.summary
        assert int(m.group(1)) == d.total_entries == 23

    def test_empty_input(self):
        g = DigestGenerator()
        d = g.generate()
        assert d.sections == []
        assert d.total_entries == 0
        assert d.summary == "No new content found."

    def test_source_grouping_falsy_source_is_unknown(self):
        g = DigestGenerator()
        g.add_entry(_entry(url="u1", source="", score=1.0))
        g.add_entry(_entry(url="u2", source="real", score=2.0))
        d = g.generate(group_by="source")
        topics = [s.topic for s in d.sections]
        assert "Unknown" in topics and "real" in topics
        # source grouping: each entry in exactly one bucket -> sum == total
        assert sum(s.count for s in d.sections) == d.total_entries == 2

    def test_group_by_none_single_section(self):
        g = DigestGenerator()
        for i in range(5):
            g.add_entry(_entry(url=f"u{i}", tags=["x"], score=float(i)))
        d = g.generate(group_by="none")
        assert len(d.sections) == 1
        assert d.sections[0].topic == "All Content"
        assert d.sections[0].count == 5

    def test_unrecognized_group_by_falls_to_tags(self):
        g = DigestGenerator()
        g.add_entry(_entry(url="u1", tags=["a"], score=1.0))
        d = g.generate(group_by="tag")  # typo -> tag grouping
        assert [s.topic for s in d.sections] == ["a"]


# ---------------------------------------------------------------------------
# Sorting and clamping
# ---------------------------------------------------------------------------
class TestGenerateSortingClamping:
    def test_sort_by_score_descending(self):
        g = DigestGenerator()
        g.add_entry(_entry(url="low", tags=["a"], score=1.0))
        g.add_entry(_entry(url="high", tags=["a"], score=9.0))
        g.add_entry(_entry(url="mid", tags=["a"], score=5.0))
        d = g.generate()
        urls = [e.url for e in d.sections[0].entries]
        assert urls == ["high", "mid", "low"]

    def test_stable_sort_equal_scores(self):
        g = DigestGenerator()
        g.add_entry(_entry(url="first", tags=["a"], score=1.0))
        g.add_entry(_entry(url="second", tags=["a"], score=1.0))
        d = g.generate()
        urls = [e.url for e in d.sections[0].entries]
        assert urls == ["first", "second"], "stable sort must keep insertion order"

    def test_negative_cap_clamped_to_zero(self):
        """Documented: negative max_entries_per_section clamped to 0."""
        g = DigestGenerator()
        for i in range(3):
            g.add_entry(_entry(url=f"u{i}", tags=["a"], score=float(i)))
        d = g.generate(max_entries_per_section=-5)
        # Clamped to 0 -> empty sections (no entries displayed).
        assert all(s.count == 0 for s in d.sections)
        # But the distinct-entry count / headline figure is unaffected.
        assert d.total_entries == 3
        assert d.summary.startswith("3 new items"), d.summary

    def test_zero_cap(self):
        g = DigestGenerator()
        g.add_entry(_entry(url="u1", tags=["a"], score=1.0))
        d = g.generate(max_entries_per_section=0)
        assert all(s.count == 0 for s in d.sections)
        assert d.total_entries == 1


# ---------------------------------------------------------------------------
# Period passthrough + idempotence
# ---------------------------------------------------------------------------
class TestPeriodAndIdempotence:
    def test_period_passthrough_verbatim(self):
        """Documented hole: malformed period strings passed through unchanged."""
        g = DigestGenerator()
        g.add_entry(_entry(url="u1", tags=["a"], score=1.0))
        d = g.generate(period_start="not-a-date", period_end="also-not-a-date")
        assert d.period_start == "not-a-date"
        assert d.period_end == "also-not-a-date"

    def test_period_defaults_when_falsy(self):
        g = DigestGenerator()
        g.add_entry(_entry(url="u1", tags=["a"], score=1.0))
        d = g.generate(period_start="", period_end="")
        # Falsy -> defaults substituted (ISO-8601 UTC, non-empty).
        assert d.period_start and d.period_end
        assert "T" in d.period_start and "T" in d.period_end

    def test_generate_idempotent(self):
        g = DigestGenerator()
        g.add_entry(_entry(url="u1", tags=["a"], score=1.0))
        g.add_entry(_entry(url="u2", tags=["b"], score=2.0))
        d1 = g.generate(period_start="p0", period_end="p1")
        d2 = g.generate(period_start="p0", period_end="p1")
        # Same entries -> same sections/total/summary (generated_at may differ
        # only if a wall-clock tick lands between calls; pin the stable fields).
        assert d1.total_entries == d2.total_entries
        assert d1.summary == d2.summary
        assert [s.topic for s in d1.sections] == [s.topic for s in d2.sections]
        assert [[e.url for e in s.entries] for s in d1.sections] == \
               [[e.url for e in s.entries] for s in d2.sections]

    def test_clear(self):
        g = DigestGenerator()
        g.add_entry(_entry(url="u1", tags=["a"], score=1.0))
        g.clear()
        d = g.generate()
        assert d.total_entries == 0 and d.sections == []


# ---------------------------------------------------------------------------
# End-to-end CLI run (the digest module has no CLI command; exercise the
# installed CLI group's documented empty-index guard path).
# ---------------------------------------------------------------------------
class TestCliEndToEnd:
    def test_search_empty_index_guard(self, tmp_path):
        dd = str(tmp_path)
        runner = CliRunner()
        res = runner.invoke(main, ["search", "anything", "--data-dir", dd])
        assert res.exit_code == 0, res.output
        assert "No indexed content found" in res.output

    def test_export_empty_index_guard(self, tmp_path):
        dd = str(tmp_path)
        runner = CliRunner()
        res = runner.invoke(main, ["export", "--data-dir", dd])
        assert res.exit_code == 0, res.output
        assert "No indexed content to export" in res.output
