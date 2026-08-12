"""Content deduplication for personal-index.

Detects and removes duplicate content using hash-based comparison,
similarity scoring, and URL normalization.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DuplicateGroup:
    """A group of duplicate content items."""
    representative: str  # URL of the representative (best) item
    duplicates: list[str] = field(default_factory=list)
    similarity_score: float = 1.0
    dedup_method: str = "exact"

    @property
    def total_count(self) -> int:
        return 1 + len(self.duplicates)

    def to_dict(self) -> dict[str, Any]:
        return {
            "representative": self.representative,
            "duplicates": self.duplicates,
            "similarity_score": self.similarity_score,
            "dedup_method": self.dedup_method,
            "total_count": self.total_count,
        }


def normalize_url(url: str) -> str:
    """Normalize a URL for comparison.

    Removes trailing slashes, fragments, and normalizes case.
    """
    if not url:
        return url
    # Remove fragment
    url = url.split("#")[0]
    # Remove trailing slash (but keep root /)
    if len(url) > 1 and url.endswith("/"):
        url = url.rstrip("/")
    # Normalize scheme and host to lowercase
    parts = url.split("://", 1)
    if len(parts) == 2:
        scheme, rest = parts
        host_path = rest.split("/", 1)
        if len(host_path) == 2:
            rest = host_path[0].lower() + "/" + host_path[1]
        else:
            rest = host_path[0].lower()
        url = scheme.lower() + "://" + rest
    return url


def content_hash(text: str) -> str:
    """Generate a hash of content text."""
    if not text:
        return ""
    # Normalize whitespace
    normalized = re.sub(r'\s+', ' ', text.lower().strip())
    return hashlib.sha256(normalized.encode()).hexdigest()


def url_hash(url: str) -> str:
    """Generate a hash of a normalized URL."""
    return hashlib.sha256(normalize_url(url).encode()).hexdigest()


def text_similarity(text_a: str, text_b: str) -> float:
    """Calculate similarity between two texts using word overlap.

    Uses Jaccard similarity on word sets.
    """
    if not text_a or not text_b:
        return 0.0

    words_a = set(re.findall(r'[a-z0-9]+', text_a.lower()))
    words_b = set(re.findall(r'[a-z0-9]+', text_b.lower()))

    if not words_a or not words_b:
        return 0.0

    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


@dataclass
class DedupResult:
    """Result of a deduplication operation."""
    total_items: int = 0
    unique_items: int = 0
    duplicate_groups: list[DuplicateGroup] = field(default_factory=list)
    removed_count: int = 0
    method: str = "hash"

    @property
    def dedup_ratio(self) -> float:
        """Ratio of duplicates to total items."""
        if self.total_items == 0:
            return 0.0
        return self.removed_count / self.total_items

    def summary(self) -> str:
        """Generate a human-readable summary."""
        return (
            f"Deduplication Results:\n"
            f"  Total items: {self.total_items}\n"
            f"  Unique items: {self.unique_items}\n"
            f"  Duplicates found: {self.removed_count}\n"
            f"  Duplicate groups: {len(self.duplicate_groups)}\n"
            f"  Dedup ratio: {self.dedup_ratio:.1%}\n"
            f"  Method: {self.method}"
        )


class ContentDeduplicator:
    """Deduplicates content items using various strategies.

    Supports exact hash matching, URL normalization, and
    similarity-based deduplication.
    """

    def __init__(self, similarity_threshold: float = 0.9):
        self.similarity_threshold = similarity_threshold

    def dedup_by_hash(
        self,
        items: list[dict[str, Any]],
        hash_field: str = "content",
    ) -> DedupResult:
        """Deduplicate items by content hash.

        Args:
            items: List of content item dicts.
            hash_field: Field to hash for comparison.

        Returns:
            DedupResult with duplicate groups.
        """
        hash_groups: dict[str, list[dict[str, Any]]] = {}

        for item in items:
            text = item.get(hash_field, "")
            h = content_hash(text)
            if h:
                hash_groups.setdefault(h, []).append(item)

        groups = []
        removed = 0
        for h, group in hash_groups.items():
            if len(group) > 1:
                representative = group[0].get("url", "")
                duplicates = [g.get("url", "") for g in group[1:]]
                groups.append(DuplicateGroup(
                    representative=representative,
                    duplicates=duplicates,
                    similarity_score=1.0,
                    dedup_method="exact_hash",
                ))
                removed += len(duplicates)

        return DedupResult(
            total_items=len(items),
            unique_items=len(items) - removed,
            duplicate_groups=groups,
            removed_count=removed,
            method="hash",
        )

    def dedup_by_url(
        self,
        items: list[dict[str, Any]],
    ) -> DedupResult:
        """Deduplicate items by normalized URL.

        Args:
            items: List of content item dicts.

        Returns:
            DedupResult with duplicate groups.
        """
        url_groups: dict[str, list[dict[str, Any]]] = {}

        for item in items:
            url = item.get("url", "")
            normalized = normalize_url(url)
            url_groups.setdefault(normalized, []).append(item)

        groups = []
        removed = 0
        for normalized, group in url_groups.items():
            if len(group) > 1:
                representative = group[0].get("url", "")
                duplicates = [g.get("url", "") for g in group[1:]]
                groups.append(DuplicateGroup(
                    representative=representative,
                    duplicates=duplicates,
                    similarity_score=1.0,
                    dedup_method="normalized_url",
                ))
                removed += len(duplicates)

        return DedupResult(
            total_items=len(items),
            unique_items=len(items) - removed,
            duplicate_groups=groups,
            removed_count=removed,
            method="url",
        )

    def dedup_by_similarity(
        self,
        items: list[dict[str, Any]],
        compare_field: str = "content",
    ) -> DedupResult:
        """Deduplicate items by content similarity.

        Args:
            items: List of content item dicts.
            compare_field: Field to compare for similarity.

        Returns:
            DedupResult with duplicate groups.
        """
        n = len(items)
        visited = set()
        groups = []
        removed = 0

        for i in range(n):
            if i in visited:
                continue
            group_urls = [items[i].get("url", "")]
            visited.add(i)

            for j in range(i + 1, n):
                if j in visited:
                    continue

                text_a = items[i].get(compare_field, "")
                text_b = items[j].get(compare_field, "")
                similarity = text_similarity(text_a, text_b)

                if similarity >= self.similarity_threshold:
                    group_urls.append(items[j].get("url", ""))
                    visited.add(j)

            if len(group_urls) > 1:
                groups.append(DuplicateGroup(
                    representative=group_urls[0],
                    duplicates=group_urls[1:],
                    similarity_score=self.similarity_threshold,
                    dedup_method="similarity",
                ))
                removed += len(group_urls) - 1

        return DedupResult(
            total_items=len(items),
            unique_items=len(items) - removed,
            duplicate_groups=groups,
            removed_count=removed,
            method="similarity",
        )

    def _check_single_item(
        self,
        url: str,
        _title: str,
        content: str,
    ) -> DedupResult:
        """Check a single item for duplication.

        Args:
            url: Content URL.
            _title: Content title (unused, kept for API compatibility).
            content: Content text to check for duplicates.

        Returns:
            DedupResult indicating whether the item is a duplicate.
        """
        h = content_hash(content)
        if not hasattr(self, '_seen_hashes'):
            self._seen_hashes: dict[str, str] = {}

        if h in self._seen_hashes:
            return DedupResult(
                total_items=1,
                unique_items=0,
                duplicate_groups=[DuplicateGroup(
                    representative=self._seen_hashes[h],
                    duplicates=[url],
                    similarity_score=1.0,
                    dedup_method="exact_hash",
                )],
                removed_count=1,
                method="hash",
            )

        self._seen_hashes[h] = url
        return DedupResult(
            total_items=1,
            unique_items=1,
            duplicate_groups=[],
            removed_count=0,
            method="hash",
        )

    def dedup_all(
        self,
        items: list[dict[str, Any]],
    ) -> DedupResult:
        """Run all deduplication strategies and combine results.

        Args:
            items: List of content item dicts.

        Returns:
            Combined DedupResult.
        """
        # First dedup by URL (exact matches)
        url_result = self.dedup_by_url(items)

        # Get unique items after URL dedup
        seen_urls = set()
        unique_items = []
        for item in items:
            normalized = normalize_url(item.get("url", ""))
            if normalized not in seen_urls:
                seen_urls.add(normalized)
                unique_items.append(item)

        # Then dedup by content hash
        hash_result = self.dedup_by_hash(unique_items)

        # Combine groups
        all_groups = url_result.duplicate_groups + hash_result.duplicate_groups
        total_removed = url_result.removed_count + hash_result.removed_count

        return DedupResult(
            total_items=len(items),
            unique_items=len(items) - total_removed,
            duplicate_groups=all_groups,
            removed_count=total_removed,
            method="combined",
        )
