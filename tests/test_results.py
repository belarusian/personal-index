"""Tests for personal_index.results."""

import pytest

from personal_index.models import CrawledPage
from personal_index.results import (
    ResultsExporter,
    ResultsFormatter,
    SearchResult,
    search_and_format,
)
from personal_index.search_index import SearchIndex


@pytest.fixture
def formatter():
    return ResultsFormatter(max_snippet_length=100)


@pytest.fixture
def sample_result():
    return SearchResult(
        rank=1,
        url="https://example.com",
        title="Test Page",
        score=5.5,
        snippet="This is a test snippet",
        matched_interests=["Python", "ML"],
        meta_description="A test page",
    )


class TestSearchResult:
    """Tests for SearchResult."""

    def test_create_result(self, sample_result):
        assert sample_result.rank == 1
        assert sample_result.url == "https://example.com"
        assert sample_result.title == "Test Page"
        assert sample_result.score == 5.5
        assert sample_result.matched_interests == ["Python", "ML"]

    def test_default_interests(self):
        result = SearchResult(
            rank=1,
            url="https://example.com",
            title="Test",
            score=1.0,
        )
        assert result.matched_interests == []


class TestResultsFormatter:
    """Tests for ResultsFormatter."""

    def test_format_result(self, formatter, sample_result):
        output = formatter.format_result(sample_result)
        assert "[1] Test Page" in output
        assert "https://example.com" in output
        assert "Score: 5.50" in output
        assert "Python, ML" in output

    def test_format_results(self, formatter, sample_result):
        results = [sample_result]
        output = formatter.format_results(results)
        assert "Test Page" in output
        assert "-" * 60 in output

    def test_format_empty_results(self, formatter):
        output = formatter.format_results([])
        assert output == "No results found."

    def test_create_snippet_match(self, formatter):
        text = "This is some text about python programming"
        snippet = formatter.create_snippet(text, "python")
        assert "python" in snippet

    def test_create_snippet_no_match(self, formatter):
        text = "This is some text about java"
        snippet = formatter.create_snippet(text, "python")
        assert snippet == "This is some text about java"

    def test_create_snippet_empty(self, formatter):
        snippet = formatter.create_snippet("", "python")
        assert snippet == ""

    def test_create_snippet_truncated(self, formatter):
        text = "a" * 500
        snippet = formatter.create_snippet(text, "a")
        assert len(snippet) <= 250  # max_length + ellipsis


class TestResultsExporter:
    """Tests for ResultsExporter."""

    def test_to_json(self, sample_result):
        results = [sample_result]
        output = ResultsExporter.to_json(results)
        assert '"rank": 1' in output
        assert '"url": "https://example.com"' in output

    def test_to_csv(self, sample_result):
        results = [sample_result]
        output = ResultsExporter.to_csv(results)
        assert "rank,url,title,score,snippet,interests" in output
        assert "1,https://example.com,Test Page" in output

    def test_to_markdown(self, sample_result):
        results = [sample_result]
        output = ResultsExporter.to_markdown(results)
        assert "## 1. Test Page" in output
        assert "**URL**: https://example.com" in output


class TestSearchAndFormat:
    """Tests for search_and_format."""

    def test_search_and_format(self, tmp_path):
        index = SearchIndex(index_path=str(tmp_path / "index.json"))
        index.add(CrawledPage(
            url="https://example.com",
            title="Python Guide",
            content="Python is a great language",
            matched_interests=["Python"],
        ))

        results = search_and_format(index, "python", show_snippets=True)
        assert len(results) == 1
        assert results[0].title == "Python Guide"
        assert "Python" in results[0].matched_interests

    def test_search_and_format_empty(self, tmp_path):
        index = SearchIndex(index_path=str(tmp_path / "index.json"))
        results = search_and_format(index, "python")
        assert results == []
