"""Content merging for personal-index.

Merges content from multiple sources, combining text, tags,
and metadata while avoiding duplication.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MergeSource:
    """A source of content to merge."""
    url: str
    title: str = ""
    content: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # Higher = more authoritative

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "tags": self.tags,
            "metadata": self.metadata,
            "priority": self.priority,
        }


@dataclass
class MergedContent:
    """Result of merging multiple content sources."""
    url: str
    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    source_count: int = 0
    sources: list[str] = field(default_factory=list)
    merge_strategy: str = "concatenate"

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "tags": self.tags,
            "metadata": self.metadata,
            "source_count": self.source_count,
            "sources": self.sources,
            "merge_strategy": self.merge_strategy,
        }


class ContentMerger:
    """Merges content from multiple sources.

    Supports different merge strategies:
    - concatenate: Join content with separators
    - longest: Use the longest content
    - highest_priority: Use content from highest priority source
    - unique_paragraphs: Merge unique paragraphs from all sources
    """

    def __init__(self, strategy: str = "concatenate"):
        self.strategy = strategy

    def merge(self, sources: list[MergeSource]) -> MergedContent | None:
        """Merge multiple content sources.

        Args:
            sources: List of MergeSource objects to merge.

        Returns:
            MergedContent or None if no sources provided.
        """
        if not sources:
            return None

        # Sort by priority descending
        sorted_sources = sorted(sources, key=lambda s: s.priority, reverse=True)

        if self.strategy == "longest":
            return self._merge_longest(sorted_sources)
        elif self.strategy == "highest_priority":
            return self._merge_highest_priority(sorted_sources)
        elif self.strategy == "unique_paragraphs":
            return self._merge_unique_paragraphs(sorted_sources)
        else:  # concatenate (default)
            return self._merge_concatenate(sorted_sources)

    def _merge_concatenate(self, sources: list[MergeSource]) -> MergedContent:
        """Merge by concatenating content with separators."""
        primary = sources[0]
        contents = []
        all_tags: set[str] = set()
        all_sources = []

        for source in sources:
            if source.content:
                contents.append(source.content.strip())
            all_tags.update(t.lower() for t in source.tags if isinstance(t, str))
            all_sources.append(source.url)

        merged_content = "\n\n---\n\n".join(contents) if contents else ""

        return MergedContent(
            url=primary.url,
            title=primary.title or self._best_title(sources),
            content=merged_content,
            tags=sorted(all_tags),
            metadata=self._merge_metadata(sources),
            source_count=len(sources),
            sources=all_sources,
            merge_strategy="concatenate",
        )

    def _merge_longest(self, sources: list[MergeSource]) -> MergedContent:
        """Use the longest content as the merged result."""
        longest = max(sources, key=lambda s: len(s.content))
        all_tags: set[str] = set()
        for source in sources:
            all_tags.update(t.lower() for t in source.tags if isinstance(t, str))

        return MergedContent(
            url=longest.url,
            title=longest.title or self._best_title(sources),
            content=longest.content,
            tags=sorted(all_tags),
            metadata=self._merge_metadata(sources),
            source_count=len(sources),
            sources=[s.url for s in sources],
            merge_strategy="longest",
        )

    def _merge_highest_priority(self, sources: list[MergeSource]) -> MergedContent:
        """Use content from the highest priority source."""
        primary = sources[0]  # Already sorted by priority
        all_tags: set[str] = set()
        for source in sources:
            all_tags.update(t.lower() for t in source.tags if isinstance(t, str))

        return MergedContent(
            url=primary.url,
            title=primary.title or self._best_title(sources),
            content=primary.content,
            tags=sorted(all_tags),
            metadata=self._merge_metadata(sources),
            source_count=len(sources),
            sources=[s.url for s in sources],
            merge_strategy="highest_priority",
        )

    def _merge_unique_paragraphs(self, sources: list[MergeSource]) -> MergedContent:
        """Merge paragraphs from all sources, deduped on a case-insensitive,
        whitespace-stripped paragraph text (para.strip().lower()). Paragraphs
        differing only in case or surrounding whitespace collapse to one."""
        primary = sources[0]
        seen_paragraphs: set[str] = set()
        merged_paragraphs: list[str] = []
        all_tags: set[str] = set()

        for source in sources:
            paragraphs = source.content.split("\n\n")
            for para in paragraphs:
                normalized = para.strip().lower()
                if normalized and normalized not in seen_paragraphs:
                    seen_paragraphs.add(normalized)
                    merged_paragraphs.append(para.strip())
            all_tags.update(t.lower() for t in source.tags if isinstance(t, str))

        merged_content = "\n\n".join(merged_paragraphs)

        return MergedContent(
            url=primary.url,
            title=primary.title or self._best_title(sources),
            content=merged_content,
            tags=sorted(all_tags),
            metadata=self._merge_metadata(sources),
            source_count=len(sources),
            sources=[s.url for s in sources],
            merge_strategy="unique_paragraphs",
        )

    def _best_title(self, sources: list[MergeSource]) -> str:
        """Get the best title from sources (longest non-empty)."""
        titled = [s for s in sources if s.title]
        if not titled:
            return ""
        return max(titled, key=lambda s: len(s.title)).title

    def _merge_metadata(self, sources: list[MergeSource]) -> dict[str, Any]:
        """Merge metadata from all sources, higher priority wins."""
        merged: dict[str, Any] = {}
        for source in sources:
            for key, value in source.metadata.items():
                if key not in merged:
                    merged[key] = value
        return merged
