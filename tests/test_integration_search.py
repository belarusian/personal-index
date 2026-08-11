"""Integration tests for search functionality."""

from __future__ import annotations

import os
import tempfile

import pytest

from personal_index.app import PersonalIndexApp


class TestSearchIntegration:
    """Test search across the full application."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.app = PersonalIndexApp(
            config_path=os.path.join(self.tmpdir, "config.yaml"),
            data_dir=os.path.join(self.tmpdir, "data"),
        )
        self.app.initialize()
        # Add an interest so content passes the interest match filter
        self.app.add_interest("General", keywords=["python", "javascript", "tech", "programming", "content", "article"])

    def _add_content(self, url: str, content: str, title: str = ""):
        """Add content that passes the filter (min 100 chars)."""
        # Pad content to meet min_content_length=100
        padded = content if len(content) >= 100 else content + " " + "extra context words for padding. " * 10
        self.app.process_content(url, padded, title)

    def test_single_term_search(self):
        """Search for a single term."""
        self._add_content("https://ex.com/1", "Python is great for programming", "Python Guide")
        results = self.app.search("python")
        assert len(results) >= 1

    def test_multi_term_search(self):
        """Search for multiple terms."""
        self._add_content("https://ex.com/1", "Python and JavaScript are programming languages", "Languages")
        results = self.app.search("python javascript")
        assert len(results) >= 1

    def test_search_limit(self):
        """Search should respect the limit parameter."""
        for i in range(10):
            self._add_content(f"https://ex.com/{i}", f"Article number {i} about tech", f"Article {i}")
        results = self.app.search("tech", limit=3)
        assert len(results) <= 3

    def test_search_case_insensitive(self):
        """Search should be case-insensitive."""
        self._add_content("https://ex.com/1", "Python programming language", "Python")
        assert len(self.app.search("python")) >= 1
        assert len(self.app.search("PYTHON")) >= 1
        assert len(self.app.search("Python")) >= 1

    def test_search_no_results(self):
        """Search for non-existent term returns empty."""
        self._add_content("https://ex.com/1", "Python programming language", "Python")
        results = self.app.search("xyznonexistent")
        assert results == []

    def test_search_with_special_chars(self):
        """Search should handle special characters gracefully."""
        self._add_content("https://ex.com/1", "Using Python's features for development", "Python Features")
        results = self.app.search("python")
        assert len(results) >= 1

    def test_search_multiple_documents(self):
        """Search across multiple documents."""
        docs = [
            ("https://ex.com/py", "Python is a programming language", "Python"),
            ("https://ex.com/js", "JavaScript is also a programming language", "JavaScript"),
            ("https://ex.com/ai", "AI uses machine learning", "AI"),
        ]
        for url, content, title in docs:
            self._add_content(url, content, title)

        results = self.app.search("programming")
        assert len(results) >= 2  # Python and JS docs

    def test_search_returns_title(self):
        """Search results should include the title."""
        self._add_content("https://ex.com/1", "Some content here", "My Special Title")
        results = self.app.search("content")
        assert len(results) >= 1
        assert "title" in results[0]

    def test_search_returns_url(self):
        """Search results should include the URL."""
        self._add_content("https://example.com/page", "Some content here", "Title")
        results = self.app.search("content")
        assert len(results) >= 1
        assert "url" in results[0]
        assert results[0]["url"] == "https://example.com/page"

    def test_search_returns_score(self):
        """Search results should include a relevance score."""
        self._add_content("https://ex.com/1", "Important content here", "Title")
        results = self.app.search("content")
        assert len(results) >= 1
        assert "score" in results[0]
        assert isinstance(results[0]["score"], (int, float))
