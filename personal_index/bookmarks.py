"""Bookmark management for personal index."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Bookmark:
    """A single bookmark entry."""
    url: str
    title: str = ""
    description: str = ""
    category: str = "uncategorized"
    tags: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    is_favorite: bool = False

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_favorite": self.is_favorite,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Bookmark:
        """Create from dictionary."""
        return cls(
            url=data["url"],
            title=data.get("title", ""),
            description=data.get("description", ""),
            category=data.get("category", "uncategorized"),
            tags=data.get("tags", []),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            is_favorite=data.get("is_favorite", False),
        )


class BookmarkManager:
    """Manage bookmarks for the personal index."""

    def __init__(self, storage_path: str | None = None):
        self._bookmarks: dict[str, Bookmark] = {}
        self._storage_path = storage_path

    def add(self, bookmark: Bookmark) -> Bookmark:
        """Add a bookmark, updating if URL already exists."""
        now = datetime.now(timezone.utc).isoformat()
        if bookmark.url in self._bookmarks:
            existing = self._bookmarks[bookmark.url]
            bookmark.created_at = existing.created_at
        bookmark.updated_at = now
        self._bookmarks[bookmark.url] = bookmark
        return bookmark

    def get(self, url: str) -> Bookmark | None:
        """Get a bookmark by URL."""
        return self._bookmarks.get(url)

    def remove(self, url: str) -> bool:
        """Remove a bookmark by URL. Returns True if removed."""
        if url in self._bookmarks:
            del self._bookmarks[url]
            return True
        return False

    def list_all(self) -> list[Bookmark]:
        """List all bookmarks."""
        return list(self._bookmarks.values())

    def list_by_category(self, category: str) -> list[Bookmark]:
        """List bookmarks in a category."""
        return [b for b in self._bookmarks.values() if b.category == category]

    def list_by_tag(self, tag: str) -> list[Bookmark]:
        """List bookmarks with a specific tag."""
        return [b for b in self._bookmarks.values() if tag in b.tags]

    def list_favorites(self) -> list[Bookmark]:
        """List favorite bookmarks."""
        return [b for b in self._bookmarks.values() if b.is_favorite]

    def toggle_favorite(self, url: str) -> Bookmark | None:
        """Toggle favorite status of a bookmark."""
        bookmark = self._bookmarks.get(url)
        if bookmark:
            bookmark.is_favorite = not bookmark.is_favorite
            bookmark.updated_at = datetime.now(timezone.utc).isoformat()
        return bookmark

    def search(self, query: str) -> list[Bookmark]:
        """Search bookmarks by title, description, or URL."""
        query_lower = query.lower()
        results = []
        for b in self._bookmarks.values():
            if (query_lower in b.title.lower() or
                query_lower in b.description.lower() or
                query_lower in b.url.lower()):
                results.append(b)
        return results

    def get_categories(self) -> list[str]:
        """Get all unique categories."""
        categories = set()
        for b in self._bookmarks.values():
            categories.add(b.category)
        return sorted(categories)

    def get_all_tags(self) -> list[str]:
        """Get all unique tags."""
        tags = set()
        for b in self._bookmarks.values():
            tags.update(b.tags)
        return sorted(tags)

    def count(self) -> int:
        """Count total bookmarks."""
        return len(self._bookmarks)

    def save(self, path: str | None = None) -> str:
        """Save bookmarks to JSON file."""
        save_path = path or self._storage_path
        if not save_path:
            raise ValueError("No storage path specified")
        data = [b.to_dict() for b in self._bookmarks.values()]
        with open(save_path, "w") as f:
            json.dump(data, f, indent=2)
        return save_path

    def load(self, path: str | None = None) -> int:
        """Load bookmarks from a JSON file and return the count loaded.

        Raises ValueError when neither ``path`` nor the configured
        storage path is set. Returns 0 without touching the current
        set when the file is missing, the JSON is malformed
        (``JSONDecodeError``), or the top-level JSON value is not a
        list. Otherwise replaces the current set with the loaded
        bookmarks and returns the number loaded.
        """
        load_path = path or self._storage_path
        if not load_path:
            raise ValueError("No storage path specified")
        path_obj = Path(load_path)
        if not path_obj.exists():
            return 0
        with open(path_obj) as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                return 0
        if not isinstance(data, list):
            return 0
        self._bookmarks.clear()
        for item in data:
            bookmark = Bookmark.from_dict(item)
            self._bookmarks[bookmark.url] = bookmark
        return len(self._bookmarks)
