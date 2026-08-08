"""Tests for the content filter module."""

import pytest
from personal_index.interests import Interest, InterestManager
from personal_index.index import Document
from personal_index.filter import FilterConfig, ContentFilter


@pytest.fixture
def interest_manager():
    mgr = InterestManager()
    mgr.add_interest(Interest(name="python", keywords=["python"]))
    mgr.add_interest(Interest(name="web", keywords=["web", "html"]))
    return mgr


@pytest.fixture
def filter_with_interests(interest_manager):
    config = FilterConfig(min_content_length=10, min_title_length=2)
    return ContentFilter(interest_manager, config)


@pytest.fixture
def filter_no_interests():
    return ContentFilter(InterestManager())


class TestFilterConfig:
    def test_default_config(self):
        config = FilterConfig()
        assert config.min_content_length == 100
        assert config.min_title_length == 3
        assert '.jpg' in config.blocked_extensions

    def test_custom_config(self):
        config = FilterConfig(min_content_length=50, require_interest_match=False)
        assert config.min_content_length == 50
        assert config.require_interest_match is False


class TestContentFilter:
    def test_blocked_extension(self, filter_no_interests):
        doc = Document(url="https://example.com/image.jpg", title="Image", content="x" * 200)
        assert filter_no_interests.should_filter(doc) is True

    def test_blocked_pdf(self, filter_no_interests):
        doc = Document(url="https://example.com/doc.pdf", title="PDF", content="x" * 200)
        assert filter_no_interests.should_filter(doc) is True

    def test_allowed_extension(self, filter_no_interests):
        doc = Document(url="https://example.com/page.html", title="Page", content="x" * 200)
        assert filter_no_interests.should_filter(doc) is False

    def test_blocked_content_type(self, filter_no_interests):
        doc = Document(
            url="https://example.com/page",
            title="Page",
            content="x" * 200,
            metadata={"content_type": "image/png"},
        )
        assert filter_no_interests.should_filter(doc) is True

    def test_allowed_content_type(self, filter_no_interests):
        doc = Document(
            url="https://example.com/page",
            title="Page",
            content="x" * 200,
            metadata={"content_type": "text/html"},
        )
        assert filter_no_interests.should_filter(doc) is False

    def test_too_short_content(self, filter_no_interests):
        doc = Document(url="https://example.com/page", title="Page", content="short")
        assert filter_no_interests.should_filter(doc) is True

    def test_too_short_title(self, filter_with_interests):
        doc = Document(url="https://example.com/page", title="A", content="python " * 50)
        assert filter_with_interests.should_filter(doc) is True

    def test_too_long_content(self, filter_no_interests):
        doc = Document(
            url="https://example.com/page",
            title="Page",
            content="x" * 2_000_000,
        )
        assert filter_no_interests.should_filter(doc) is True

    def test_interest_match_pass(self, filter_with_interests):
        doc = Document(
            url="https://example.com/page",
            title="Python Guide",
            content="Learn python programming basics",
        )
        assert filter_with_interests.should_filter(doc) is False

    def test_interest_match_fail(self, filter_with_interests):
        doc = Document(
            url="https://example.com/page",
            title="Cooking",
            content="How to make pasta and sauce",
        )
        assert filter_with_interests.should_filter(doc) is True

    def test_no_interests_accept_all(self, filter_no_interests):
        doc = Document(
            url="https://example.com/page",
            title="Anything",
            content="x" * 200,
        )
        assert filter_no_interests.should_filter(doc) is False

    def test_url_pattern_match(self):
        mgr = InterestManager()
        mgr.add_interest(Interest(name="docs", url_patterns=[r"docs\.example\.com"]))
        f = ContentFilter(mgr, FilterConfig(min_content_length=10, min_title_length=2))
        doc = Document(url="https://docs.example.com/api", title="API", content="docs here now")
        assert f.should_filter(doc) is False

    def test_get_matching_interests(self, filter_with_interests):
        doc = Document(
            url="https://example.com/page",
            title="Python Web",
            content="python and web development",
        )
        matches = filter_with_interests.get_matching_interests(doc)
        assert "python" in matches
        assert "web" in matches

    def test_filter_documents(self, filter_with_interests):
        docs = [
            Document(url="https://a.com", title="Python", content="python code"),
            Document(url="https://b.com", title="Cooking", content="pasta recipe"),
            Document(url="https://c.com", title="Web", content="html web page"),
        ]
        filtered = filter_with_interests.filter_documents(docs)
        assert len(filtered) == 2
        assert filtered[0].url == "https://a.com"
        assert filtered[1].url == "https://c.com"

    def test_query_string_does_not_block(self, filter_no_interests):
        doc = Document(
            url="https://example.com/page.html?download=true",
            title="Page",
            content="x" * 200,
        )
        assert filter_no_interests.should_filter(doc) is False
