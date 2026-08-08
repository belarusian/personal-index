"""Tests for link analyzer module."""

import pytest
from personal_index.link_analyzer import LinkAnalyzer, LinkStats, LinkAnalysisResult


class TestLinkAnalyzer:
    def _make_links(self, *urls_and_texts):
        links = []
        for i in range(0, len(urls_and_texts), 2):
            links.append({"url": urls_and_texts[i], "text": urls_and_texts[i + 1]})
        return links

    def test_analyze_empty(self):
        analyzer = LinkAnalyzer()
        result = analyzer.analyze("http://example.com", [])
        assert result.stats.total_links == 0
        assert result.stats.internal_links == 0
        assert result.stats.external_links == 0

    def test_analyze_external_links(self):
        analyzer = LinkAnalyzer(base_domain="example.com")
        links = self._make_links(
            "http://other.com/page", "Other Site",
            "http://another.com", "Another",
        )
        result = analyzer.analyze("http://example.com", links)
        assert result.stats.total_links == 2
        assert result.stats.external_links == 2
        assert result.stats.internal_links == 0
        assert result.stats.unique_domains == 2

    def test_analyze_internal_links(self):
        analyzer = LinkAnalyzer(base_domain="example.com")
        links = self._make_links(
            "http://example.com/page1", "Page 1",
            "http://example.com/page2", "Page 2",
        )
        result = analyzer.analyze("http://example.com", links)
        assert result.stats.internal_links == 2
        assert result.stats.external_links == 0

    def test_mixed_links(self):
        analyzer = LinkAnalyzer(base_domain="example.com")
        links = self._make_links(
            "http://example.com/internal", "Internal",
            "http://other.com/external", "External",
        )
        result = analyzer.analyze("http://example.com", links)
        assert result.stats.internal_links == 1
        assert result.stats.external_links == 1

    def test_anchor_text_tracking(self):
        analyzer = LinkAnalyzer()
        links = self._make_links(
            "http://a.com", "Click here",
            "http://b.com", "Click here",
            "http://c.com", "Other text",
        )
        result = analyzer.analyze("http://example.com", links)
        assert result.stats.anchor_text_distribution.get("Click here") == 2

    def test_top_anchor_texts(self):
        analyzer = LinkAnalyzer()
        links = self._make_links(
            "http://a.com", "Link A",
            "http://b.com", "Link B",
        )
        result = analyzer.analyze("http://example.com", links)
        assert len(result.top_anchor_texts) == 2

    def test_suspicious_empty_anchor(self):
        analyzer = LinkAnalyzer()
        links = [{"url": "http://example.com", "text": ""}]
        result = analyzer.analyze("http://example.com", links)
        assert len(result.suspicious_links) == 1

    def test_suspicious_generic_anchor(self):
        analyzer = LinkAnalyzer()
        links = [{"url": "http://example.com", "text": "click here"}]
        result = analyzer.analyze("http://example.com", links)
        assert len(result.suspicious_links) == 1

    def test_suspicious_long_url(self):
        analyzer = LinkAnalyzer()
        long_url = "http://example.com/" + "a" * 500
        links = [{"url": long_url, "text": "Normal text"}]
        result = analyzer.analyze("http://example.com", links)
        assert len(result.suspicious_links) == 1

    def test_domain_distribution(self):
        analyzer = LinkAnalyzer(base_domain="example.com")
        links = self._make_links(
            "http://a.com/1", "A1",
            "http://a.com/2", "A2",
            "http://b.com", "B",
        )
        result = analyzer.analyze("http://example.com", links)
        assert result.stats.domain_distribution.get("a.com") == 2
        assert result.stats.domain_distribution.get("b.com") == 1

    def test_analyze_batch(self):
        analyzer = LinkAnalyzer(base_domain="example.com")
        pages = [
            {"url": "http://example.com/1", "links": self._make_links("http://other.com", "O")},
            {"url": "http://example.com/2", "links": self._make_links("http://other.com", "O")},
        ]
        results = analyzer.analyze_batch(pages)
        assert len(results) == 2

    def test_aggregate_stats(self):
        analyzer = LinkAnalyzer(base_domain="example.com")
        pages = [
            {"url": "http://example.com/1", "links": self._make_links("http://other.com", "O")},
            {"url": "http://example.com/2", "links": self._make_links("http://other.com", "O")},
        ]
        results = analyzer.analyze_batch(pages)
        agg = analyzer.get_aggregate_stats(results)
        assert agg["pages_analyzed"] == 2
        assert agg["total_links"] == 2
        assert agg["external_links"] == 2

    def test_no_base_domain_all_external(self):
        analyzer = LinkAnalyzer()
        links = self._make_links("http://example.com", "Home")
        result = analyzer.analyze("http://example.com", links)
        assert result.stats.external_links == 1
        assert result.stats.internal_links == 0

    def test_anchor_text_truncation(self):
        analyzer = LinkAnalyzer(max_anchor_length=5)
        links = [{"url": "http://example.com", "text": "Very long anchor text"}]
        result = analyzer.analyze("http://example.com", links)
        assert "Very " in result.stats.anchor_text_distribution
