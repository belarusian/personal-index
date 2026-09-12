"""Cycle 169 PROBE: personal_index/link_analyzer.py (never-probed subsystem).

Adversarial deep tests for the LinkAnalyzer:
  - analyze: empty links, missing url key, whitespace/unicode anchors,
    internal vs external classification, base_domain case-insensitivity,
    empty base_domain (all external), anchor truncation, suspicious flags,
    idempotence, top-N (10) vs distribution (20) split.
  - analyze_batch / get_aggregate_stats: empty, duplicates, unicode.
  - guard inputs: None / empty / whitespace / out-of-range.
  - one end-to-end run through the installed CLI (status).

The documented contract (analyze docstring) was attacked. Two REAL defects
were found and filed:

  QA-9  - analyze with a NEGATIVE max_anchor_length corrupts anchor text
          (a[:-1] drops the last character instead of clamping to 0).
  QA-10 - get_aggregate_stats computes unique_external_domains from the
          top-20-truncated domain_distribution, so it undercounts whenever a
          page has more than 20 distinct external domains.

Both are pinned xfail-strict so the suite stays green while the defects are
open; they flip to hard passes once the implementer fixes them.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from personal_index.link_analyzer import LinkAnalyzer


@pytest.fixture
def analyzer() -> LinkAnalyzer:
    return LinkAnalyzer(base_domain="example.com")


# ── analyze: basic + guard inputs ───────────────────────────────────────


class TestAnalyzeGuards:
    def test_empty_links(self, analyzer):
        r = analyzer.analyze("http://example.com/", [])
        assert r.stats.total_links == 0
        assert r.stats.internal_links == 0
        assert r.stats.external_links == 0
        assert r.stats.unique_domains == 0
        assert r.top_anchor_texts == []
        assert r.top_domains == []
        assert r.suspicious_links == []

    def test_missing_url_key_skipped(self, analyzer):
        # A link dict without a "url" key -> link.get("url","") == "" -> skipped.
        r = analyzer.analyze("http://example.com/", [{"text": "t"}])
        assert r.stats.total_links == 0

    def test_empty_url_skipped(self, analyzer):
        r = analyzer.analyze("http://example.com/", [{"url": "", "text": "t"}])
        assert r.stats.total_links == 0

    def test_whitespace_url_counted(self, analyzer):
        # A whitespace url is truthy -> counted (urlparse of " " -> netloc "").
        r = analyzer.analyze("http://example.com/", [{"url": " ", "text": "t"}])
        assert r.stats.total_links == 1

    def test_url_none_preserved(self, analyzer):
        # url=None is stored verbatim; analysis still runs over the links.
        r = analyzer.analyze(None, [{"url": "http://ext.com/x", "text": "t"}])
        assert r.url is None
        assert r.stats.total_links == 1


class TestAnalyzeNoneGuards:
    """None inputs are OUT OF CONTRACT (signatures are str / list[dict]).

    Pinned as documented crashes (not xfail) so a future None-safety contract
    change is caught. The docstring promises nothing about None input.
    """

    def test_links_none_raises(self, analyzer):
        with pytest.raises(TypeError):
            analyzer.analyze("http://example.com/", None)

    def test_text_none_raises(self, analyzer):
        with pytest.raises(AttributeError):
            analyzer.analyze("http://example.com/", [{"url": "http://ext.com/x", "text": None}])


# ── internal vs external classification ─────────────────────────────────


class TestClassification:
    def test_internal_same_domain(self, analyzer):
        r = analyzer.analyze("http://example.com/", [{"url": "http://example.com/a", "text": "t"}])
        assert r.stats.internal_links == 1
        assert r.stats.external_links == 0
        assert r.stats.unique_domains == 0

    def test_external_other_domain(self, analyzer):
        r = analyzer.analyze("http://example.com/", [{"url": "http://other.com/a", "text": "t"}])
        assert r.stats.external_links == 1
        assert r.stats.internal_links == 0
        assert r.stats.unique_domains == 1
        assert r.top_domains == [("other.com", 1)]

    def test_base_domain_case_insensitive(self):
        a = LinkAnalyzer(base_domain="Example.COM")
        r = a.analyze("http://example.com/", [{"url": "http://EXAMPLE.com/a", "text": "t"}])
        assert r.stats.internal_links == 1

    def test_empty_base_domain_all_external(self):
        a = LinkAnalyzer(base_domain="")
        r = a.analyze("http://example.com/", [{"url": "http://example.com/a", "text": "t"}])
        assert r.stats.external_links == 1
        assert r.stats.internal_links == 0

    def test_mixed_counts(self, analyzer):
        links = [
            {"url": "http://example.com/a", "text": "i1"},
            {"url": "http://example.com/b", "text": "i2"},
            {"url": "http://a.com/x", "text": "e1"},
            {"url": "http://b.com/x", "text": "e2"},
            {"url": "http://a.com/y", "text": "e3"},
        ]
        r = analyzer.analyze("http://example.com/", links)
        assert r.stats.total_links == 5
        assert r.stats.internal_links == 2
        assert r.stats.external_links == 3
        assert r.stats.unique_domains == 2  # a.com, b.com


# ── anchor text handling ────────────────────────────────────────────────


class TestAnchorText:
    def test_anchor_stripped(self, analyzer):
        r = analyzer.analyze("http://example.com/", [{"url": "http://ext.com/x", "text": "  hello  "}])
        assert r.stats.anchor_text_distribution == {"hello": 1}

    def test_whitespace_anchor_not_counted(self, analyzer):
        r = analyzer.analyze("http://example.com/", [{"url": "http://ext.com/x", "text": "   "}])
        assert r.stats.anchor_text_distribution == {}

    def test_anchor_truncated_to_max(self):
        a = LinkAnalyzer(base_domain="example.com", max_anchor_length=5)
        r = a.analyze("http://example.com/", [{"url": "http://ext.com/x", "text": "hello world"}])
        assert r.stats.anchor_text_distribution == {"hello": 1}

    def test_anchor_truncated_after_strip(self):
        # strip first, then truncate: "  hi  " -> "hi" (len 2 < 5) -> "hi".
        a = LinkAnalyzer(base_domain="example.com", max_anchor_length=5)
        r = a.analyze("http://example.com/", [{"url": "http://ext.com/x", "text": "  hi  "}])
        assert r.stats.anchor_text_distribution == {"hi": 1}

    def test_unicode_anchor(self, analyzer):
        r = analyzer.analyze("http://example.com/", [{"url": "http://ext.com/x", "text": "héllo wörld"}])
        assert r.stats.anchor_text_distribution == {"héllo wörld": 1}

    def test_duplicate_anchors_counted(self, analyzer):
        links = [{"url": f"http://ext.com/{i}", "text": "same"} for i in range(3)]
        r = analyzer.analyze("http://example.com/", links)
        assert r.stats.anchor_text_distribution == {"same": 3}


# ── suspicious link detection ───────────────────────────────────────────


class TestSuspicious:
    def test_empty_anchor_suspicious(self, analyzer):
        r = analyzer.analyze("http://example.com/", [{"url": "http://ext.com/x", "text": ""}])
        assert r.suspicious_links == ["http://ext.com/x"]

    def test_generic_anchor_suspicious(self, analyzer):
        for generic in ["click here", "link", "here", "read more", "more", "this"]:
            r = analyzer.analyze("http://example.com/", [{"url": "http://ext.com/x", "text": generic}])
            assert r.suspicious_links == ["http://ext.com/x"], generic

    def test_generic_anchor_case_insensitive(self, analyzer):
        r = analyzer.analyze("http://example.com/", [{"url": "http://ext.com/x", "text": "Click Here"}])
        assert r.suspicious_links == ["http://ext.com/x"]

    def test_long_url_suspicious(self, analyzer):
        long_url = "http://ext.com/" + "a" * 500
        r = analyzer.analyze("http://example.com/", [{"url": long_url, "text": "ok anchor"}])
        assert long_url in r.suspicious_links

    def test_normal_link_not_suspicious(self, analyzer):
        r = analyzer.analyze("http://example.com/", [{"url": "http://ext.com/x", "text": "a good title"}])
        assert r.suspicious_links == []


# ── top-N vs distribution split ─────────────────────────────────────────


class TestTopNSplit:
    def test_top10_vs_dist20(self, analyzer):
        # 25 distinct external domains -> top_domains capped at 10,
        # domain_distribution capped at 20, unique_domains is the full 25.
        links = [{"url": f"http://d{i}.com/x", "text": f"t{i}"} for i in range(25)]
        r = analyzer.analyze("http://example.com/", links)
        assert len(r.top_domains) == 10
        assert len(r.stats.domain_distribution) == 20
        assert r.stats.unique_domains == 25

    def test_top_anchor_capped_at_10(self, analyzer):
        links = [{"url": f"http://ext.com/{i}", "text": f"anchor{i}"} for i in range(15)]
        r = analyzer.analyze("http://example.com/", links)
        assert len(r.top_anchor_texts) == 10


# ── idempotence / round-trip ────────────────────────────────────────────


class TestIdempotence:
    def test_analyze_idempotent(self, analyzer):
        links = [
            {"url": "http://example.com/a", "text": "i"},
            {"url": "http://ext.com/x", "text": "e"},
        ]
        r1 = analyzer.analyze("http://example.com/", links)
        r2 = analyzer.analyze("http://example.com/", links)
        assert r1.stats.total_links == r2.stats.total_links
        assert r1.stats.internal_links == r2.stats.internal_links
        assert r1.stats.external_links == r2.stats.external_links
        assert r1.stats.unique_domains == r2.stats.unique_domains
        assert r1.top_domains == r2.top_domains
        assert r1.suspicious_links == r2.suspicious_links


# ── analyze_batch / get_aggregate_stats ─────────────────────────────────


class TestBatchAndAggregate:
    def test_analyze_batch_empty(self, analyzer):
        assert analyzer.analyze_batch([]) == []

    def test_analyze_batch_missing_keys(self, analyzer):
        results = analyzer.analyze_batch([{}, {"url": "http://example.com/"}])
        assert len(results) == 2
        assert results[0].stats.total_links == 0

    def test_aggregate_empty(self, analyzer):
        agg = analyzer.get_aggregate_stats([])
        assert agg["pages_analyzed"] == 0
        assert agg["total_links"] == 0
        assert agg["unique_external_domains"] == 0
        assert agg["total_suspicious"] == 0

    def test_aggregate_sums(self, analyzer):
        pages = [
            {"url": "http://example.com/1", "links": [
                {"url": "http://example.com/a", "text": "i"},
                {"url": "http://a.com/x", "text": "e"},
            ]},
            {"url": "http://example.com/2", "links": [
                {"url": "http://b.com/x", "text": "e"},
                {"url": "http://a.com/y", "text": "e"},
            ]},
        ]
        results = analyzer.analyze_batch(pages)
        agg = analyzer.get_aggregate_stats(results)
        assert agg["pages_analyzed"] == 2
        assert agg["total_links"] == 4
        assert agg["internal_links"] == 1
        assert agg["external_links"] == 3
        # a.com and b.com are the two distinct external domains.
        assert agg["unique_external_domains"] == 2


# ── DEFECT QA-9: negative max_anchor_length corrupts anchor text ────────


class TestNegativeMaxAnchorLength:
    """QA-9: a negative max_anchor_length must clamp to a non-negative bound.

    The docstring says anchor text is "truncated to ``max_anchor_length``".
    A negative bound is out-of-range and must behave like 0 (anchor truncated
    to '' -> counted as '', consistent with max_anchor_length=0). Before the
    fix, ``a[:self.max_anchor_length]`` with a negative N dropped the last N
    characters, corrupting the anchor text.
    """

    def test_negative_max_anchor_length_clamped(self, analyzer):
        a = LinkAnalyzer(base_domain="example.com", max_anchor_length=-1)
        r = a.analyze("http://example.com/", [{"url": "http://ext.com/x", "text": "hello"}])
        # Clamped to 0 -> anchor truncated to '' -> counted as '' (same as max_anchor_length=0).
        assert r.stats.anchor_text_distribution == {"": 1}

    def test_negative_max_anchor_length_matches_zero(self, analyzer):
        neg = LinkAnalyzer(base_domain="example.com", max_anchor_length=-2)
        zero = LinkAnalyzer(base_domain="example.com", max_anchor_length=0)
        links = [{"url": "http://ext.com/x", "text": "hello world"}]
        assert neg.analyze("http://example.com/", links).stats.anchor_text_distribution == \
            zero.analyze("http://example.com/", links).stats.anchor_text_distribution


# ── DEFECT QA-10: aggregate undercounts unique_external_domains >20 ─────


class TestAggregateUniqueDomainsTruncation:
    """QA-10: get_aggregate_stats must not truncate the unique-domain count.

    The per-page ``stats.unique_domains`` is the full distinct count, but
    ``get_aggregate_stats`` derives ``unique_external_domains`` from the
    top-20-truncated ``domain_distribution`` keys, so a page with more than
    20 distinct external domains is undercounted.
    """

    def test_aggregate_unique_domains_not_truncated(self, analyzer):
        links = [{"url": f"http://d{i}.com/x", "text": "t"} for i in range(25)]
        r = analyzer.analyze("http://example.com/", links)
        agg = analyzer.get_aggregate_stats([r])
        # Expected: 25 distinct external domains, matching stats.unique_domains.
        assert agg["unique_external_domains"] == 25
        assert agg["unique_external_domains"] == r.stats.unique_domains

    def test_aggregate_matches_per_page_unique_domains(self, analyzer):
        links = [{"url": f"http://d{i}.com/x", "text": "t"} for i in range(50)]
        r = analyzer.analyze("http://example.com/", links)
        agg = analyzer.get_aggregate_stats([r])
        assert agg["unique_external_domains"] == r.stats.unique_domains == 50


# ── end-to-end through the installed CLI (status) ───────────────────────


class TestCliEndToEnd:
    def test_cli_status_runs(self, tmp_path):
        data_dir = str(tmp_path / "dd")
        run = subprocess.run(
            [sys.executable, "-m", "personal_index",
             "--data-dir", data_dir, "status"],
            capture_output=True, text=True,
        )
        assert run.returncode == 0, run.stderr
        assert "Pages" in run.stdout or "pages" in run.stdout.lower()
