"""Tests for personal_index.storage."""

import pytest
import tempfile
import shutil
from datetime import datetime

from personal_index.models import CrawledPage, Interest
from personal_index.storage import InterestStore, PageStore, StorageError


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def interest_store(temp_data_dir):
    """Create an InterestStore with a temp directory."""
    return InterestStore(data_dir=temp_data_dir)


@pytest.fixture
def page_store(temp_data_dir):
    """Create a PageStore with a temp directory."""
    return PageStore(data_dir=temp_data_dir)


class TestInterestStore:
    def test_add_interest(self, interest_store):
        interest = Interest(topic="python", keywords=["python", "code"])
        result = interest_store.add_interest(interest)
        assert result.topic == "python"

    def test_add_duplicate_interest_raises(self, interest_store):
        interest = Interest(topic="python")
        interest_store.add_interest(interest)
        with pytest.raises(ValueError, match="already exists"):
            interest_store.add_interest(Interest(topic="python"))

    def test_get_interest(self, interest_store):
        interest = Interest(topic="python", keywords=["python"])
        interest_store.add_interest(interest)
        retrieved = interest_store.get_interest("python")
        assert retrieved is not None
        assert retrieved.topic == "python"
        assert retrieved.keywords == ["python"]

    def test_get_nonexistent_interest(self, interest_store):
        assert interest_store.get_interest("nonexistent") is None

    def test_list_interests(self, interest_store):
        interest_store.add_interest(Interest(topic="python"))
        interest_store.add_interest(Interest(topic="ai"))
        interests = interest_store.list_interests()
        assert len(interests) == 2

    def test_list_interests_empty(self, interest_store):
        interests = interest_store.list_interests()
        assert len(interests) == 0

    def test_list_interests_enabled_only(self, interest_store):
        interest_store.add_interest(Interest(topic="python", enabled=True))
        interest_store.add_interest(Interest(topic="disabled", enabled=False))
        interests = interest_store.list_interests(enabled_only=True)
        assert len(interests) == 1
        assert interests[0].topic == "python"

    def test_remove_interest(self, interest_store):
        interest_store.add_interest(Interest(topic="python"))
        assert interest_store.remove_interest("python") is True
        assert interest_store.get_interest("python") is None

    def test_remove_nonexistent_interest(self, interest_store):
        assert interest_store.remove_interest("nonexistent") is False

    def test_toggle_interest(self, interest_store):
        interest_store.add_interest(Interest(topic="python", enabled=True))
        result = interest_store.toggle_interest("python")
        assert result.enabled is False
        result = interest_store.toggle_interest("python")
        assert result.enabled is True

    def test_toggle_nonexistent_interest(self, interest_store):
        assert interest_store.toggle_interest("nonexistent") is None

    def test_persistence(self, temp_data_dir):
        """Test that data persists across store instances."""
        store1 = InterestStore(data_dir=temp_data_dir)
        store1.add_interest(Interest(topic="python", keywords=["python"]))

        store2 = InterestStore(data_dir=temp_data_dir)
        interests = store2.list_interests()
        assert len(interests) == 1
        assert interests[0].topic == "python"


class TestPageStore:
    def test_save_page(self, page_store):
        page = CrawledPage(
            url="https://example.com",
            title="Test Page",
            content="Test content",
        )
        page_store.save_page(page)
        assert page_store.count_pages() == 1

    def test_get_page(self, page_store):
        page = CrawledPage(
            url="https://example.com",
            title="Test Page",
            content="Test content",
            word_count=2,
        )
        page_store.save_page(page)
        retrieved = page_store.get_page(page.id)
        assert retrieved is not None
        assert retrieved.url == "https://example.com"
        assert retrieved.title == "Test Page"
        assert retrieved.content == "Test content"

    def test_get_nonexistent_page(self, page_store):
        assert page_store.get_page("nonexistent-id") is None

    def test_list_pages(self, page_store):
        page_store.save_page(CrawledPage(url="https://example.com/1", title="Page 1"))
        page_store.save_page(CrawledPage(url="https://example.com/2", title="Page 2"))
        pages = page_store.list_pages()
        assert len(pages) == 2

    def test_list_pages_empty(self, page_store):
        pages = page_store.list_pages()
        assert len(pages) == 0

    def test_delete_page(self, page_store):
        page = CrawledPage(url="https://example.com", title="Test")
        page_store.save_page(page)
        assert page_store.delete_page(page.id) is True
        assert page_store.count_pages() == 0

    def test_delete_nonexistent_page(self, page_store):
        assert page_store.delete_page("nonexistent-id") is False

    def test_count_pages(self, page_store):
        assert page_store.count_pages() == 0
        page_store.save_page(CrawledPage(url="https://example.com"))
        assert page_store.count_pages() == 1

    def test_persistence(self, temp_data_dir):
        """Test that pages persist across store instances."""
        store1 = PageStore(data_dir=temp_data_dir)
        store1.save_page(CrawledPage(url="https://example.com", title="Test"))

        store2 = PageStore(data_dir=temp_data_dir)
        assert store2.count_pages() == 1
