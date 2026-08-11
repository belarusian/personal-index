"""End-to-end tests for search index persistence."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from personal_index.index import SearchIndex
from personal_index.models import CrawledPage, IndexedPage


class TestSearchIndexPersistenceE2E:
    """Test search index persistence with realistic scenarios."""

    def test_save_and_load(self, tmp_path):
        """Save index and load it back."""
        path = str(tmp_path / "index.json")
        index1 = SearchIndex(db_path=path)
        
        # Add some pages
        index1.add_page(CrawledPage(
            url="https://example.com/1",
            title="Page 1",
            content="Content for page one.",
        ))
        index1.add_page(CrawledPage(
            url="https://example.com/2",
            title="Page 2",
            content="Content for page two.",
        ))
        
        # Verify saved
        assert os.path.exists(path)
        
        # Load new instance
        index2 = SearchIndex(db_path=path)
        
        assert index2.get_page_count() == 2

    def test_persistence_across_instances(self, tmp_path):
        """Index persists across different instances."""
        path = str(tmp_path / "index.json")
        
        # First instance
        index1 = SearchIndex(db_path=path)
        index1.add_page(CrawledPage(
            url="https://example.com/test",
            title="Test Page",
            content="This is test content.",
        ))
        del index1
        
        # Second instance
        index2 = SearchIndex(db_path=path)
        page = index2.get_page("https://example.com/test")
        
        assert page is not None
        assert page.title == "Test Page"

    def test_search_persistence(self, tmp_path):
        """Search works after loading persisted index."""
        path = str(tmp_path / "index.json")
        
        # Create and search
        index1 = SearchIndex(db_path=path)
        index1.add_page(CrawledPage(
            url="https://example.com/python",
            title="Python Guide",
            content="Python is a programming language.",
        ))
        
        # Load and search
        index2 = SearchIndex(db_path=path)
        results = index2.search("python")
        
        assert len(results) >= 1
        assert "Python" in results[0].title

    def test_remove_persistence(self, tmp_path):
        """Removed pages don't persist."""
        path = str(tmp_path / "index.json")
        
        index1 = SearchIndex(db_path=path)
        index1.add_page(CrawledPage(
            url="https://example.com/keep",
            title="Keep",
            content="Keep this page.",
        ))
        index1.add_page(CrawledPage(
            url="https://example.com/remove",
            title="Remove",
            content="Remove this page.",
        ))
        index1.remove_page("https://example.com/remove")
        
        # Verify removal persisted
        index2 = SearchIndex(db_path=path)
        
        assert index2.get_page_count() == 1
        assert index2.get_page("https://example.com/keep") is not None

    def test_clear_persistence(self, tmp_path):
        """Clear operation persists."""
        path = str(tmp_path / "index.json")
        
        index1 = SearchIndex(db_path=path)
        for i in range(5):
            index1.add_page(CrawledPage(
                url=f"https://example.com/{i}",
                title=f"Page {i}",
                content=f"Content {i}.",
            ))
        index1.clear()
        
        # Verify clear persisted
        index2 = SearchIndex(db_path=path)
        assert index2.get_page_count() == 0

    def test_large_index_persistence(self, tmp_path):
        """Handle large index persistence."""
        path = str(tmp_path / "index.json")
        index = SearchIndex(db_path=path)
        
        # Add 100 pages
        for i in range(100):
            index.add_page(CrawledPage(
                url=f"https://example.com/page{i}",
                title=f"Page {i}",
                content=f"Content for page {i} with some keywords.",
            ))
        
        # Verify all persisted
        index2 = SearchIndex(db_path=path)
        assert index2.get_page_count() == 100

    def test_empty_file_handling(self, tmp_path):
        """Handle empty file gracefully."""
        path = str(tmp_path / "index.json")
        
        with open(path, "w") as f:
            f.write("")
        
        index = SearchIndex(db_path=path)
        assert index.get_page_count() == 0

    def test_invalid_json_handling(self, tmp_path):
        """Handle invalid JSON gracefully."""
        path = str(tmp_path / "index.json")
        
        with open(path, "w") as f:
            f.write("{invalid json}")
        
        index = SearchIndex(db_path=path)
        assert index.get_page_count() == 0

    def test_search_snippet_persistence(self, tmp_path):
        """Search results include snippets after loading."""
        path = str(tmp_path / "index.json")
        
        index1 = SearchIndex(db_path=path)
        index1.add_page(CrawledPage(
            url="https://example.com/test",
            title="Test Page",
            content="This is a long piece of content that contains the word search in the middle.",
        ))
        
        index2 = SearchIndex(db_path=path)
        results = index2.search("search")
        
        assert len(results) >= 1
        assert "search" in results[0].snippet.lower()

    def test_word_index_persistence(self, tmp_path):
        """Word index persists for faster searching."""
        path = str(tmp_path / "index.json")
        
        index1 = SearchIndex(db_path=path)
        index1.add_page(CrawledPage(
            url="https://example.com/a",
            title="Python Programming",
            content="Python is a programming language.",
        ))
        index1.add_page(CrawledPage(
            url="https://example.com/b",
            title="Rust Programming",
            content="Rust is also a programming language.",
        ))
        
        # Check word index
        assert "python" in index1._word_index
        assert "programming" in index1._word_index
        
        # Load and verify word index persisted
        index2 = SearchIndex(db_path=path)
        assert "python" in index2._word_index
        assert "programming" in index2._word_index
