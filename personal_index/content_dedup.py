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

    Removes trailing slashes and fragments, and lowercases the
    scheme and host.
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


class DocumentHash:
    """Content fingerprinting using sha256."""

    @staticmethod
    def compute_fingerprint(content: str) -> str:
        """Compute a 16-char fingerprint for content."""
        return content_hash(content)[:16]


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
    is_duplicate: bool = False

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

        Groups items by the sha256 hash of ``item.get(hash_field, "")``
        (``hash_field`` defaults to ``"content"``). Items whose content hash
        is empty (empty content) are skipped and never grouped. A
        ``DuplicateGroup`` is built only for a hash group holding more than
        one item: its ``representative`` is the first item's ``url``,
        ``duplicates`` are the remaining items' ``url`` values,
        ``similarity_score`` is 1.0 and ``dedup_method`` is ``"exact_hash"``.

        Returns a ``DedupResult`` with ``total_items=len(items)``,
        ``unique_items=len(items) - removed``, ``duplicate_groups`` the built
        groups, ``removed_count`` the number of removed duplicates and
        ``method="hash"``.
        """
        hash_groups = self._group_by_hash(items, hash_field)
        groups, removed = self._build_dup_groups(hash_groups)
        return DedupResult(
            total_items=len(items),
            unique_items=len(items) - removed,
            duplicate_groups=groups,
            removed_count=removed,
            method="hash",
        )

    def _group_by_hash(
        self, items: list[dict[str, Any]], field: str
    ) -> dict[str, list[dict[str, Any]]]:
        """Group items by content hash."""
        groups: dict[str, list[dict[str, Any]]] = {}
        for item in items:
            h = content_hash(item.get(field, ""))
            if h:
                groups.setdefault(h, []).append(item)
        return groups

    @staticmethod
    def _build_dup_groups(
        hash_groups: dict[str, list[dict[str, Any]]]
    ) -> tuple[list[DuplicateGroup], int]:
        """Build duplicate groups from hash groups."""
        groups: list[DuplicateGroup] = []
        removed = 0
        for group in hash_groups.values():
            if len(group) > 1:
                groups.append(DuplicateGroup(
                    representative=group[0].get("url", ""),
                    duplicates=[g.get("url", "") for g in group[1:]],
                    similarity_score=1.0,
                    dedup_method="exact_hash",
                ))
                removed += len(group) - 1
        return groups, removed

    def dedup_by_url(
        self,
        items: list[dict[str, Any]],
    ) -> DedupResult:
        """Deduplicate items by normalized URL.

        Groups items by ``normalize_url(item["url"])`` (trailing slash and
        fragment removed, scheme and host lowercased). Items whose normalized
        URL is empty are SKIPPED and never grouped (an empty URL cannot be
        deduplicated by URL, mirroring the ``if h:`` guard in
        ``_group_by_hash``). Only groups with more than one item become a
        ``DuplicateGroup``: ``representative`` is the first item's raw url,
        ``duplicates`` are the remaining raw urls, ``similarity_score`` is
        1.0 and ``dedup_method`` is ``"normalized_url"``.

        Args:
            items: List of content item dicts.

        Returns:
            DedupResult with ``total_items=len(items)``,
            ``unique_items=len(items) - removed_count``,
            ``duplicate_groups`` (the >1-item groups), ``removed_count``
            (sum of ``len(duplicates)`` over groups) and ``method="url"``.
        """
        url_groups: dict[str, list[dict[str, Any]]] = {}

        for item in items:
            url = item.get("url", "")
            normalized = normalize_url(url)
            # Skip items with no URL: an empty URL cannot be deduplicated by
            # URL, so it must not be grouped (mirrors the `if h:` guard in
            # _group_by_hash for empty content).
            if not normalized:
                continue
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
        """Deduplicate items by content similarity (Jaccard word overlap).

        Iterates items in order; for each unvisited seed ``i`` it calls
        ``_find_similarity_group``, which compares item ``i``'s
        ``compare_field`` text against every LATER item ``j`` and groups
        those whose ``text_similarity`` is >= ``self.similarity_threshold``
        (earlier items are never re-scanned). Only groups with >1 item
        become a ``DuplicateGroup`` (representative = first url,
        duplicates = remaining urls, similarity_score =
        ``self.similarity_threshold``, dedup_method="similarity");
        ``removed_count`` += len(group) - 1.

        An empty or missing ``compare_field`` text yields
        ``text_similarity`` 0.0, so such items never group (guard path:
        they stay unique).

        Returns:
            DedupResult(total_items=len(items),
                unique_items=len(items) - removed,
                duplicate_groups=groups, removed_count=removed,
                method="similarity").
        """
        n = len(items)
        visited: set[int] = set()
        groups: list[DuplicateGroup] = []
        removed = 0

        for i in range(n):
            if i in visited:
                continue
            group = self._find_similarity_group(items, i, compare_field, visited)
            if len(group) > 1:
                groups.append(DuplicateGroup(
                    representative=group[0],
                    duplicates=group[1:],
                    similarity_score=self.similarity_threshold,
                    dedup_method="similarity",
                ))
                removed += len(group) - 1

        return DedupResult(
            total_items=len(items),
            unique_items=len(items) - removed,
            duplicate_groups=groups,
            removed_count=removed,
            method="similarity",
        )

    def _find_similarity_group(
        self,
        items: list[dict[str, Any]],
        seed: int,
        compare_field: str,
        visited: set[int],
    ) -> list[str]:
        """Find all items similar to the seed item."""
        visited.add(seed)
        group_urls = [items[seed].get("url", "")]
        text_a = items[seed].get(compare_field, "")

        for j in range(seed + 1, len(items)):
            if j in visited:
                continue
            text_b = items[j].get(compare_field, "")
            if text_similarity(text_a, text_b) >= self.similarity_threshold:
                group_urls.append(items[j].get("url", ""))
                visited.add(j)

        return group_urls

    def _check_single_item(
        self,
        url: str,
        _title: str,
        content: str,
    ) -> DedupResult:
        """Check a single item for duplication."""
        if not hasattr(self, '_seen_hashes'):
            self._seen_hashes: dict[str, str] = {}
        h = content_hash(content)
        if h in self._seen_hashes:
            return self._dup_result(url, h)
        self._seen_hashes[h] = url
        return self._unique_result()

    def _dup_result(self, url: str, h: str) -> DedupResult:
        """Build DedupResult for a duplicate item."""
        return DedupResult(
            total_items=1, unique_items=0,
            duplicate_groups=[DuplicateGroup(
                representative=self._seen_hashes[h],
                duplicates=[url],
                similarity_score=1.0,
                dedup_method="exact_hash",
            )],
            removed_count=1, method="hash", is_duplicate=True,
        )

    @staticmethod
    def _unique_result() -> DedupResult:
        """Build DedupResult for a unique item."""
        return DedupResult(
            total_items=1, unique_items=1,
            duplicate_groups=[], removed_count=0,
            method="hash", is_duplicate=False,
        )

    def dedup_all(
        self,
        items: list[dict[str, Any]],
    ) -> DedupResult:
        """Run URL dedup then content-hash dedup and combine the two results.

        Pipeline (two stages, in order):
          1. ``url_result = self.dedup_by_url(items)`` on the FULL input list.
          2. Rebuild ``unique_items`` by keeping the FIRST item per
             ``normalize_url(item.get("url", ""))``. Items whose URL normalizes
             to the empty string all share the same empty key, so only the
             FIRST empty-URL item survives this stage.
          3. ``hash_result = self.dedup_by_hash(unique_items)`` on that reduced
             list (NOT on ``url_result.unique_items``).

        Combine:
          * ``duplicate_groups = url_result.duplicate_groups +
            hash_result.duplicate_groups``
          * ``removed_count = url_result.removed_count +
            hash_result.removed_count``

        Args:
            items: List of content item dicts.

        Returns:
            A ``DedupResult`` with ``total_items=len(items)``,
            ``unique_items=len(items) - removed_count``, the combined
            ``duplicate_groups``, the summed ``removed_count`` and
            ``method="combined"``.
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
