"""Content aggregator module - aggregate content from multiple sources."""

from personal_index.content_aggregator.aggregator import ContentAggregator
from personal_index.content_aggregator.merge import MergeStrategy
from personal_index.content_aggregator.source import ContentSource, SourceConfig

__all__ = [
    "ContentAggregator",
    "ContentSource",
    "MergeStrategy",
    "SourceConfig",
]
