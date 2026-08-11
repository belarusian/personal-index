"""Tests for individual pipeline stages and their interactions."""

from __future__ import annotations

import pytest

from personal_index.content_extractor import ContentExtractor, ExtractedContent
from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.content_scoring import ContentScorer, ContentScore, ScoreWeights
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest
from personal_index.tags import TagStore


class TestContentExtractor:
    """Test content extraction from HTML."""

    def test_extract_title(self):
        extractor = ContentExtractor()
        html = "<html><head><title>My Page</title></head><body></body></html>"
        result = extractor.extract(html)
        assert result.title == "My Page"

    def test_extract_og_title(self):
        extractor = ContentExtractor()
        html = '<html><head><meta property="og:title" content="OG Title"></head><body></body></html>'
        result = extractor.extract(html)
        assert result.title == "OG Title"

    def test_extract_text(self):
        extractor = ContentExtractor()
        html = "<html><body><p>Hello world</p><p>Second paragraph</p></body></html>"
        result = extractor.extract(html)
        assert "Hello world" in result.text
        assert "Second paragraph" in result.text

    def test_extract_removes_scripts(self):
        extractor = ContentExtractor()
        html = "<html><body><script>alert('xss')</script><p>Safe content</p></body></html>"
        result = extractor.extract(html)
        assert "alert" not in result.text
        assert "Safe content" in result.text

    def test_extract_headings(self):
        extractor = ContentExtractor()
        html = "<html><body><h1>Main</h1><h2>Sub</h2><p>Content</p></body></html>"
        result = extractor.extract(html)
        assert "Main" in result.headings
        assert "Sub" in result.headings

    def test_extract_links(self):
        extractor = ContentExtractor()
        html = '<html><body><a href="https://example.com">Link</a></body></html>'
        result = extractor.extract(html)
        assert len(result.links) == 1
        assert result.links[0] == ("Link", "https://example.com")

    def test_extract_empty(self):
        extractor = ContentExtractor()
        result = extractor.extract("")
        assert result.title == ""
        assert result.text == ""

    def test_extract_word_count(self):
        extractor = ContentExtractor()
        html = "<html><body><p>One two three four five</p></body></html>"
        result = extractor.extract(html)
        assert result.word_count == 5

    def test_extract_meta_description(self):
        extractor = ContentExtractor()
        html = '<html><head><meta name="description" content="Page description"></head><body></body></html>'
        result = extractor.extract(html)
        assert result.meta_description == "Page description"

    def test_extract_readability_score(self):
        extractor = ContentExtractor()
        html = "<html><head><title>T</title><meta name='description' content='desc'></head><body><h1>H</h1><p>" + "word " * 100 + "</p></body></html>"
        result = extractor.extract(html)
        score = extractor.extract_readability_score(result)
        assert 0.0 <= score <= 1.0


class TestContentFilter:
    """Test content filtering logic."""

    def test_filter_min_content_length(self):
        cfg = FilterConfig(min_content_length=50)
        f = ContentFilter(config=cfg)
        page = CrawledPage(url="https://x.com", title="T", content="Short")
        assert not f.should_include(page)

    def test_filter_max_content_length(self):
        cfg = FilterConfig(max_content_length=10)
        f = ContentFilter(config=cfg)
        page = CrawledPage(url="https://x.com", title="T", content="This is way too long content")
        assert not f.should_include(page)

    def test_filter_min_title_length(self):
        cfg = FilterConfig(min_title_length=5)
        f = ContentFilter(config=cfg)
        page = CrawledPage(url="https://x.com", title="Hi", content="Good content here that is long enough.")
        assert not f.should_include(page)

    def test_filter_blocked_domain(self):
        cfg = FilterConfig(blocked_domains=["spam.com"])
        f = ContentFilter(config=cfg)
        page = CrawledPage(url="https://spam.com/page", title="T", content="Good content here that is long enough.")
        assert not f.should_include(page)

    def test_filter_blocked_pattern(self):
        cfg = FilterConfig(blocked_patterns=["spam", "scam"])
        f = ContentFilter(config=cfg)
        page = CrawledPage(url="https://x.com", title="T", content="This is spam content that should be blocked.")
        assert not f.should_include(page)

    def test_filter_required_pattern(self):
        cfg = FilterConfig(required_patterns=["required"], min_content_length=10)
        f = ContentFilter(config=cfg)
        page = CrawledPage(url="https://x.com", title="Test", content="This has the required word in it.")
        assert f.should_include(page)

    def test_filter_interest_match(self, tmp_path):
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"]))
        cfg = FilterConfig(min_content_length=10, require_interest_match=True)
        f = ContentFilter(config=cfg, interest_store=store)

        matching = CrawledPage(url="https://x.com", title="Test", content="Python is great.")
        assert f.should_include(matching)

        non_matching = CrawledPage(url="https://x.com", title="Test", content="No programming language mentioned here at all whatsoever.")
        assert not f.should_include(non_matching)

    def test_filter_get_reasons(self):
        cfg = FilterConfig(min_content_length=50)
        f = ContentFilter(config=cfg)
        page = CrawledPage(url="https://x.com", title="T", content="Short")
        reasons = f.get_filter_reasons(page)
        assert len(reasons) > 0
        assert any("content length" in r for r in reasons)

    def test_filter_passes_all(self):
        cfg = FilterConfig(min_content_length=10, require_interest_match=False)
        f = ContentFilter(config=cfg)
        page = CrawledPage(url="https://x.com", title="Test Title", content="This is good content that passes all filters.")
        assert f.should_include(page)


class TestContentScorer:
    """Test content scoring logic."""

    def test_scorer_basic(self):
        scorer = ContentScorer()
        result = scorer.score(
            keyword_matches=5,
            total_keywords=10,
            word_count=500,
            domain_authority=0.8,
        )
        assert 0.0 <= result.total <= 1.0
        assert result.relevance > 0

    def test_scorer_no_matches(self):
        scorer = ContentScorer()
        result = scorer.score(
            keyword_matches=0,
            total_keywords=10,
            word_count=500,
            domain_authority=0.1,
        )
        assert result.relevance == 0.0

    def test_scorer_all_matches(self):
        scorer = ContentScorer()
        result = scorer.score(
            keyword_matches=10,
            total_keywords=10,
            word_count=1000,
            domain_authority=1.0,
        )
        assert result.relevance == 1.0

    def test_scorer_quality(self):
        scorer = ContentScorer()
        result = scorer.score(
            keyword_matches=5,
            total_keywords=10,
            word_count=5000,
            domain_authority=0.5,
        )
        assert result.quality > 0

    def test_scorer_custom_weights(self):
        weights = ScoreWeights(
            recency=0.1,
            relevance=0.5,
            engagement=0.1,
            quality=0.2,
            authority=0.1,
            freshness=0.0,
        )
        scorer = ContentScorer(weights=weights)
        result = scorer.score(
            keyword_matches=5,
            total_keywords=10,
            word_count=500,
            domain_authority=0.8,
        )
        assert 0.0 <= result.total <= 1.0

    def test_scorer_rank(self):
        scorer = ContentScorer()
        items = [
            {"keyword_matches": 5, "total_keywords": 10, "word_count": 500, "domain_authority": 0.8},
            {"keyword_matches": 2, "total_keywords": 10, "word_count": 200, "domain_authority": 0.3},
            {"keyword_matches": 8, "total_keywords": 10, "word_count": 1000, "domain_authority": 0.9},
        ]
        ranked = scorer.rank(items, limit=2)
        assert len(ranked) == 2
        assert ranked[0][0]["keyword_matches"] == 8  # Highest score first


class TestTagStore:
    """Test tag store operations."""

    def test_create_tag(self, tmp_path):
        store = TagStore(store_path=str(tmp_path / "tags.json"))
        store.create_tag("python", color="#3572A5")
        tags = store.list_tags()
        assert len(tags) == 1
        assert tags[0].name == "python"

    def test_add_tag_to_page(self, tmp_path):
        store = TagStore(store_path=str(tmp_path / "tags.json"))
        store.create_tag("python", color="#3572A5")
        store.add_tag_to_page("https://example.com", "python")
        tags = store.get_tags_for_page("https://example.com")
        assert any(t.name == "python" for t in tags)

    def test_get_pages_for_tag(self, tmp_path):
        store = TagStore(store_path=str(tmp_path / "tags.json"))
        store.create_tag("python", color="#3572A5")
        store.add_tag_to_page("https://a.com", "python")
        store.add_tag_to_page("https://b.com", "python")
        pages = store.get_pages_for_tag("python")
        assert "https://a.com" in pages
        assert "https://b.com" in pages

    def test_tag_count(self, tmp_path):
        store = TagStore(store_path=str(tmp_path / "tags.json"))
        store.create_tag("a", color="#fff")
        store.create_tag("b", color="#000")
        assert store.get_tag_count() == 2

    def test_tagged_page_count(self, tmp_path):
        store = TagStore(store_path=str(tmp_path / "tags.json"))
        store.create_tag("a", color="#fff")
        store.add_tag_to_page("https://a.com", "a")
        assert store.get_tagged_page_count() == 1

    def test_persistence(self, tmp_path):
        path = str(tmp_path / "tags.json")
        store1 = TagStore(store_path=path)
        store1.create_tag("persist", color="#fff")
        store1.add_tag_to_page("https://x.com", "persist")

        store2 = TagStore(store_path=path)
        tags = store2.get_tags_for_page("https://x.com")
        assert any(t.name == "persist" for t in tags)


class TestInterestStore:
    """Test interest store operations."""

    def test_add_interest(self, tmp_path):
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"]))
        interests = store.list_all()
        assert len(interests) == 1

    def test_remove_interest(self, tmp_path):
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"]))
        store.remove("python")
        assert len(store.list_all()) == 0

    def test_matches_any(self, tmp_path):
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"]))
        matches = store.matches_any("I love Python", "")
        assert len(matches) == 1

    def test_total_score(self, tmp_path):
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"]))
        score = store.total_score("Python Python Python")
        assert score > 0

    def test_persistence(self, tmp_path):
        path = str(tmp_path / "interests.json")
        store1 = InterestStore(store_path=path)
        store1.add(Interest(name="persist", keywords=["test"]))

        store2 = InterestStore(store_path=path)
        interests = store2.list_all()
        assert any(i.name == "persist" for i in interests)
