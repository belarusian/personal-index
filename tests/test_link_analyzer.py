"""Tests for link analysis."""

from __future__ import annotations

import pytest

from personal_index.link_analyzer import (
    LinkAnalyzer,
    LinkAnalysisResult,
    LinkInfo,
)


class TestLinkInfo:
    """Tests for LinkInfo dataclass."""

    def test_create_link(self):
        l = LinkInfo(url="http://example.com/page")
        assert l.url == "http://example.com/page"
        assert l.domain == "example.com"
        assert l.path == "/page"

    def test_anchor_link(self):
        l = LinkInfo(url="#section", is_anchor=True)
        assert l.is_anchor is True

    def test_mailto_link(self):
        l = LinkInfo(url="mailto:test@example.com", is_mailto=True)
        assert l.is_mailto is True

    def test_to_dict(self):
        l = LinkInfo(url="http://example.com", text="Example")
        d = l.to_dict()
        assert d["url"] == "http://example.com"
        assert d["text"] == "Example"


class TestLinkAnalyzer:
    """Tests for LinkAnalyzer class."""

    def test_analyze_empty(self):
        analyzer = LinkAnalyzer()
        result = analyzer.analyze("")
        assert result.total_links == 0

    def test_analyze_single_link(self):
        analyzer = LinkAnalyzer(base_url="http://example.com")
        html = '<a href="/page">Page Link</a>'
        result = analyzer.analyze(html)
        assert result.total_links == 1
        assert result.internal_links == 1

    def test_analyze_external_link(self):
        analyzer = LinkAnalyzer(base_url="http://example.com")
        html = '<a href="http://other.com/page">External</a>'
        result = analyzer.analyze(html)
        assert result.external_links == 1
        assert result.unique_domains == 1

    def test_analyze_anchor_link(self):
        analyzer = LinkAnalyzer()
        html = '<a href="#section">Section</a>'
        result = analyzer.analyze(html)
        assert result.anchor_links == 1

    def test_analyze_mailto_link(self):
        analyzer = LinkAnalyzer()
        html = '<a href="mailto:test@example.com">Email</a>'
        result = analyzer.analyze(html)
        assert result.mailto_links == 1

    def test_analyze_mixed_links(self):
        analyzer = LinkAnalyzer(base_url="http://example.com")
        html = (
            '<a href="/page1">Internal 1</a>'
            '<a href="http://other.com">External</a>'
            '<a href="#top">Top</a>'
            '<a href="mailto:a@b.com">Email</a>'
        )
        result = analyzer.analyze(html)
        assert result.total_links == 4
        assert result.internal_links == 1
        assert result.external_links == 1
        assert result.anchor_links == 1
        assert result.mailto_links == 1

    def test_extract_links(self):
        analyzer = LinkAnalyzer()
        html = '<a href="http://a.com">A</a><a href="http://b.com">B</a>'
        links = analyzer.extract_links(html)
        assert "http://a.com" in links
        assert "http://b.com" in links

    def test_get_external_links(self):
        analyzer = LinkAnalyzer(base_url="http://example.com")
        html = '<a href="/page">Internal</a><a href="http://other.com">External</a>'
        links = analyzer.get_external_links(html)
        assert links == ["http://other.com"]

    def test_get_internal_links(self):
        analyzer = LinkAnalyzer(base_url="http://example.com")
        html = '<a href="/page">Internal</a><a href="http://other.com">External</a>'
        links = analyzer.get_internal_links(html)
        assert "/page" in links or "http://example.com/page" in links

    def test_get_link_text_pairs(self):
        analyzer = LinkAnalyzer()
        html = '<a href="http://a.com">Link A</a>'
        pairs = analyzer.get_link_text_pairs(html)
        assert ("http://a.com", "Link A") in pairs

    def test_duplicate_links_removed(self):
        analyzer = LinkAnalyzer()
        html = '<a href="http://a.com">A</a><a href="http://a.com">A again</a>'
        links = analyzer.extract_links(html)
        assert len(links) == 1

    def test_broken_patterns_empty_anchor(self):
        analyzer = LinkAnalyzer()
        html = '<a href="#">Click</a>'
        result = analyzer.analyze(html)
        assert any("Empty anchor" in p for p in result.broken_patterns)

    def test_broken_patterns_javascript(self):
        analyzer = LinkAnalyzer()
        html = '<a href="javascript:void(0)">Click</a>'
        result = analyzer.analyze(html)
        assert any("JavaScript void" in p for p in result.broken_patterns)

    def test_domain_counts(self):
        analyzer = LinkAnalyzer(base_url="http://example.com")
        html = (
            '<a href="http://a.com/page1">A1</a>'
            '<a href="http://a.com/page2">A2</a>'
            '<a href="http://b.com/page1">B1</a>'
        )
        result = analyzer.analyze(html)
        assert result.domain_counts.get("a.com", 0) == 2
        assert result.domain_counts.get("b.com", 0) == 1

    def test_top_anchor_texts(self):
        analyzer = LinkAnalyzer()
        html = (
            '<a href="http://a.com">Click here</a>'
            '<a href="http://b.com">Click here</a>'
            '<a href="http://c.com">Other text</a>'
        )
        result = analyzer.analyze(html)
        assert len(result.top_anchor_texts) > 0
        assert result.top_anchor_texts[0][0] == "Click here"
        assert result.top_anchor_texts[0][1] == 2

    def test_to_dict(self):
        analyzer = LinkAnalyzer()
        result = analyzer.analyze('<a href="http://a.com">A</a>')
        d = result.to_dict()
        assert d["total_links"] == 1
        assert "domain_counts" in d

    def test_relative_url_resolution(self):
        analyzer = LinkAnalyzer(base_url="http://example.com/dir/")
        html = '<a href="page.html">Page</a>'
        links = analyzer.extract_links(html)
        assert "http://example.com/dir/page.html" in links

    def test_protocol_relative_url(self):
        analyzer = LinkAnalyzer()
        html = '<a href="//cdn.example.com/script.js">CDN</a>'
        result = analyzer.analyze(html)
        assert any("Protocol-relative" in p for p in result.broken_patterns)

    def test_file_protocol_detection(self):
        analyzer = LinkAnalyzer()
        html = '<a href="file:///etc/passwd">Local</a>'
        result = analyzer.analyze(html)
        assert any("File protocol" in p for p in result.broken_patterns)
