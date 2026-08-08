"""Tests for the storage module."""

import os
import pytest
from personal_index.storage import PageStore, StoredPage


class TestStoredPage:
    def test_create_page(self):
        page = StoredPage(url="https://example.com", title="Test", content="Hello")
        assert page.url == "https://example.com"
        assert page.title == "Test"

    def test_to_dict_and_from_dict(self):
        page = StoredPage(
            url="https://example.com",
            title="Test",
            content="Hello",
            file_hash="abc123",
            file_size=100,
        )
        data = page.to_dict()
        restored = StoredPage.from_dict(data)
        assert restored.url == "https://example.com"
        assert restored.file_hash == "abc123"
        assert restored.file_size == 100


class TestPageStore:
    def test_create_store(self, tmp_path):
        store = PageStore(store_dir=str(tmp_path / "pages"))
        assert store.count_pages() == 0

    def test_save_and_get_page(self, tmp_path):
        store = PageStore(store_dir=str(tmp_path / "pages"))
        page = store.save_page(
            url="https://example.com",
            content="<html><body>Hello</body></html>",
            title="Test Page",
        )
        assert page.url == "https://example.com"
        assert page.file_size > 0

    def test_get_page_content(self, tmp_path):
        store = PageStore(store_dir=str(tmp_path / "pages"))
        content = "<html><body>Hello World</body></html>"
        store.save_page(url="https://example.com", content=content, title="Test")
        retrieved = store.get_page_content("https://example.com")
        assert retrieved == content

    def test_get_nonexistent_content(self, tmp_path):
        store = PageStore(store_dir=str(tmp_path / "pages"))
        assert store.get_page_content("https://nonexistent.com") is None

    def test_delete_page(self, tmp_path):
        store = PageStore(store_dir=str(tmp_path / "pages"))
        store.save_page(url="https://example.com", content="Hello", title="Test")
        assert store.delete_page("https://example.com") is True
        assert store.count_pages() == 0

    def test_delete_nonexistent(self, tmp_path):
        store = PageStore(store_dir=str(tmp_path / "pages"))
        assert store.delete_page("https://nonexistent.com") is False

    def test_list_pages(self, tmp_path):
        store = PageStore(store_dir=str(tmp_path / "pages"))
        store.save_page(url="https://a.com", content="A", title="A")
        store.save_page(url="https://b.com", content="B", title="B")
        pages = store.list_pages()
        assert len(pages) == 2

    def test_count_pages(self, tmp_path):
        store = PageStore(store_dir=str(tmp_path / "pages"))
        assert store.count_pages() == 0
        store.save_page(url="https://example.com", content="Hello", title="Test")
        assert store.count_pages() == 1

    def test_total_size(self, tmp_path):
        store = PageStore(store_dir=str(tmp_path / "pages"))
        store.save_page(url="https://example.com", content="Hello World", title="Test")
        assert store.get_total_size() > 0

    def test_clear(self, tmp_path):
        store = PageStore(store_dir=str(tmp_path / "pages"))
        store.save_page(url="https://a.com", content="A", title="A")
        store.save_page(url="https://b.com", content="B", title="B")
        store.clear()
        assert store.count_pages() == 0

    def test_has_page(self, tmp_path):
        store = PageStore(store_dir=str(tmp_path / "pages"))
        assert store.has_page("https://example.com") is False
        store.save_page(url="https://example.com", content="Hello", title="Test")
        assert store.has_page("https://example.com") is True

    def test_get_page_hash(self, tmp_path):
        store = PageStore(store_dir=str(tmp_path / "pages"))
        assert store.get_page_hash("https://example.com") is None
        store.save_page(url="https://example.com", content="Hello", title="Test")
        assert store.get_page_hash("https://example.com") is not None

    def test_persistence(self, tmp_path):
        store_dir = str(tmp_path / "pages")
        store = PageStore(store_dir=store_dir)
        store.save_page(url="https://example.com", content="Hello", title="Test")

        store2 = PageStore(store_dir=store_dir)
        assert store2.has_page("https://example.com") is True

    def test_file_created_on_disk(self, tmp_path):
        store = PageStore(store_dir=str(tmp_path / "pages"))
        store.save_page(url="https://example.com", content="Hello", title="Test")
        files = list(tmp_path.glob("pages/*.html"))
        assert len(files) == 1

    def test_url_to_filename_deterministic(self, tmp_path):
        store = PageStore(store_dir=str(tmp_path / "pages"))
        fn1 = store._url_to_filename("https://example.com")
        fn2 = store._url_to_filename("https://example.com")
        assert fn1 == fn2

    def test_url_to_filename_different(self, tmp_path):
        store = PageStore(store_dir=str(tmp_path / "pages"))
        fn1 = store._url_to_filename("https://example.com/a")
        fn2 = store._url_to_filename("https://example.com/b")
        assert fn1 != fn2
