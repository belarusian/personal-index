"""Adversarial deep tests for personal_index.stats (StatsCollector).

Complements tests/deep/test_stats_collector_adversarial.py (which covers the
basic None/empty/single/multi-page, interest-count, top-10-cap, and timestamp
contracts). This file pins the EDGE cases that file leaves open:

- no-domain URLs (extract_domain -> None) contribute to total_pages but NOT to
  unique_domains / top_domains
- duplicate interest names on a single page are counted per occurrence
- get_index_stats() is idempotent (repeated calls return equal IndexStats)
- avg_content_length is a true float (fractional, not truncated to int)
- port-stripped and unicode domains are normalized in top_domains
- format_index_stats() omits the "Top domains:" section when no page has a
  resolvable domain, and always emits Oldest/Newest (crawled_at defaults to an
  aware UTC timestamp)
- top_domains tie-break is stable (insertion order) for equal counts
- mixed-interest pages: only pages that actually matched an interest count

All pins are regression armor: they must PASS on current main.
"""

import tempfile
from datetime import datetime, timezone

from personal_index.models import CrawledPage
from personal_index.search_index import SearchIndex
from personal_index.stats import StatsCollector


def make_collector(pages=None):
    """Create a StatsCollector backed by a temp SearchIndex with optional pages."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        index_path = f.name
    index = SearchIndex(index_path=index_path)
    if pages:
        for url, page in pages.items():
            index.add(page)
    return StatsCollector(search_index=index)


class TestNoDomainUrls:
    """URLs with no resolvable domain count as pages but not as domains."""

    def test_no_domain_url_counts_page_not_domain(self):
        collector = make_collector(
            {"not-a-url": CrawledPage(url="not-a-url", content="hello")}
        )
        stats = collector.get_index_stats()
        assert stats.total_pages == 1
        assert stats.unique_domains == 0
        assert stats.top_domains == []

    def test_mixed_domain_and_no_domain(self):
        collector = make_collector(
            {
                "http://a.com/x": CrawledPage(url="http://a.com/x", content="one"),
                "mailto:x@y.com": CrawledPage(url="mailto:x@y.com", content="two"),
            }
        )
        stats = collector.get_index_stats()
        assert stats.total_pages == 2
        assert stats.unique_domains == 1
        assert stats.top_domains == [("a.com", 1)]

    def test_format_omits_top_domains_when_none_resolvable(self):
        collector = make_collector(
            {"not-a-url": CrawledPage(url="not-a-url", content="hello")}
        )
        output = collector.format_index_stats()
        assert "Total pages: 1" in output
        assert "Top domains:" not in output


class TestDuplicateInterest:
    """Duplicate interest names on one page are counted per occurrence."""

    def test_duplicate_interest_on_single_page(self):
        collector = make_collector(
            {
                "http://a.com": CrawledPage(
                    url="http://a.com",
                    content="hello",
                    matched_interests=["tech", "tech"],
                )
            }
        )
        stats = collector.get_index_stats()
        assert stats.pages_with_interests == 2
        assert stats.top_interests == [("tech", 2)]

    def test_mixed_interest_pages_only_matched_count(self):
        collector = make_collector(
            {
                "http://a.com": CrawledPage(
                    url="http://a.com", content="x", matched_interests=["tech"]
                ),
                "http://b.com": CrawledPage(url="http://b.com", content="y"),
            }
        )
        stats = collector.get_index_stats()
        assert stats.pages_with_interests == 1
        assert stats.top_interests == [("tech", 1)]


class TestIdempotence:
    """get_index_stats() is a pure read: repeated calls return equal results."""

    def test_repeated_calls_equal(self):
        collector = make_collector(
            {
                "http://a.com": CrawledPage(
                    url="http://a.com",
                    content="one two three",
                    matched_interests=["tech"],
                )
            }
        )
        first = collector.get_index_stats()
        second = collector.get_index_stats()
        assert first == second

    def test_format_idempotent(self):
        collector = make_collector(
            {"http://a.com": CrawledPage(url="http://a.com", content="one two")}
        )
        assert collector.format_index_stats() == collector.format_index_stats()


class TestAvgContentLength:
    """avg_content_length is a true float, not truncated to an integer."""

    def test_fractional_average(self):
        collector = make_collector(
            {
                "http://a.com": CrawledPage(url="http://a.com", content="abc"),
                "http://b.com": CrawledPage(url="http://b.com", content="abcd"),
            }
        )
        stats = collector.get_index_stats()
        # (3 + 4) / 2 = 3.5, a non-integer float
        assert stats.avg_content_length == 3.5
        assert isinstance(stats.avg_content_length, float)

    def test_empty_content_zero_average(self):
        collector = make_collector(
            {"http://a.com": CrawledPage(url="http://a.com", content="")}
        )
        stats = collector.get_index_stats()
        assert stats.avg_content_length == 0.0
        assert stats.total_words == 0


class TestDomainNormalization:
    """top_domains normalizes ports and preserves unicode domains."""

    def test_port_stripped_domain(self):
        collector = make_collector(
            {
                "http://example.com:8080/x": CrawledPage(
                    url="http://example.com:8080/x", content="x"
                )
            }
        )
        stats = collector.get_index_stats()
        assert stats.top_domains == [("example.com", 1)]

    def test_unicode_domain_preserved(self):
        collector = make_collector(
            {
                "http://exämple.com/x": CrawledPage(
                    url="http://exämple.com/x", content="x"
                )
            }
        )
        stats = collector.get_index_stats()
        assert stats.top_domains == [("exämple.com", 1)]


class TestTopDomainsTieBreak:
    """Equal-count domains keep a stable (insertion) order in top_domains."""

    def test_equal_counts_stable_insertion_order(self):
        collector = make_collector(
            {
                "http://z.com": CrawledPage(url="http://z.com", content="x"),
                "http://a.com": CrawledPage(url="http://a.com", content="x"),
            }
        )
        stats = collector.get_index_stats()
        # Both count 1; Python's stable sort preserves insertion order.
        assert stats.top_domains == [("z.com", 1), ("a.com", 1)]


class TestTimestampFormat:
    """crawled_at defaults to an aware UTC timestamp, so Oldest/Newest always
    appear in format_index_stats() for a non-empty index."""

    def test_format_always_has_oldest_and_newest(self):
        collector = make_collector(
            {"http://a.com": CrawledPage(url="http://a.com", content="x")}
        )
        output = collector.format_index_stats()
        assert "Oldest page:" in output
        assert "Newest page:" in output

    def test_explicit_timestamps_round_trip(self):
        ts1 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        ts2 = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        collector = make_collector(
            {
                "http://a.com": CrawledPage(url="http://a.com", content="x", crawled_at=ts1),
                "http://b.com": CrawledPage(url="http://b.com", content="y", crawled_at=ts2),
            }
        )
        stats = collector.get_index_stats()
        assert stats.oldest_page == ts1
        assert stats.newest_page == ts2


class TestUnicodeContent:
    """Unicode content is counted as words by whitespace split."""

    def test_single_unicode_word(self):
        collector = make_collector(
            {"http://a.com": CrawledPage(url="http://a.com", content="héllo")}
        )
        stats = collector.get_index_stats()
        assert stats.total_words == 1


class TestStatsCliEndToEnd:
    """End-to-end run through the installed CLI `stats` command."""

    def test_stats_cli_empty_data_dir(self, tmp_path):
        from click.testing import CliRunner

        from personal_index.cli import main

        runner = CliRunner()
        res = runner.invoke(main, ["stats", "--data-dir", str(tmp_path)])
        assert res.exit_code == 0, res.output
        assert "Personal Index Statistics" in res.output
        assert "indexed_pages:  0" in res.output
        assert "interests:      0" in res.output
        assert "tags:           0" in res.output

    def test_stats_cli_json_empty_data_dir(self, tmp_path):
        import json

        from click.testing import CliRunner

        from personal_index.cli import main

        runner = CliRunner()
        res = runner.invoke(
            main, ["stats", "--format", "json", "--data-dir", str(tmp_path)]
        )
        assert res.exit_code == 0, res.output
        payload = json.loads(res.output)
        assert payload["indexed_pages"] == 0
        assert payload["interests"] == 0
        assert payload["total_tags"] == 0
        assert payload["tagged_pages"] == 0
