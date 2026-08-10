"""Tag/label system for organizing indexed pages."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Tag:
    """A tag that can be applied to pages."""
    name: str
    color: str = "#3498db"
    description: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, Tag):
            return self.name == other.name
        return False


@dataclass
class TagStore:
    """Persistent storage for tags and their page associations."""

    store_path: str | None = None
    _tags: dict[str, Tag] = field(default_factory=dict, repr=False)
    _page_tags: dict[str, set[str]] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        if self.store_path and os.path.exists(self.store_path):
            self._load()

    def _load(self) -> None:
        """Load tags from file."""
        if not self.store_path:
            return
        try:
            with open(self.store_path, "r") as f:
                data = json.load(f)
            for name, tag_data in data.get("tags", {}).items():
                self._tags[name] = Tag(
                    name=name,
                    color=tag_data.get("color", "#3498db"),
                    description=tag_data.get("description", ""),
                    created_at=tag_data.get("created_at", ""),
                )
            self._page_tags = data.get("page_tags", {})
            # Convert lists back to sets
            for url, tags in self._page_tags.items():
                self._page_tags[url] = set(tags)
        except (json.JSONDecodeError, KeyError, TypeError):
            self._tags = {}
            self._page_tags = {}

    def _save(self) -> None:
        """Save tags to file."""
        if not self.store_path:
            return
        parent = Path(self.store_path).parent
        parent.mkdir(parents=True, exist_ok=True)
        data = {
            "tags": {
                name: {
                    "name": tag.name,
                    "color": tag.color,
                    "description": tag.description,
                    "created_at": tag.created_at,
                }
                for name, tag in self._tags.items()
            },
            "page_tags": {
                url: list(tags) for url, tags in self._page_tags.items()
            },
        }
        with open(self.store_path, "w") as f:
            json.dump(data, f, indent=2)

    def create_tag(self, name: str, color: str = "#3498db", description: str = "") -> Tag:
        """Create a new tag."""
        tag = Tag(name=name, color=color, description=description)
        self._tags[name] = tag
        self._save()
        return tag

    def get_tag(self, name: str) -> Tag | None:
        """Get a tag by name."""
        return self._tags.get(name)

    def list_tags(self) -> list[Tag]:
        """List all tags."""
        return list(self._tags.values())

    def delete_tag(self, name: str) -> bool:
        """Delete a tag and remove it from all pages."""
        if name not in self._tags:
            return False
        del self._tags[name]
        for url in self._page_tags:
            self._page_tags[url].discard(name)
        self._save()
        return True

    def add_tag_to_page(self, url: str, tag_name: str) -> bool:
        """Add a tag to a page. Returns False if tag doesn't exist."""
        if tag_name not in self._tags:
            return False
        if url not in self._page_tags:
            self._page_tags[url] = set()
        self._page_tags[url].add(tag_name)
        self._save()
        return True

    def remove_tag_from_page(self, url: str, tag_name: str) -> bool:
        """Remove a tag from a page."""
        if url not in self._page_tags:
            return False
        # removed = self._page_tags[url].discard(tag_name)
        self._save()
        return True

    def get_tags_for_page(self, url: str) -> list[Tag]:
        """Get all tags for a page."""
        tag_names = self._page_tags.get(url, set())
        return [self._tags[name] for name in tag_names if name in self._tags]

    def get_pages_for_tag(self, tag_name: str) -> list[str]:
        """Get all pages with a specific tag."""
        if tag_name not in self._tags:
            return []
        return [url for url, tags in self._page_tags.items() if tag_name in tags]

    def search_by_tag(self, tag_name: str) -> list[str]:
        """Search for pages by tag name (alias for get_pages_for_tag)."""
        return self.get_pages_for_tag(tag_name)

    def get_tag_count(self) -> int:
        """Get total number of tags."""
        return len(self._tags)

    def get_tagged_page_count(self) -> int:
        """Get number of pages that have at least one tag."""
        return sum(1 for tags in self._page_tags.values() if tags)

    def clear(self) -> None:
        """Clear all tags and associations."""
        self._tags.clear()
        self._page_tags.clear()
        self._save()
