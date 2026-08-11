"""Tests for content aggregator module."""

import pytest

from personal_index.content_aggregator.aggregator import ContentAggregator
from personal_index.content_aggregator.merge import (
    MergeResult,
    MergeStrategy,
    merge_append,
    merge_dedup,
    merge_fields,
    merge_replace,
)
from personal_index.content_aggregator.source import ContentSource, SourceConfig


class TestContentSource:
    def test_add_items(self) -> None:
        config = SourceConfig(name="test")
        source = ContentSource(config=config)
        source.add_items([{"id": "1"}])
        assert source.item_count == 1

    def test_get_items(self) -> None:
        config = SourceConfig(name="test")
        source = ContentSource(config=config)
        source.add_items([{"id": "1"}, {"id": "2"}])
        items = source.get_items()
        assert len(items) == 2

    def test_clear(self) -> None:
        config = SourceConfig(name="test")
        source = ContentSource(config=config)
        source.add_items([{"id": "1"}])
        source.clear()
        assert source.item_count == 0


class TestMergeStrategies:
    def test_merge_append(self) -> None:
        result = merge_append([[{"id": "1"}], [{"id": "2"}]])
        assert result.total_items == 2
        assert result.strategy == MergeStrategy.APPEND

    def test_merge_dedup(self) -> None:
        result = merge_dedup(
            [[{"id": "1"}], [{"id": "1"}, {"id": "2"}]]
        )
        assert result.total_items == 2
        assert result.duplicates_removed == 1

    def test_merge_replace(self) -> None:
        result = merge_replace(
            [[{"id": "1", "title": "A"}], [{"id": "1", "title": "B"}]]
        )
        assert result.total_items == 1
        assert result.items[0]["title"] == "B"

    def test_merge_fields(self) -> None:
        result = merge_fields(
            [[{"id": "1", "title": "A"}], [{"id": "1", "content": "C"}]]
        )
        assert result.total_items == 1
        assert result.items[0]["title"] == "A"
        assert result.items[0]["content"] == "C"


class TestContentAggregator:
    def test_add_source(self) -> None:
        agg = ContentAggregator()
        source = ContentSource(config=SourceConfig(name="s1"))
        agg.add_source(source)
        assert agg.source_count == 1

    def test_aggregate_dedup(self) -> None:
        agg = ContentAggregator(default_strategy=MergeStrategy.DEDUP)
        s1 = ContentSource(config=SourceConfig(name="s1"))
        s1.add_items([{"id": "1"}, {"id": "2"}])
        s2 = ContentSource(config=SourceConfig(name="s2"))
        s2.add_items([{"id": "2"}, {"id": "3"}])
        agg.add_source(s1)
        agg.add_source(s2)
        result = agg.aggregate()
        assert result.total_items == 3
        assert result.duplicates_removed == 1

    def test_aggregate_append(self) -> None:
        agg = ContentAggregator(default_strategy=MergeStrategy.APPEND)
        s1 = ContentSource(config=SourceConfig(name="s1"))
        s1.add_items([{"id": "1"}])
        s2 = ContentSource(config=SourceConfig(name="s2"))
        s2.add_items([{"id": "1"}])
        agg.add_source(s1)
        agg.add_source(s2)
        result = agg.aggregate()
        assert result.total_items == 2

    def test_disabled_source(self) -> None:
        agg = ContentAggregator()
        s1 = ContentSource(config=SourceConfig(name="s1", enabled=False))
        s1.add_items([{"id": "1"}])
        agg.add_source(s1)
        result = agg.aggregate()
        assert result.total_items == 0

    def test_get_source(self) -> None:
        agg = ContentAggregator()
        source = ContentSource(config=SourceConfig(name="s1"))
        agg.add_source(source)
        found = agg.get_source("s1")
        assert found is not None
        assert agg.get_source("nonexistent") is None

    def test_total_items(self) -> None:
        agg = ContentAggregator()
        s1 = ContentSource(config=SourceConfig(name="s1"))
        s1.add_items([{"id": "1"}, {"id": "2"}])
        agg.add_source(s1)
        assert agg.total_items == 2
