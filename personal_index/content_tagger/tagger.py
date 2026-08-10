"""High-level content tagging interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from personal_index.content_tagger.detector import TopicDetector
from personal_index.content_tagger.tag import Tag


@dataclass
class TagResult:
    """Result of tagging content."""

    content: str
    tags: list[Tag] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "tags": [t.to_dict() for t in self.tags],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TagResult:
        tags = [Tag.from_dict(t) for t in data.get("tags", [])]
        return cls(content=data.get("content", ""), tags=tags)


class ContentTagger:
    """High-level interface for tagging content by detected topics."""

    TagResult = TagResult  # type: ignore[misc]  # Expose for ContentTagger.TagResult access

    def __init__(self) -> None:
        self._detector = TopicDetector()
        self._tag_stats: dict[str, int] = {}

    def tag(self, content: str, min_confidence: float = 0.0) -> TagResult:  # type: ignore[type-arg]
        """Tag content by detecting topics."""
        if not content or not content.strip():
            return TagResult(content=content, tags=[])

        tags = self._detector.detect(content)
        tags = [t for t in tags if t.confidence >= min_confidence]

        for tag in tags:
            self._tag_stats[tag.name] = self._tag_stats.get(tag.name, 0) + 1

        return TagResult(content=content, tags=tags)

    def batch_tag(self, contents: list[str]) -> list[TagResult]:  # type: ignore[type-arg]
        """Tag multiple pieces of content."""
        return [self.tag(c) for c in contents]

    def get_tag_statistics(self) -> dict[str, int]:
        """Return tag usage statistics."""
        return dict(self._tag_stats)

    def add_topic(self, name: str, keywords: list[str]) -> None:
        """Add a custom topic to the detector."""
        self._detector.add_topic(name, keywords)

    def clear_statistics(self) -> None:
        """Clear tag usage statistics."""
        self._tag_stats.clear()
