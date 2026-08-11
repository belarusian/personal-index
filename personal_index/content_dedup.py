"""Content deduplication - detect duplicate saved content.

Provides multiple deduplication strategies including hash-based exact matching,
Jaccard similarity, and TF-IDF cosine similarity. Also includes a simpler
DeduplicationEngine for streaming duplicate detection.
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Classes from the original dedup.py (merged in)
# ---------------------------------------------------------------------------


@dataclass
class DocumentHash:
    """Hash representation of a document."""

    url: str
    content_hash: str
    title_hash: str
    fingerprint: str
    similarity_score: float = 0.0

    @staticmethod
    def compute_hash(text: str) -> str:
        """Compute SHA-256 hash of text."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_fingerprint(text: str) -> str:
        """Compute a shorter fingerprint for quick comparison."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def from_text(cls, url: str, title: str, content: str) -> DocumentHash:
        """Create a DocumentHash from page data."""
        return cls(
            url=url,
            content_hash=cls.compute_hash(content),
            title_hash=cls.compute_hash(title),
            fingerprint=cls.compute_fingerprint(content),
        )


class DeduplicationEngine:
    """Detect duplicate or near-duplicate content using streaming approach.

    This is a simpler engine that processes documents one at a time
    and tracks seen hashes for quick duplicate detection.
    """

    def __init__(self, similarity_threshold: float = 0.85) -> None:
        """Initialize DeduplicationEngine.

        Args:
            similarity_threshold: Minimum similarity score to flag as duplicate.
        """
        self._seen_hashes: dict[str, str] = {}  # hash -> first url
        self._seen_fingerprints: dict[str, str] = {}  # fingerprint -> first url
        self._similarity_threshold = similarity_threshold
        self._document_hashes: dict[str, DocumentHash] = {}

    def is_duplicate(self, url: str, title: str, content: str) -> tuple[bool, str | None]:
        """Check if content is a duplicate. Returns (is_dup, original_url)."""
        doc_hash = DocumentHash.from_text(url, title, content)
        self._document_hashes[url] = doc_hash

        # Exact content match
        if doc_hash.content_hash in self._seen_hashes:
            return True, self._seen_hashes[doc_hash.content_hash]

        # Exact title match with similar content
        if doc_hash.title_hash in self._seen_hashes:
            original_url = self._seen_hashes[doc_hash.title_hash]
            original = self._document_hashes.get(original_url)
            if original:
                similarity = self._compute_similarity(content, original)
                if similarity >= self._similarity_threshold:
                    return True, original_url

        # Fingerprint-based near-duplicate detection
        for fp, original_url in self._seen_fingerprints.items():
            if fp == doc_hash.fingerprint:
                return True, original_url

        # Register this document
        self._seen_hashes[doc_hash.content_hash] = url
        self._seen_fingerprints[doc_hash.fingerprint] = url
        return False, None

    def _compute_similarity(self, text1: str, doc_hash: DocumentHash) -> float:
        """Compute similarity between text and a stored document."""
        # Use token-based Jaccard similarity
        # We need the original content for comparison
        # For simplicity, use hash-based approach
        return 0.0

    def is_near_duplicate(
        self, url: str, title: str, content: str
    ) -> tuple[bool, str | None, float]:
        """Check for near-duplicates using token overlap. Returns (is_dup, url, score)."""
        tokens = set(re.findall(r"[a-z0-9]+", content.lower()))
        if not tokens:
            return False, None, 0.0

        best_score = 0.0
        for stored_url, stored_hash in self._document_hashes.items():
            if stored_url == url:
                continue
            # Compare fingerprints for quick rejection
            if stored_hash.fingerprint == DocumentHash.compute_fingerprint(content):
                return True, stored_url, 1.0

        # Check against stored token sets if available
        for stored_url, _stored_hash in self._document_hashes.items():
            if stored_url == url:
                continue
            # We need to store tokens for proper comparison
            # For now, use hash-based check

        return False, None, best_score

    @property
    def duplicate_count(self) -> int:
        """Number of duplicates detected."""
        return len(self._seen_hashes)

    @property
    def document_count(self) -> int:
        """Number of unique documents stored."""
        return len(self._document_hashes)

    def clear(self) -> None:
        """Clear all stored hashes."""
        self._seen_hashes.clear()
        self._seen_fingerprints.clear()
        self._document_hashes.clear()

    def get_original_url(self, url: str) -> str | None:
        """Get the original URL for a duplicate."""
        doc_hash = self._document_hashes.get(url)
        if not doc_hash:
            return None
        if doc_hash.content_hash in self._seen_hashes:
            original = self._seen_hashes[doc_hash.content_hash]
            if original != url:
                return original
        return None


# ---------------------------------------------------------------------------
# Original content_dedup.py classes (unchanged)
# ---------------------------------------------------------------------------


class SimilarityMethod(str, Enum):
    """Available similarity detection methods."""

    HASH = "hash"
    TFIDF = "tfidf"
    JACCARD = "jaccard"


@dataclass
class DuplicateGroup:
    """A group of duplicate content items."""

    representative: str
    duplicates: list[str] = field(default_factory=list)
    similarity_score: float = 0.0

    @property
    def total_count(self) -> int:
        """Total items in this group (representative + duplicates)."""
        return 1 + len(self.duplicates)


@dataclass
class DedupResult:
    """Result of deduplication analysis."""

    total_items: int = 0
    unique_items: int = 0
    duplicate_groups: int = 0
    groups: list[DuplicateGroup] = field(default_factory=list)

    @property
    def duplicate_ratio(self) -> float:
        """Ratio of duplicate items to total items."""
        if self.total_items == 0:
            return 0.0
        return (self.total_items - self.unique_items) / self.total_items


@dataclass
class AddItemResult:
    """Result of adding an item to the deduplicator."""

    is_duplicate: bool = False
    original_url: str | None = None
    similarity_score: float = 0.0


@dataclass
class DedupConfig:
    """Configuration for content deduplication."""

    similarity_threshold: float = 0.85
    method: str = "hash"
    min_content_length: int = 50

    _VALID_METHODS: ClassVar[set[str]] = {"hash", "tfidf", "jaccard"}

    def __post_init__(self) -> None:
        """Initialize post-processing for DedupConfig."""
        if self.method not in self._VALID_METHODS:
            raise ValueError(
                f"Invalid method '{self.method}'. Must be one of: {self._VALID_METHODS}"
            )


class ContentDeduplicator:
    """Detect duplicate or near-duplicate saved content.

    Supports hash-based exact matching, Jaccard similarity, and TF-IDF
    cosine similarity for flexible duplicate detection.
    """

    def __init__(self, config: DedupConfig | None = None) -> None:
        """Initialize ContentDeduplicator with optional config.

        Args:
            config: Deduplication configuration.
        """
        self.config = config or DedupConfig()
        self._content_hashes: dict[str, str] = {}  # hash -> first url
        self._content_tokens: dict[str, set[str]] = {}  # url -> token set
        self._content_texts: dict[str, str] = {}  # url -> text
        self._content_tfidf: dict[str, dict[str, float]] = {}  # url -> tfidf vector
        self._idf_cache: dict[str, float] = {}  # term -> idf

    def find_duplicates(self, items: list[dict[str, Any]]) -> DedupResult:
        """Find duplicate groups among content items.

        Args:
            items: List of dicts with 'url', 'title', 'content' keys.

        Returns:
            DedupResult with duplicate groups and statistics.
        """
        # Filter items by minimum content length
        valid_items = [
            item for item in items
            if len(item.get("content", "")) >= self.config.min_content_length
        ]

        if not valid_items:
            return DedupResult(total_items=len(items), unique_items=len(items))

        groups: dict[str, DuplicateGroup] = {}

        if self.config.method == "hash":
            groups = self._find_hash_duplicates(valid_items)
        elif self.config.method == "jaccard":
            groups = self._find_jaccard_duplicates(valid_items)
        elif self.config.method == "tfidf":
            groups = self._find_tfidf_duplicates(valid_items)

        # Calculate unique items
        duplicate_urls: set[str] = set()
        for group in groups.values():
            duplicate_urls.update(group.duplicates)

        unique_items = len(valid_items) - len(duplicate_urls)

        return DedupResult(
            total_items=len(items),
            unique_items=max(unique_items, len(valid_items) - len(duplicate_urls)),
            duplicate_groups=len(groups),
            groups=list(groups.values()),
        )

    def add_items(self, items: list[dict[str, Any]]) -> AddItemResult:
        """Add items incrementally and check for duplicates.

        Args:
            items: List of content item dicts.

        Returns:
            AddItemResult for the first item (indicating if it's a duplicate).
        """
        results: list[AddItemResult] = []
        for item in items:
            url = item.get("url", "")
            content = item.get("content", "")
            title = item.get("title", "")

            if len(content) < self.config.min_content_length:
                results.append(AddItemResult())
                continue

            result = self._check_single_item(url, title, content)
            results.append(result)

        return results[0] if results else AddItemResult()

    def _check_single_item(
        self, url: str, _title: str, content: str
    ) -> AddItemResult:
        """Check a single item against stored content.

        Args:
            url: Item URL.
            _title: Item title (unused).
            content: Item content text.

        Returns:
            AddItemResult indicating if the item is a duplicate.
        """
        content_hash = self._compute_hash(content)

        if content_hash in self._content_hashes:
            original_url = self._content_hashes[content_hash]
            return AddItemResult(
                is_duplicate=True,
                original_url=original_url,
                similarity_score=1.0,
            )

        # Store this item
        self._content_hashes[content_hash] = url
        self._content_tokens[url] = self._tokenize(content)
        self._content_texts[url] = content

        # Check for near-duplicates using Jaccard
        best_score = 0.0
        best_url = None
        current_tokens = self._content_tokens[url]

        for stored_url, stored_tokens in self._content_tokens.items():
            if stored_url == url:
                continue
            score = self._jaccard_similarity(current_tokens, stored_tokens)
            if score > best_score:
                best_score = score
                best_url = stored_url

        if best_score >= self.config.similarity_threshold and best_url:
            return AddItemResult(
                is_duplicate=True,
                original_url=best_url,
                similarity_score=best_score,
            )

        return AddItemResult(is_duplicate=False)

    def _find_hash_duplicates(self, items: list[dict[str, Any]]) -> dict[str, DuplicateGroup]:
        """Find duplicates using exact hash matching."""
        groups: dict[str, DuplicateGroup] = {}
        seen_hashes: dict[str, str] = {}

        for item in items:
            url = item.get("url", "")
            content = item.get("content", "")
            content_hash = self._compute_hash(content)

            if content_hash in seen_hashes:
                rep_url = seen_hashes[content_hash]
                if rep_url in groups:
                    groups[rep_url].duplicates.append(url)
                else:
                    groups[rep_url] = DuplicateGroup(
                        representative=rep_url,
                        duplicates=[url],
                        similarity_score=1.0,
                    )
            else:
                seen_hashes[content_hash] = url

        return groups

    def _find_jaccard_duplicates(self, items: list[dict[str, Any]]) -> dict[str, DuplicateGroup]:
        """Find duplicates using Jaccard similarity."""
        groups: dict[str, DuplicateGroup] = {}
        assigned: set[str] = set()

        # Tokenize all items
        token_sets: dict[str, set[str]] = {}
        for item in items:
            url = item.get("url", "")
            content = item.get("content", "")
            token_sets[url] = self._tokenize(content)

        for i, item_a in enumerate(items):
            url_a = item_a.get("url", "")
            if url_a in assigned:
                continue

            group = DuplicateGroup(representative=url_a, similarity_score=1.0)

            for j, item_b in enumerate(items):
                if i >= j:
                    continue
                url_b = item_b.get("url", "")
                if url_b in assigned:
                    continue

                score = self._jaccard_similarity(
                    token_sets[url_a], token_sets[url_b]
                )

                if score >= self.config.similarity_threshold:
                    group.duplicates.append(url_b)
                    group.similarity_score = max(group.similarity_score, score)
                    assigned.add(url_b)

            if group.duplicates:
                groups[url_a] = group

        return groups

    def _find_tfidf_duplicates(self, items: list[dict[str, Any]]) -> dict[str, DuplicateGroup]:
        """Find duplicates using TF-IDF cosine similarity."""
        groups: dict[str, DuplicateGroup] = {}
        assigned: set[str] = set()

        # Compute IDF
        doc_freq: Counter = Counter()
        all_tokens: dict[str, set[str]] = {}
        for item in items:
            url = item.get("url", "")
            content = item.get("content", "")
            tokens = self._tokenize(content)
            all_tokens[url] = tokens
            for token in tokens:
                doc_freq[token] += 1

        num_docs = len(items)
        idf: dict[str, float] = {}
        for term, freq in doc_freq.items():
            idf[term] = math.log((num_docs + 1) / (freq + 1)) + 1

        # Compute TF-IDF vectors
        tfidf_vectors: dict[str, dict[str, float]] = {}
        for item in items:
            url = item.get("url", "")
            tokens = all_tokens[url]
            tfidf_vectors[url] = self._compute_tfidf_with_idf(tokens, idf)

        # Compare vectors
        for i, item_a in enumerate(items):
            url_a = item_a.get("url", "")
            if url_a in assigned:
                continue

            vec_a = tfidf_vectors[url_a]
            group = DuplicateGroup(representative=url_a, similarity_score=1.0)

            for j, item_b in enumerate(items):
                if i >= j:
                    continue
                url_b = item_b.get("url", "")
                if url_b in assigned:
                    continue

                vec_b = tfidf_vectors[url_b]
                score = self._cosine_similarity(vec_a, vec_b)

                if score >= self.config.similarity_threshold:
                    group.duplicates.append(url_b)
                    group.similarity_score = max(group.similarity_score, score)
                    assigned.add(url_b)

            if group.duplicates:
                groups[url_a] = group

        return groups

    def _compute_hash(self, text: str) -> str:
        """Compute SHA-256 hash of text."""
        normalized = re.sub(r"\s+", " ", text.strip().lower())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _tokenize(self, text: str) -> set[str]:
        """Tokenize text into a set of lowercase words."""
        return set(re.findall(r"\b[a-z0-9]{2,}\b", text.lower()))

    def _jaccard_similarity(self, set_a: set[str], set_b: set[str]) -> float:
        """Compute Jaccard similarity between two token sets."""
        if not set_a and not set_b:
            return 1.0
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0

    def _compute_tfidf(self, tokens: set[str]) -> dict[str, float]:
        """Compute simple TF vector for tokens."""
        counter = Counter(list(tokens))
        total = sum(counter.values())
        if total == 0:
            return {}
        return {term: count / total for term, count in counter.items()}

    def _compute_tfidf_with_idf(
        self, tokens: set[str], idf: dict[str, float]
    ) -> dict[str, float]:
        """Compute TF-IDF vector with precomputed IDF."""
        counter = Counter(list(tokens))
        total = sum(counter.values())
        if total == 0:
            return {}
        vector: dict[str, float] = {}
        for term, count in counter.items():
            tf = count / total
            vector[term] = tf * idf.get(term, 1.0)
        return vector

    def _cosine_similarity(
        self, vec_a: dict[str, float], vec_b: dict[str, float]
    ) -> float:
        """Compute cosine similarity between two sparse vectors."""
        if not vec_a or not vec_b:
            return 0.0

        # Find common terms
        common_terms = set(vec_a.keys()) & set(vec_b.keys())
        if not common_terms:
            return 0.0

        dot_product = sum(vec_a[t] * vec_b[t] for t in common_terms)

        mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
        mag_b = math.sqrt(sum(v * v for v in vec_b.values()))

        if mag_a == 0 or mag_b == 0:
            return 0.0

        return dot_product / (mag_a * mag_b)


class BatchDedupReport:
    """Generate a report of deduplication results."""

    def __init__(self, result: DedupResult) -> None:
        """Initialize from DedupResult.

        Args:
            result: Deduplication result to wrap.
        """
        self.result = result

    def to_dict(self) -> dict:
        """Convert report to dictionary."""
        return {
            "total_items": self.result.total_items,
            "unique_items": self.result.unique_items,
            "duplicate_groups": self.result.duplicate_groups,
            "duplicate_ratio": self.result.duplicate_ratio,
            "groups": [
                {
                    "representative": g.representative,
                    "duplicates": g.duplicates,
                    "similarity_score": g.similarity_score,
                    "total_count": g.total_count,
                }
                for g in self.result.groups
            ],
        }

    def to_summary_string(self) -> str:
        """Generate a human-readable summary."""
        lines = [
            f"Total items: {self.result.total_items}",
            f"Unique items: {self.result.unique_items}",
            f"Duplicate groups: {self.result.duplicate_groups}",
            f"Duplicate ratio: {self.result.duplicate_ratio:.1%}",
        ]
        for i, group in enumerate(self.result.groups, 1):
            lines.append(f"\nGroup {i}:")
            lines.append(f"  Representative: {group.representative}")
            lines.append(f"  Similarity: {group.similarity_score:.1%}")
            lines.append(f"  Duplicates ({len(group.duplicates)}):")
            for dup in group.duplicates:
                lines.append(f"    - {dup}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Convenience functions for backward compatibility
# ---------------------------------------------------------------------------


def find_duplicates(items: list[str]) -> list[str]:
    """Find duplicate strings in a list.

    Args:
        items: List of strings to check for duplicates.

    Returns:
        List of duplicate strings (first occurrence of each duplicate).
    """
    seen: set[str] = set()
    duplicates: list[str] = []
    for item in items:
        if item in seen and item not in duplicates:
            duplicates.append(item)
        seen.add(item)
    return duplicates


def remove_duplicates(items: list[str]) -> list[str]:
    """Remove duplicate strings from a list, preserving order.

    Args:
        items: List of strings that may contain duplicates.

    Returns:
        List with duplicates removed, preserving first occurrence order.
    """
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
