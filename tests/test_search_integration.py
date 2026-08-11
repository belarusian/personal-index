"""Integration tests for search functionality."""

from __future__ import annotations

import json
import os
import tempfile

import pytest
from click.testing import CliRunner

from personal_index.cli import main
from personal_index.index import SearchIndex
from personal_index.models import CrawledPage


class TestSearchIntegration:
    """Test search integration with real components."""

    def test_search_text_format(self, tmp_path, monkeypatch):
        """Test search with text output format."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        # Import content
        article = tmp_path / "article.txt"
        article.write_text("Python is a great programming language for web development.")
        runner.invoke(main, ["import", str(article)])

        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0
        assert "Python" in result.output

    def test_search_json_format(self, tmp_path, monkeypatch):
        """Test search with JSON output format."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        article = tmp_path / "article.txt"
        article.write_text("Python programming tutorial for web development.")
        runner.invoke(main, ["import", str(article)])

        result = runner.invoke(main, ["search", "python", "-f", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_search_json_format_output(self, tmp_path, monkeypatch):
        """Test search JSON format output structure."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        article = tmp_path / "article.txt"
        article.write_text("Python programming tutorial.")
        runner.invoke(main, ["import", str(article)])

        result = runner.invoke(main, ["search", "python", "-f", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "title" in data[0]

    def test_search_limit(self, tmp_path, monkeypatch):
        """Test search with result limit."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        # Import multiple articles
        for i in range(5):
            article = tmp_path / f"article{i}.txt"
            article.write_text(f"Python article {i}: programming language tutorial.")
            runner.invoke(main, ["import", str(article)])

        result = runner.invoke(main, ["search", "python", "--limit", "2"])
        assert result.exit_code == 0

    def test_search_empty_index(self, tmp_path, monkeypatch):
        """Test search on empty index."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        result = runner.invoke(main, ["search", "nonexistent"])
        assert result.exit_code == 0

    def test_search_multiple_terms(self, tmp_path, monkeypatch):
        """Test search with multiple terms."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        article = tmp_path / "article.txt"
        article.write_text("Python and JavaScript are popular programming languages for web development.")
        runner.invoke(main, ["import", str(article)])

        result = runner.invoke(main, ["search", "python javascript"])
        assert result.exit_code == 0

    def test_search_case_insensitive(self, tmp_path, monkeypatch):
        """Test that search is case-insensitive."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        article = tmp_path / "article.txt"
        article.write_text("Python programming language.")
        runner.invoke(main, ["import", str(article)])

        # Search with different cases
        result = runner.invoke(main, ["search", "PYTHON"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["search", "Python"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0


class TestSearchIndexDirect:
    """Test SearchIndex directly."""

    def test_add_and_search(self, tmp_path):
        """Test adding pages and searching."""
        db_path = str(tmp_path / "index.json")
        index = SearchIndex(db_path=db_path)

        pages = [
            CrawledPage(url="https://a.com", title="Python Guide", content="Python is great."),
            CrawledPage(url="https://b.com", title="Rust Guide", content="Rust is safe."),
            CrawledPage(url="https://c.com", title="Go Guide", content="Go is fast."),
        ]
        for page in pages:
            index.add_page(page)

        results = index.search("python")
        assert len(results) == 1
        assert results[0].url == "https://a.com"

    def test_search_ranking(self, tmp_path):
        """Test that search results are ranked by relevance."""
        db_path = str(tmp_path / "index.json")
        index = SearchIndex(db_path=db_path)

        # Page with more keyword matches should rank higher
        index.add_page(CrawledPage(
            url="https://a.com", title="Python", content="Python Python Python"
        ))
        index.add_page(CrawledPage(
            url="https://b.com", title="Other", content="Python is mentioned once"
        ))

        results = index.search("python")
        assert len(results) == 2
        assert results[0].url == "https://a.com"  # Higher score

    def test_search_persistence(self, tmp_path):
        """Test that search index persists to disk."""
        db_path = str(tmp_path / "index.json")

        # Create and save
        index1 = SearchIndex(db_path=db_path)
        index1.add_page(CrawledPage(
            url="https://persist.com", title="Persistent", content="This persists"
        ))
        index1.close()

        # Reload
        index2 = SearchIndex(db_path=db_path)
        results = index2.search("persists")
        assert len(results) == 1

    def test_search_remove(self, tmp_path):
        """Test removing pages from index."""
        db_path = str(tmp_path / "index.json")
        index = SearchIndex(db_path=db_path)

        index.add_page(CrawledPage(
            url="https://remove.com", title="Remove Me", content="Remove this page"
        ))
        assert index.get_page_count() == 1

        index.remove_page("https://remove.com")
        assert index.get_page_count() == 0

        results = index.search("remove")
        assert len(results) == 0

    def test_search_clear(self, tmp_path):
        """Test clearing the entire index."""
        db_path = str(tmp_path / "index.json")
        index = SearchIndex(db_path=db_path)

        for i in range(5):
            index.add_page(CrawledPage(
                url=f"https://example.com/{i}", title=f"Page {i}", content=f"Content {i}"
            ))

        assert index.get_page_count() == 5
        index.clear()
        assert index.get_page_count() == 0

    def test_search_snippet_generation(self, tmp_path):
        """Test that search snippets are generated correctly."""
        db_path = str(tmp_path / "index.json")
        index = SearchIndex(db_path=db_path)

        index.add_page(CrawledPage(
            url="https://example.com",
            title="Test Page",
            content="This is a long piece of content that contains the word search in the middle of a paragraph about searching."
        ))

        results = index.search("search")
        assert len(results) == 1
        assert "search" in results[0].snippet.lower()
