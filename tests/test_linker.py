"""Tests for content linker."""

from datetime import datetime, timezone

from personal_index.content_linker.linker import ContentLinker


class TestContentLinker:
    def test_add_and_get_item(self):
        l = ContentLinker()
        l.add_item("id1", "hello world", url="https://example.com")
        item = l.get_item("id1")
        assert item is not None
        assert item["content"] == "hello world"

    def test_get_missing_item(self):
        l = ContentLinker()
        assert l.get_item("missing") is None

    def test_remove_item(self):
        l = ContentLinker()
        l.add_item("id1", "hello")
        l.remove_item("id1")
        assert l.get_item("id1") is None

    def test_get_all_items(self):
        l = ContentLinker()
        l.add_item("id1", "a")
        l.add_item("id2", "b")
        assert len(l.get_all_items()) == 2

    def test_find_related_content(self):
        l = ContentLinker()
        l.add_item("id1", "hello world foo bar")
        l.add_item("id2", "hello world baz qux")
        related = l.find_related("id1", threshold=0.05)
        assert len(related) >= 1
        assert related[0]["id"] == "id2"

    def test_find_related_no_match(self):
        l = ContentLinker()
        l.add_item("id1", "hello world")
        l.add_item("id2", "completely different content")
        related = l.find_related("id1", threshold=0.5)
        assert len(related) == 0

    def test_find_related_missing_item(self):
        l = ContentLinker()
        related = l.find_related("missing")
        assert related == []

    def test_find_related_domain(self):
        l = ContentLinker()
        l.add_item("id1", "unique content xyz", url="https://example.com/a")
        l.add_item("id2", "other unique abc", url="https://example.com/b")
        related = l.find_related("id1", threshold=0.01)
        assert len(related) >= 1
        assert "domain" in related[0]["reasons"]

    def test_find_related_temporal(self):
        now = datetime.now(timezone.utc).isoformat()
        l = ContentLinker()
        l.add_item("id1", "unique text abc", saved_at=now)
        l.add_item("id2", "different text xyz", saved_at=now)
        related = l.find_related("id1", threshold=0.01)
        assert len(related) >= 1

    def test_find_related_limit(self):
        l = ContentLinker()
        now = datetime.now(timezone.utc).isoformat()
        l.add_item("id1", "shared content text")
        for i in range(5):
            l.add_item(f"other{i}", "shared content text", saved_at=now)
        related = l.find_related("id1", threshold=0.01, limit=2)
        assert len(related) <= 2

    def test_get_all_links(self):
        l = ContentLinker()
        now = datetime.now(timezone.utc).isoformat()
        l.add_item("id1", "hello world")
        l.add_item("id2", "hello there", saved_at=now)
        links = l.get_all_links("id1", threshold=0.05)
        assert len(links) >= 1

    def test_clear_cache(self):
        l = ContentLinker()
        l.add_item("id1", "hello")
        l.clear_cache()
        assert len(l.get_all_items()) == 0
