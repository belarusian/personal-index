"""Content tags module - tag management with autocomplete."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set


@dataclass
class Tag:
    """A tag that can be applied to content items."""

    name: str
    color: str = "#3498db"
    description: str = ""
    usage_count: int = 0
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self) -> None:
        """Normalize tag name: strip whitespace and lowercase."""
        self.name = self.name.strip().lower()

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, Tag):
            return self.name == other.name
        return False

    def __repr__(self) -> str:
        return f"Tag(name={self.name!r}, color={self.color!r})"

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "color": self.color,
            "description": self.description,
            "usage_count": self.usage_count,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Tag":
        """Deserialize from dictionary."""
        return cls(
            name=data.get("name", ""),
            color=data.get("color", "#3498db"),
            description=data.get("description", ""),
            usage_count=data.get("usage_count", 0),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
        )


@dataclass
class TagAutocompleteResult:
    """Result of a tag autocomplete query."""

    suggestions: List[str] = field(default_factory=list)
    exact_match: Optional[str] = None
    partial_matches: List[str] = field(default_factory=list)
    popular_tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "suggestions": self.suggestions,
            "exact_match": self.exact_match,
            "partial_matches": self.partial_matches,
            "popular_tags": self.popular_tags,
        }


class TagStore:
    """Manages tags with autocomplete support."""

    def __init__(self) -> None:
        self._tags: Dict[str, Tag] = {}
        self._content_tags: Dict[str, Set[str]] = {}
        self._tag_content: Dict[str, Set[str]] = {}

    def create_tag(self, name: str, color: str = "#3498db", description: str = "") -> Tag:
        """Create a new tag."""
        tag = Tag(name=name, color=color, description=description)
        self._tags[tag.name] = tag
        return tag

    def get_tag(self, name: str) -> Optional[Tag]:
        """Get a tag by name."""
        return self._tags.get(name.strip().lower())

    def list_tags(self, sort_by: str = "name") -> List[Tag]:
        """List all tags, optionally sorted."""
        tags = list(self._tags.values())
        if sort_by == "usage_count":
            tags.sort(key=lambda t: t.usage_count, reverse=True)
        elif sort_by == "name":
            tags.sort(key=lambda t: t.name)
        return tags

    def delete_tag(self, name: str) -> bool:
        """Delete a tag."""
        name = name.strip().lower()
        if name not in self._tags:
            return False
        del self._tags[name]
        if name in self._tag_content:
            del self._tag_content[name]
        for content_id in self._content_tags:
            self._content_tags[content_id].discard(name)
        return True

    def add_tag_to_content(self, content_id: str, tag_name: str) -> bool:
        """Add a tag to a content item."""
        tag_name = tag_name.strip().lower()
        if tag_name not in self._tags:
            return False
        if content_id not in self._content_tags:
            self._content_tags[content_id] = set()
        self._content_tags[content_id].add(tag_name)
        if tag_name not in self._tag_content:
            self._tag_content[tag_name] = set()
        self._tag_content[tag_name].add(content_id)
        self._tags[tag_name].usage_count += 1
        return True

    def remove_tag_from_content(self, content_id: str, tag_name: str) -> bool:
        """Remove a tag from a content item."""
        tag_name = tag_name.strip().lower()
        if content_id not in self._content_tags:
            return False
        if tag_name not in self._content_tags[content_id]:
            return False
        self._content_tags[content_id].discard(tag_name)
        if tag_name in self._tag_content:
            self._tag_content[tag_name].discard(content_id)
        if tag_name in self._tags:
            self._tags[tag_name].usage_count = max(0, self._tags[tag_name].usage_count - 1)
        return True

    def get_tags_for_content(self, content_id: str) -> List[Tag]:
        """Get all tags for a content item."""
        tag_names = self._content_tags.get(content_id, set())
        return [self._tags[name] for name in tag_names if name in self._tags]

    def get_content_for_tag(self, tag_name: str) -> List[str]:
        """Get all content IDs for a tag."""
        tag_name = tag_name.strip().lower()
        return list(self._tag_content.get(tag_name, set()))

    def autocomplete(self, query: str, limit: int = 10) -> TagAutocompleteResult:
        """Autocomplete tag suggestions based on query."""
        query = query.strip().lower()
        result = TagAutocompleteResult()

        if not query:
            result.popular_tags = [
                t.name for t in sorted(self._tags.values(), key=lambda t: t.usage_count, reverse=True)[:limit]
            ]
            return result

        # Check for exact match
        if query in self._tags:
            result.exact_match = query

        # Find partial matches
        partial = []
        for name in self._tags:
            if query in name and name != query:
                partial.append(name)
        partial.sort()
        result.partial_matches = partial[:limit]

        # Combine suggestions: exact match first, then partial, then popular
        suggestions = []
        if result.exact_match:
            suggestions.append(result.exact_match)
        for m in result.partial_matches:
            if m not in suggestions:
                suggestions.append(m)
        # Add popular tags that start with query
        for tag in sorted(self._tags.values(), key=lambda t: t.usage_count, reverse=True):
            if tag.name.startswith(query) and tag.name not in suggestions:
                suggestions.append(tag.name)
            if len(suggestions) >= limit:
                break
        result.suggestions = suggestions[:limit]

        return result

    def get_tag_count(self) -> int:
        """Get total number of tags."""
        return len(self._tags)

    def get_tagged_content_count(self) -> int:
        """Get number of content items with at least one tag."""
        return len(self._content_tags)

    def merge_tags(self, source_name: str, target_name: str) -> bool:
        """Merge source tag into target tag."""
        source_name = source_name.strip().lower()
        target_name = target_name.strip().lower()
        if source_name not in self._tags:
            return False
        if target_name not in self._tags:
            self.create_tag(target_name)
        # Move all content from source to target
        for content_id in list(self._tag_content.get(source_name, set())):
            if content_id in self._content_tags:
                self._content_tags[content_id].discard(source_name)
                self._content_tags[content_id].add(target_name)
            if target_name not in self._tag_content:
                self._tag_content[target_name] = set()
            self._tag_content[target_name].add(content_id)
        # Update usage count
        self._tags[target_name].usage_count += self._tags[source_name].usage_count
        # Delete source
        del self._tags[source_name]
        if source_name in self._tag_content:
            del self._tag_content[source_name]
        return True

    def rename_tag(self, old_name: str, new_name: str) -> bool:
        """Rename a tag."""
        old_name = old_name.strip().lower()
        new_name = new_name.strip().lower()
        if old_name not in self._tags:
            return False
        if new_name in self._tags:
            return self.merge_tags(old_name, new_name)
        tag = self._tags.pop(old_name)
        tag.name = new_name
        self._tags[new_name] = tag
        # Update content mappings
        if old_name in self._tag_content:
            self._tag_content[new_name] = self._tag_content.pop(old_name)
        for content_id in self._content_tags:
            if old_name in self._content_tags[content_id]:
                self._content_tags[content_id].discard(old_name)
                self._content_tags[content_id].add(new_name)
        return True

    def get_stats(self) -> dict:
        """Get tag statistics."""
        return {
            "total_tags": len(self._tags),
            "tagged_content": len(self._content_tags),
            "most_used": [
                {"name": t.name, "count": t.usage_count}
                for t in sorted(self._tags.values(), key=lambda t: t.usage_count, reverse=True)[:10]
            ],
        }

    def clear(self) -> None:
        """Remove all tags and associations."""
        self._tags.clear()
        self._content_tags.clear()
        self._tag_content.clear()
