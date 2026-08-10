"""Tests for data models."""

import pytest
from personal_index.models import Interest, CrawlConfig, IndexedPage, SearchResult


class TestInterest:
    def test_create_interest_with_name_only(self):
        interest = Interest(name="python")
        assert interest.name == "python"
        assert interest.keywords == []
        assert interest.url_patterns == []
        assert interest.enabled is True

    def test_create_interest_with_keywords(self):
        interest = Interest(name="python", keywords=["python", "programming"])
        assert interest.keywords == ["python", "programming"]

    def test_create_interest_with_url_patterns(self):
        interest = Interest(name="python", url_patterns=["*.python.org"])
        assert interest.url_patterns == ["*.python.org"]

    def test_interest_to_dict(self):
        interest = Interest(name="python", keywords=["python"])
        d = interest.to_dict()
        assert d["name"] == "python"
        assert d["keywords"] == ["python"]

    def test_interest_from_dict(self):
        data = {"name": "python", "keywords": ["python"], "url_patterns": [], "topics": [], "enabled": True}
        interest = Interest.from_dict(data)
        assert interest.name == "python"
        assert interest.keywords == ["python"]

    def test_interest_roundtrip(self):
        interest = Interest(name="python", keywords=["python", "dev"], enabled=False)
        d = interest.to_dict()
        restored = Interest.from_dict(d)
        assert restored.name == interest.name
        assert restored.keywords == interest.keywords
        assert restored.enabled == interest.enabled


class TestCrawlConfig:
    def test_default_config(self):
        config = CrawlConfig()
        assert config.max_depth == 3
        assert config.politeness_delay == 1.0
        assert config.rate_limit == 10
        assert config.respect_robots_txt is True

    def test_custom_config(self):
        config = CrawlConfig(max_depth=5, politeness_delay=2.0)
        assert config.max_depth == 5
        assert config.politeness_delay == 2.0

    def test_config_to_dict(self):
        config = CrawlConfig(max_depth=5)
        d = config.to_dict()
        assert d["max_depth"] == 5

    def test_config_from_dict(self):
        data = {"max_depth": 5, "politeness_delay": 2.0, "rate_limit": 10,
                "max_pages_per_domain": 100, "timeout": 30,
                "user_agent": "test", "respect_robots_txt": True,
                "allowed_domains": [], "blocked_domains": []}
        config = CrawlConfig.from_dict(data)
        assert config.max_depth == 5
        assert config.politeness_delay == 2.0


class TestIndexedPage:
    def test_create_page(self):
        page = IndexedPage(url="https://example.com")
        assert page.url == "https://example.com"
        assert page.title == ""
        assert page.status_code == 200

    def test_page_with_content(self):
        page = IndexedPage(url="https://example.com", title="Test", content="Hello")
        assert page.title == "Test"
        assert page.content == "Hello"

    def test_page_to_dict(self):
        page = IndexedPage(url="https://example.com", title="Test")
        d = page.to_dict()
        assert d["url"] == "https://example.com"
        assert d["title"] == "Test"

    def test_page_from_dict(self):
        data = {"url": "https://example.com", "title": "Test", "content": "Hello",
                "keywords": [], "matched_interests": [], "domain": "",
                "status_code": 200, "content_length": 0, "language": "en"}
        page = IndexedPage.from_dict(data)
        assert page.url == "https://example.com"
        assert page.title == "Test"


class TestSearchResult:
    def test_create_result(self):
        page = IndexedPage(url="https://example.com", title="Test")
        result = SearchResult(url=page.url, title=page.title, relevance_score=0.95)
        assert result.relevance_score == 0.95
        assert result.url == "https://example.com"

    def test_result_to_dict(self):
        page = IndexedPage(url="https://example.com")
        result = SearchResult(url=page.url, title=page.title, relevance_score=0.5, matched_terms=["test"])
        d = result.to_dict()
        assert d["relevance_score"] == 0.5
        assert d["matched_terms"] == ["test"]
        assert d["url"] == "https://example.com"
