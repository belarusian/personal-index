"""Tests for content_search module."""

import pytest
from datetime import datetime, timezone
from personal_index.content_search import SearchIndex, ContentSearch


@pytest.fixture
def sample_items():
    return [
        {"id": "1", "title": "Python Tutorial", "description": "Learn Python basics", "tags": ["python", "tutorial"]},
        {"id": "2", "title": "JavaScript Guide", "description": "JavaScript fundamentals", "tags": ["javascript", "web"]},
        {"id": "3", "title": "Python Advanced", "description": "Advanced Python techniques", "tags": ["python", "advanced"]},
        {"id": "4", "title": "React Framework", "description": "Building UIs with React", "tags": ["react", "javascript", "web"]},
        {"id": "5", "title": "Data Science", "description": "Python for data science", "tags": ["python", "data"]},
    ]


@pytest.fixture
def search():
    s = ContentSearch()
    return s


# --- Basic Indexing Tests ---

class TestIndexing:
    def test_add_single_item(self, search):
        search.index_items([{"id": "1", "title": "Test Post"}])
        assert search.index.item_count == 1

    def test_add_multiple_items(self, search, sample_items):
        search.index_items(sample_items)
        assert search.index.item_count == 5

    def test_remove_item(self, search, sample_items):
        search.index_items(sample_items)
        search.remove_item("1")
        assert search.index.item_count == 4

    def test_remove_nonexistent_item(self, search):
        search.remove_item("999")  # should not raise

    def test_term_count(self, search, sample_items):
        search.index_items(sample_items)
        assert search.index.term_count > 0

    def test_add_duplicate_item(self, search):
        item = {"id": "1", "title": "Test"}
        search.index_items([item, item])
        assert search.index.item_count == 1
