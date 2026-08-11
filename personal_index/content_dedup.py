"""
Content Deduplication Module
Remove duplicate content items.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List


class ContentDeduplicator:
    """Removes duplicates from content items."""

    def __init__(self):
        self._seen_hashes: set = set()

    def _compute_hash(self, item: Dict[str, Any]) -> str:
        """Compute hash for an item based on title and description."""
        title = str(item.get("title", "")).strip().lower()
        desc = str(item.get("description", "")).strip().lower()
        content = f"{title}:{desc}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def deduplicate(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicates from a list of items."""
        unique = []
        for item in items:
            item_hash = self._compute_hash(item)
            if item_hash not in self._seen_hashes:
                self._seen_hashes.add(item_hash)
                unique.append(item)
        return unique

    def is_duplicate(self, item: Dict[str, Any]) -> bool:
        """Check if an item is a duplicate."""
        item_hash = self._compute_hash(item)
        return item_hash in self._seen_hashes

    def mark_seen(self, item: Dict[str, Any]) -> None:
        """Mark an item as seen."""
        self._seen_hashes.add(self._compute_hash(item))

    def clear_seen(self) -> None:
        """Clear the seen hashes."""
        self._seen_hashes.clear()

    @property
    def seen_count(self) -> int:
        return len(self._seen_hashes)


class DedupFilter:
    """Filter that removes duplicates from content streams."""

    def __init__(self):
        self._seen: set = set()

    def filter(self, items: List[Dict[str, Any]], key: str = "id") -> List[Dict[str, Any]]:
        """Remove duplicates based on a key field."""
        unique = []
        for item in items:
            k = item.get(key)
            if k is not None and k not in self._seen:
                self._seen.add(k)
                unique.append(item)
        return unique

    def clear(self) -> None:
        """Clear seen values."""
        self._seen.clear()
