"""Content aggregator for combining multiple sources."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

from personal_index.content_aggregator.merge import (
    MergeResult,
    MergeStrategy,
    merge_append,
    merge_dedup,
    merge_fields,
    merge_replace,
)
from personal_index.content_aggregator.source import ContentSource, SourceConfig


@dataclass
class ContentAggregator:
    """Aggregates content from multiple sources.

    Attributes:
        sources: Registered content sources.
        default_strategy: Default merge strategy.
        id_field: Field used for deduplication.
    """

    sources: list[ContentSource] = field(default_factory=list)
    default_strategy: MergeStrategy = MergeStrategy.DEDUP
    id_field: str = "id"

    def add_source(self, source: ContentSource) -> None:
        """Add a content source.

        Args:
            source: Source to add.
        """
        self.sources.append(source)

    def add_source_config(
        self,
        config: SourceConfig,
    ) -> ContentSource:
        """Add a source from configuration.

        Args:
            config: Source configuration.

        Returns:
            Created ContentSource.
        """
        source = ContentSource(config=config)
        self.add_source(source)
        return source

    def aggregate(
        self,
        strategy: MergeStrategy | None = None,
    ) -> MergeResult:
        """Aggregate content from all enabled sources.

        Args:
            strategy: Merge strategy to use.

        Returns:
            MergeResult with aggregated content.
        """
        strategy = strategy or self.default_strategy
        all_items = [
            source.get_items()
            for source in self.sources
            if source.config.enabled
        ]

        if not all_items:
            return MergeResult(
                items=[],
                strategy=strategy,
                total_sources=0,
                total_items=0,
            )

        merge_fns = {
            MergeStrategy.APPEND: lambda items: merge_append(items),
            MergeStrategy.DEDUP: lambda items: merge_dedup(items, self.id_field),
            MergeStrategy.REPLACE: lambda items: merge_replace(items, self.id_field),
            MergeStrategy.MERGE_FIELDS: lambda items: merge_fields(items, self.id_field),
        }

        fn = merge_fns.get(strategy, merge_append)
        return cast(MergeResult, fn(all_items))

    def get_source(self, name: str) -> ContentSource | None:
        """Get a source by name.

        Args:
            name: Source name.

        Returns:
            ContentSource or None.
        """
        for source in self.sources:
            if source.config.name == name:
                return source
        return None

    @property
    def source_count(self) -> int:
        """Number of registered sources."""
        return len(self.sources)

    @property
    def total_items(self) -> int:
        """Total items across all sources."""
        return sum(s.item_count for s in self.sources)
