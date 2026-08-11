"""Tests for content_dedup module."""

import pytest
from personal_index.content_dedup import ContentDeduplicator, DedupFilter


class TestContentDeduplicator:
    def test_deduplicate_basic(self):
        items = [
            {"id": "1", "title": "Same", "description": "Text"},
            {"id": "2", "title": "Same", "description": "Text"},
            {"id": "3", "title": "Different", "description": "Other"},
        ]
        dedup = ContentDeduplicator()
        result = dedup.deduplicate(items)
        assert len(result) == 2

    def test_deduplicate_no_duplicates(self):
        items = [
            {"id": "1", "title": "A", "description": "X"},
            {"id": "2", "title": "B", "description": "Y"},
        ]
        dedup = ContentDeduplicator()
        result = dedup.deduplicate(items)
        assert len(result) == 2

    def test_deduplicate_all_same(self):
        items = [
            {"id": "1", "title": "Same", "description": "Text"},
            {"id": "2", "title": "Same", "description": "Text"},
        ]
        dedup = ContentDeduplicator()
        result = dedup.deduplicate(items)
        assert len(result) == 1

    def test_is_duplicate(self):
        items = [
            {"id": "1", "title": "A", "description": "B"},
            {"id": "2", "title": "A", "description": "B"},
        ]
        dedup = ContentDeduplicator()
        assert not dedup.is_duplicate(items[0])
        dedup.mark_seen(items[0])
        assert dedup.is_duplicate(items[1])

    def test_mark_seen(self):
        item = {"id": "1", "title": "A", "description": "B"}
        dedup = ContentDeduplicator()
        dedup.mark_seen(item)
        assert dedup.seen_count == 1

    def test_clear_seen(self):
        item = {"id": "1", "title": "A", "description": "B"}
        dedup = ContentDeduplicator()
        dedup.mark_seen(item)
        dedup.clear_seen()
        assert dedup.seen_count == 0


class TestDedupFilter:
    def test_filter_by_id(self):
        items = [
            {"id": "1", "title": "A"},
            {"id": "2", "title": "B"},
            {"id": "1", "title": "C"},  # duplicate
        ]
        filter_ = DedupFilter()
        result = filter_.filter(items)
        assert len(result) == 2

    def test_filter_by_custom_key(self):
        items = [
            {"url": "a.com", "title": "A"},
            {"url": "b.com", "title": "B"},
            {"url": "a.com", "title": "C"},
        ]
        filter_ = DedupFilter()
        result = filter_.filter(items, key="url")
        assert len(result) == 2

    def test_filter_empty(self):
        filter_ = DedupFilter()
        result = filter_.filter([])
        assert result == []

    def test_clear(self):
        items = [{"id": "1"}]
        filter_ = DedupFilter()
        filter_.filter(items)
        filter_.clear()
        # After clear, should allow duplicates again
        result = filter_.filter([{"id": "1"}])
        assert len(result) == 1
