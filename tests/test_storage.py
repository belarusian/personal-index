"""Tests for storage layer."""

import shutil
import tempfile

import pytest

from personal_index.models import CrawlConfig, IndexedPage, Interest
from personal_index.storage import Storage


@pytest.fixture
def temp_storage():
    """Create a temporary storage instance."""
    tmpdir = tempfile.mkdtemp()
    storage = Storage(data_dir=tmpdir)
    yield storage
    shutil.rmtree(tmpdir)


class TestStorageInterests:
    def test_add_interest(self, temp_storage):
        interest = Interest(name="python", keywords=["python", "dev"])
        result = temp_storage.add_interest(interest)
        assert result.name == "python"
        assert len(temp_storage.get_interests()) == 1

    def test_get_interests_empty(self, temp_storage):
        assert temp_storage.get_interests() == []

    def test_get_interest_by_name(self, temp_storage):
        interest = Interest(name="python", keywords=["python"])
        temp_storage.add_interest(interest)
        found = temp_storage.get_interest("python")
        assert found is not None
        assert found.name == "python"

    def test_get_interest_not_found(self, temp_storage):
        assert temp_storage.get_interest("nonexistent") is None

    def test_remove_interest(self, temp_storage):
        interest = Interest(name="python", keywords=["python"])
        temp_storage.add_interest(interest)
        assert temp_storage.remove_interest("python") is True
        assert temp_storage.get_interest("python") is None

    def test_remove_interest_not_found(self, temp_storage):
        assert temp_storage.remove_interest("nonexistent") is False

    def test_update_existing_interest(self, temp_storage):
        interest1 = Interest(name="python", keywords=["python"])
        temp_storage.add_interest(interest1)
        interest2 = Interest(name="python", keywords=["python", "dev"])
        temp_storage.add_interest(interest2)
        assert len(temp_storage.get_interests()) == 1
        found = temp_storage.get_interest("python")
        assert found.keywords == ["python", "dev"]

    def test_list_interests(self, temp_storage):
        temp_storage.add_interest(Interest(name="python", keywords=["python"]))
        temp_storage.add_interest(Interest(name="rust", keywords=["rust"]))
        listed = temp_storage.list_interests()
        assert len(listed) == 2
        assert listed[0]["name"] == "python"


class TestStorageConfig:
    def test_save_and_get_config(self, temp_storage):
        config = CrawlConfig(max_depth=5, politeness_delay=2.0)
        temp_storage.save_config(config)
        loaded = temp_storage.get_config()
        assert loaded.max_depth == 5
        assert loaded.politeness_delay == 2.0

    def test_get_default_config(self, temp_storage):
        config = temp_storage.get_config()
        assert config.max_depth == 3
        assert config.politeness_delay == 1.0


class TestStoragePages:
    def test_add_page(self, temp_storage):
        page = IndexedPage(url="https://example.com", title="Example")
        temp_storage.add_page(page)
        assert temp_storage.get_page_count() == 1

    def test_get_page(self, temp_storage):
        page = IndexedPage(url="https://example.com", title="Example")
        temp_storage.add_page(page)
        found = temp_storage.get_page("https://example.com")
        assert found is not None
        assert found.title == "Example"

    def test_get_page_not_found(self, temp_storage):
        assert temp_storage.get_page("https://nonexistent.com") is None

    def test_remove_page(self, temp_storage):
        page = IndexedPage(url="https://example.com", title="Example")
        temp_storage.add_page(page)
        assert temp_storage.remove_page("https://example.com") is True
        assert temp_storage.get_page_count() == 0

    def test_remove_page_not_found(self, temp_storage):
        assert temp_storage.remove_page("https://nonexistent.com") is False

    def test_update_existing_page(self, temp_storage):
        page1 = IndexedPage(url="https://example.com", title="Old")
        temp_storage.add_page(page1)
        page2 = IndexedPage(url="https://example.com", title="New")
        temp_storage.add_page(page2)
        assert temp_storage.get_page_count() == 1
        found = temp_storage.get_page("https://example.com")
        assert found.title == "New"

    def test_clear_pages(self, temp_storage):
        temp_storage.add_page(IndexedPage(url="https://a.com"))
        temp_storage.add_page(IndexedPage(url="https://b.com"))
        temp_storage.clear_pages()
        assert temp_storage.get_page_count() == 0


class TestStorageStats:
    def test_stats_empty(self, temp_storage):
        stats = temp_storage.get_stats()
        assert stats["total_interests"] == 0
        assert stats["total_pages"] == 0

    def test_stats_with_data(self, temp_storage):
        temp_storage.add_interest(Interest(name="python"))
        temp_storage.add_interest(Interest(name="rust", enabled=False))
        temp_storage.add_page(IndexedPage(url="https://a.com", content_length=100))
        stats = temp_storage.get_stats()
        assert stats["total_interests"] == 2
        assert stats["enabled_interests"] == 1
        assert stats["total_pages"] == 1
        assert stats["total_content_bytes"] == 100


class TestStorageTypeNarrowing:
    """Tests for TICKET-31: _read_json returns list|dict, callers must narrow."""

    def test_add_interest_with_dict_file(self, tmp_path):
        """add_interest should handle dict content in interests file gracefully."""
        storage = Storage(data_dir=str(tmp_path))
        # Simulate a dict in the interests file (should be a list)
        storage.interests_file.write_text('{"name": "bad"}')
        interest = Interest(name="test", keywords=["python"])
        result = storage.add_interest(interest)
        assert result.name == "test"

    def test_add_page_with_dict_file(self, tmp_path):
        """add_page should handle dict content in pages file gracefully."""
        storage = Storage(data_dir=str(tmp_path))
        # Simulate a dict in the pages file (should be a list)
        storage.pages_file.write_text('{"url": "bad"}')
        page = IndexedPage(url="http://example.com", title="Test")
        result = storage.add_page(page)
        assert result.url == "http://example.com"

    def test_get_config_with_list_file(self, tmp_path):
        """get_config should handle list content in config file gracefully."""
        storage = Storage(data_dir=str(tmp_path))
        # Simulate a list in the config file (should be a dict)
        storage.config_file.write_text('[1, 2, 3]')
        config = storage.get_config()
        assert isinstance(config, CrawlConfig)

    def test_get_config_with_empty_file(self, tmp_path):
        """get_config should return default CrawlConfig for empty file."""
        storage = Storage(data_dir=str(tmp_path))
        storage.config_file.write_text("")
        config = storage.get_config()
        assert isinstance(config, CrawlConfig)

    def test_add_interest_normal_operation(self, tmp_path):
        """add_interest should work normally with proper list content."""
        storage = Storage(data_dir=str(tmp_path))
        interest = Interest(name="test", keywords=["python"])
        result = storage.add_interest(interest)
        assert result.name == "test"
        assert len(storage.get_interests()) == 1

    def test_add_page_normal_operation(self, tmp_path):
        """add_page should work normally with proper list content."""
        storage = Storage(data_dir=str(tmp_path))
        page = IndexedPage(url="http://example.com", title="Test")
        result = storage.add_page(page)
        assert result.url == "http://example.com"
        assert len(storage.get_pages()) == 1


class TestStorageCorruptJson:
    """TICKET-306: malformed JSON must degrade to the documented default, not raise."""

    def test_get_interests_with_corrupt_file(self, tmp_path):
        storage = Storage(data_dir=str(tmp_path))
        storage.interests_file.write_text("{not json")
        assert storage.get_interests() == []

    def test_get_pages_with_corrupt_file(self, tmp_path):
        storage = Storage(data_dir=str(tmp_path))
        storage.pages_file.write_text("{not json")
        assert storage.get_pages() == []

    def test_get_config_with_corrupt_file(self, tmp_path):
        storage = Storage(data_dir=str(tmp_path))
        storage.config_file.write_text("{not json")
        config = storage.get_config()
        assert isinstance(config, CrawlConfig)

    def test_get_page_count_with_corrupt_file(self, tmp_path):
        storage = Storage(data_dir=str(tmp_path))
        storage.pages_file.write_text("[1, 2")
        assert storage.get_page_count() == 0

    def test_whitespace_only_interests(self, tmp_path):
        storage = Storage(data_dir=str(tmp_path))
        storage.interests_file.write_text("   \n  \t ")
        assert storage.get_interests() == []

    def test_whitespace_only_config(self, tmp_path):
        storage = Storage(data_dir=str(tmp_path))
        storage.config_file.write_text("   \n  ")
        assert isinstance(storage.get_config(), CrawlConfig)
