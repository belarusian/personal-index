"""Adversarial deep tests for SearchIndex (content_search.py).

Targets: add_item/remove_item/search/get_suggestions round-trips,
None/empty/whitespace/unicode/duplicate/out-of-range inputs,
property checks, and end-to-end CLI run.
"""
import pytest
import subprocess
import json
import tempfile
import os

from personal_index.content_search import SearchIndex


class TestAddItemEdgeCases:
    def test_add_item_none_id(self):
        """Items with None id should use id(item) fallback, not str(None)."""
        idx = SearchIndex()
        item = {"id": None, "title": "test", "content": "hello world"}
        idx.add_item(item)
        # Should not create an item with id "None"
        assert "None" not in idx._items

    def test_add_item_missing_id(self):
        """Adding item without id key should use id(item) fallback."""
        idx = SearchIndex()
        item = {"title": "test", "content": "hello world"}
        idx.add_item(item)
        assert len(idx._items) == 1

    def test_add_item_duplicate_id(self):
        """Adding same id twice should replace, not duplicate."""
        idx = SearchIndex()
        idx.add_item({"id": "1", "title": "first", "content": "hello"})
        idx.add_item({"id": "1", "title": "second", "content": "world"})
        assert len(idx._items) == 1
        assert idx._items["1"]["title"] == "second"

    def test_add_item_unicode_content(self):
        """Unicode content should be indexed correctly."""
        idx = SearchIndex()
        idx.add_item({"id": "1", "title": "test", "content": "héllo wörld"})
        results = idx.search("héllo")
        assert results["total"] == 1

    def test_add_item_whitespace_content(self):
        """Whitespace-only content should not crash."""
        idx = SearchIndex()
        idx.add_item({"id": "1", "title": "test", "content": "   "})
        # Title is indexed, so searching for title should find it
        results = idx.search("test")
        assert results["total"] == 1


class TestRemoveItemEdgeCases:
    def test_remove_nonexistent_item(self):
        """Removing an item that doesn't exist should not crash."""
        idx = SearchIndex()
        idx.remove_item("nonexistent")

    def test_remove_item_id_type_coercion(self):
        """remove_item should coerce id to string."""
        idx = SearchIndex()
        idx.add_item({"id": 123, "title": "test", "content": "hello"})
        idx.remove_item(123)
        assert len(idx._items) == 0


class TestSearchEdgeCases:
    def test_search_empty_query(self):
        """Empty query should return empty results."""
        idx = SearchIndex()
        idx.add_item({"id": "1", "title": "test", "content": "hello world"})
        results = idx.search("")
        assert results["total"] == 0
        assert results["results"] == []

    def test_search_whitespace_query(self):
        """Whitespace-only query should return empty results."""
        idx = SearchIndex()
        idx.add_item({"id": "1", "title": "test", "content": "hello world"})
        results = idx.search("   ")
        assert results["total"] == 0

    def test_search_negative_limit(self):
        """Negative limit should return empty results (bound guard)."""
        idx = SearchIndex()
        idx.add_item({"id": "1", "title": "test", "content": "hello world"})
        results = idx.search("hello", limit=-5)
        assert results["results"] == []
        assert results["total"] == 1

    def test_search_zero_limit(self):
        """Zero limit should return empty results."""
        idx = SearchIndex()
        idx.add_item({"id": "1", "title": "test", "content": "hello world"})
        results = idx.search("hello", limit=0)
        assert results["results"] == []
        assert results["total"] == 1

    def test_search_large_offset(self):
        """Offset beyond total should return empty results."""
        idx = SearchIndex()
        idx.add_item({"id": "1", "title": "test", "content": "hello world"})
        results = idx.search("hello", offset=100)
        assert results["results"] == []
        assert results["total"] == 1

    def test_search_unicode_query(self):
        """Unicode query should work."""
        idx = SearchIndex()
        idx.add_item({"id": "1", "title": "test", "content": "héllo wörld"})
        results = idx.search("wörld")
        assert results["total"] == 1

    def test_search_stopwords_only(self):
        """Query with only stopwords should return empty results."""
        idx = SearchIndex()
        idx.add_item({"id": "1", "title": "test", "content": "hello world"})
        results = idx.search("the a an is")
        assert results["total"] == 0


class TestSuggestionsEdgeCases:
    def test_suggestions_empty_prefix(self):
        """Empty prefix returns all terms (expected behavior)."""
        idx = SearchIndex()
        idx.add_item({"id": "1", "title": "test", "content": "hello world"})
        suggestions = idx.get_suggestions("")
        # Empty prefix matches all terms
        assert len(suggestions) > 0

    def test_suggestions_negative_limit(self):
        """Negative limit should return empty suggestions."""
        idx = SearchIndex()
        idx.add_item({"id": "1", "title": "test", "content": "hello world"})
        suggestions = idx.get_suggestions("h", limit=-5)
        assert suggestions == []

    def test_suggestions_zero_limit(self):
        """Zero limit should return empty suggestions."""
        idx = SearchIndex()
        idx.add_item({"id": "1", "title": "test", "content": "hello world"})
        suggestions = idx.get_suggestions("h", limit=0)
        assert suggestions == []

    def test_suggestions_unicode_prefix(self):
        """Unicode prefix should work."""
        idx = SearchIndex()
        idx.add_item({"id": "1", "title": "test", "content": "héllo wörld"})
        suggestions = idx.get_suggestions("hél")
        assert "héllo" in suggestions


class TestRoundTrip:
    def test_add_search_remove_roundtrip(self):
        """Full round-trip: add, search, remove, search again."""
        idx = SearchIndex()
        idx.add_item({"id": "1", "title": "test", "content": "hello world"})
        results = idx.search("hello")
        assert results["total"] == 1
        idx.remove_item("1")
        results = idx.search("hello")
        assert results["total"] == 0

    def test_readd_same_id(self):
        """Remove and re-add same id should work."""
        idx = SearchIndex()
        idx.add_item({"id": "1", "title": "first", "content": "hello"})
        idx.remove_item("1")
        idx.add_item({"id": "1", "title": "second", "content": "world"})
        results = idx.search("world")
        assert results["total"] == 1
        assert results["results"][0]["item"]["title"] == "second"


class TestIdempotence:
    def test_search_idempotent(self):
        """Multiple identical searches should return same results."""
        idx = SearchIndex()
        idx.add_item({"id": "1", "title": "test", "content": "hello world"})
        r1 = idx.search("hello")
        r2 = idx.search("hello")
        assert r1["total"] == r2["total"]
        assert len(r1["results"]) == len(r2["results"])


class TestEndToEndCLI:
    def test_search_cli_roundtrip(self):
        """End-to-end: import content via CLI, search, verify results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test content file
            content_file = os.path.join(tmpdir, "test.txt")
            with open(content_file, "w") as f:
                f.write("hello world test content")

            # Import the file using python -m
            result = subprocess.run(
                ["python3", "-m", "personal_index.cli", "import", content_file],
                capture_output=True, text=True, timeout=30
            )
            assert result.returncode == 0, f"import failed: {result.stderr}"

            # Search for the content
            result = subprocess.run(
                ["python3", "-m", "personal_index.cli", "search", "hello"],
                capture_output=True, text=True, timeout=30
            )
            assert result.returncode == 0, f"search failed: {result.stderr}"
            # Should find the indexed content
            assert "hello" in result.stdout.lower() or "world" in result.stdout.lower()
