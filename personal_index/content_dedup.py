"""
Content Deduplication Module
Remove duplicate content items.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List





class DocumentHash:
    """Computes document fingerprints using SHA256."""

    @staticmethod
    def compute_fingerprint(content: str) -> str:
        """Compute a 16-char fingerprint for content."""
        import hashlib
        return hashlib.sha256(content.encode()).hexdigest()[:16]

class CheckResult:
    """Result of a single item check."""
    def __init__(self, is_duplicate: bool, url: str):
        self.is_duplicate = is_duplicate
        self.url = url


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

    def _check_single_item(self, url: str, _title: str, content: str) -> CheckResult:
        """Check a single item for duplicates.
        
        Args:
            url: The URL of the item
            _title: Unused parameter (kept for compatibility)
            content: The content to check
            
        Returns:
            CheckResult with is_duplicate flag
        """
        # Compute hash from content only
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        is_dup = content_hash in self._seen_hashes
        if not is_dup:
            self._seen_hashes.add(content_hash)
        return CheckResult(is_duplicate=is_dup, url=url)

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
