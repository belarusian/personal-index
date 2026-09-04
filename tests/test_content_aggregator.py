"""Tests for content_aggregator module."""

import pytest

from personal_index.content_aggregator import ContentAggregator


@pytest.fixture
def aggregator():
    return ContentAggregator()


class TestBasicOperations:
    def test_add_source(self, aggregator):
        aggregator.add_source("feed1", [{"id": "1", "title": "Post 1"}])
        assert aggregator.source_count == 1

    def test_get_source(self, aggregator):
        items = [{"id": "1", "title": "Post 1"}]
        aggregator.add_source("feed1", items)
        assert aggregator.get_source("feed1") == items

    def test_get_nonexistent_source(self, aggregator):
        assert aggregator.get_source("nonexistent") == []

    def test_total_items(self, aggregator):
        aggregator.add_source("a", [{"id": "1"}])
        aggregator.add_source("b", [{"id": "2"}, {"id": "3"}])
        assert aggregator.total_items == 3

    def test_clear_source(self, aggregator):
        aggregator.add_source("feed1", [{"id": "1"}])
        assert aggregator.clear_source("feed1") is True
        assert aggregator.source_count == 0

    def test_clear_nonexistent_source(self, aggregator):
        assert aggregator.clear_source("nonexistent") is False

    def test_clear_all(self, aggregator):
        aggregator.add_source("a", [])
        aggregator.add_source("b", [])
        aggregator.clear_all()
        assert aggregator.source_count == 0


class TestMerge:
    def test_merge_deduplicate(self, aggregator):
        aggregator.add_source("a", [{"id": "1", "title": "A"}])
        aggregator.add_source("b", [{"id": "1", "title": "B"}])
        merged = aggregator.merge_all(deduplicate=True)
        assert len(merged) == 1

    def test_merge_no_deduplicate(self, aggregator):
        aggregator.add_source("a", [{"id": "1", "title": "A"}])
        aggregator.add_source("b", [{"id": "1", "title": "B"}])
        merged = aggregator.merge_all(deduplicate=False)
        assert len(merged) == 2

    def test_merge_empty(self, aggregator):
        merged = aggregator.merge_all()
        assert merged == []

    def test_merge_preserves_fields(self, aggregator):
        aggregator.add_source("a", [{"id": "1", "title": "T", "link": "http://x.com"}])
        merged = aggregator.merge_all()
        assert merged[0]["link"] == "http://x.com"


class TestFiltering:
    def test_filter_by_source(self, aggregator):
        aggregator.add_source("feed1", [{"id": "1"}])
        aggregator.add_source("feed2", [{"id": "2"}])
        items = aggregator.filter_by_source("feed1")
        assert len(items) == 1
        assert items[0]["id"] == "1"

    def test_filter_empty_source(self, aggregator):
        items = aggregator.filter_by_source("nonexistent")
        assert items == []


class TestSourceNames:
    def test_get_source_names(self, aggregator):
        aggregator.add_source("a", [])
        aggregator.add_source("b", [])
        names = aggregator.get_source_names()
        assert set(names) == {"a", "b"}

    def test_get_source_names_empty(self, aggregator):
        assert aggregator.get_source_names() == []


class TestMergeDedupKeepFirst:
    def test_merge_default_dedup_keeps_first_occurrence_by_id(self, aggregator):
        """Pin the corrected claim: default merge_all dedups by id (fallback
        title), keeping the FIRST occurrence, asserted on the returned list."""
        aggregator.add_source("a", [{"id": "1", "title": "First"}])
        aggregator.add_source("b", [{"id": "1", "title": "Second"}])
        merged = aggregator.merge_all()  # deduplicate defaults to True
        assert len(merged) == 1
        # The survivor is the FIRST occurrence (from source "a"), not the later one.
        assert merged[0]["title"] == "First"
